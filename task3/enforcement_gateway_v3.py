from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List

# Task-2 dependency
from common_infra_v2 import Router, Dependencies

from .data_model_v3 import DataObject, ShareGrant, RequestContext
from .policy_engine_v3 import evaluate_sensitive
from .audit_ledger_v3 import AuditLedger
from .kms_mock_v3 import KMSMock, WrappedKey
from .deletion_manager_v3 import DeletionManager

SAFE_READS = {"view_balance", "view_transaction_history", "view_profile_basic"}

@dataclass
class ReadModelRecord:
    balance: float = 0.0
    transactions: List[str] = field(default_factory=list)
    profile_basic: Dict[str, str] = field(default_factory=dict)

class ReadModelStore:
    """
    Replicated read-safe model used for Tier-1 safe reads.
    """
    def __init__(self):
        self._by_user: Dict[str, ReadModelRecord] = {}

    def seed(self, user_id: str) -> None:
        self._by_user.setdefault(user_id, ReadModelRecord())

    def set_balance(self, user_id: str, bal: float) -> None:
        self.seed(user_id)
        self._by_user[user_id].balance = bal

    def add_txn(self, user_id: str, txn: str) -> None:
        self.seed(user_id)
        self._by_user[user_id].transactions.append(txn)

    def set_profile(self, user_id: str, profile: Dict[str, str]) -> None:
        self.seed(user_id)
        self._by_user[user_id].profile_basic = dict(profile)

    def get_balance(self, user_id: str) -> float:
        self.seed(user_id)
        return self._by_user[user_id].balance

    def get_txns(self, user_id: str) -> List[str]:
        self.seed(user_id)
        return list(self._by_user[user_id].transactions)

    def get_profile(self, user_id: str) -> Dict[str, str]:
        self.seed(user_id)
        return dict(self._by_user[user_id].profile_basic)

    def delete_user(self, user_id: str) -> None:
        self._by_user.pop(user_id, None)

class DerivedStores:
    """
    Derived artifacts (OCR text, embeddings, indexes, etc.).
    Must be deleted on erasure.
    """
    def __init__(self):
        self._derived: Dict[str, Dict[str, str]] = {}

    def put(self, object_id: str, artifact_type: str, value: str) -> None:
        self._derived.setdefault(object_id, {})
        self._derived[object_id][artifact_type] = value

    def get(self, object_id: str) -> Dict[str, str]:
        return dict(self._derived.get(object_id, {}))

    def delete_object(self, object_id: str) -> None:
        self._derived.pop(object_id, None)

class ShareStore:
    def __init__(self):
        self._grants: Dict[str, ShareGrant] = {}

    def put(self, g: ShareGrant) -> None:
        self._grants[g.grant_id] = g

    def find(self, object_id: str, grantee_id: str) -> Optional[ShareGrant]:
        for g in self._grants.values():
            if g.object_id == object_id and g.grantee_user_id == grantee_id:
                return g
        return None

    def revoke(self, grant_id: str) -> None:
        g = self._grants.get(grant_id)
        if g:
            self._grants[grant_id] = ShareGrant(**{**g.__dict__, "revoked": True})

class EnforcementGateway:
    """
    Single compliance choke-point:
    - Tier-1 safe reads: ReadModelStore, degraded-friendly
    - Tier-2/3 sensitive ops: fail-closed deps + residency + KMS gate + audit
    - Deletion: tombstone + derived cleanup + crypto-erasure
    """
    def __init__(self, router: Router, ledger: AuditLedger, kms: KMSMock, shares: ShareStore, deletions: DeletionManager):
        self.router = router
        self.ledger = ledger
        self.kms = kms
        self.shares = shares
        self.deletions = deletions
        self.read_models = ReadModelStore()
        self.derived = DerivedStores()
        self._wrapped_keys: Dict[str, WrappedKey] = {}

    def _deps_healthy_sensitive(self, deps: Dependencies) -> bool:
        # Fail closed for sensitive actions 
        return deps.auth_ok and deps.policy_ok and deps.risk_ok and deps.audit_ok and deps.kms_ok

    def create_object(self, obj: DataObject) -> None:
        dk = self.kms.generate_data_key()
        self._wrapped_keys[obj.object_id] = self.kms.wrap(obj.home_region, dk)

    def share(self, grant: ShareGrant) -> None:
        self.shares.put(grant)

    def revoke(self, grant_id: str) -> None:
        self.shares.revoke(grant_id)

    def gdpr_delete(self, obj: DataObject) -> None:
        self.deletions.request_delete(obj.object_id, reason="erasure")
        self.derived.delete_object(obj.object_id)
        self.kms.revoke_object(obj.object_id)
        self.read_models.delete_user(obj.owner_user_id)

    # Tier-1 Safe Reads — available even if Anything is down 
    def handle_safe_read(
        self,
        op: str,
        subject_user_id: str,
        tenant_id: str,
        ctx: RequestContext,
        deps: Dependencies
    ) -> Tuple[bool, str]:

        if op not in SAFE_READS:
            return False, "DENY: not a safe read op"

        if not deps.auth_ok:
            return False, "DENY: auth unavailable"

        # If policy is down, allow only self-read for safety
        if not deps.policy_ok and ctx.actor_user_id != subject_user_id:
            return False, "DENY: policy down (safe reads limited to self)"

        # Serve from read model 
        if op == "view_balance":
            _ = self.read_models.get_balance(subject_user_id)
        elif op == "view_transaction_history":
            _ = self.read_models.get_txns(subject_user_id)
        elif op == "view_profile_basic":
            _ = self.read_models.get_profile(subject_user_id)

        return True, "ALLOW: safe read from read-model (degraded-friendly)"

    # Tier-2/3 Sensitive Ops
    def handle_sensitive(self, op: str, obj: DataObject, ctx: RequestContext, deps: Dependencies) -> Tuple[bool, str]:
        # Tombstone deny immediately
        if self.deletions.is_deleted(obj.object_id):
            return False, "DENY: deleted (tombstone)"

        # Using Task-2 Router to record shard 
        shard, loc, pv, msg = self.router.resolve_home(obj.owner_user_id, deps)
        if not shard:
            return False, f"DENY: placement unavailable ({msg})"

        grant = None
        if ctx.actor_user_id != obj.owner_user_id:
            grant = self.shares.find(obj.object_id, ctx.actor_user_id)

        allow, reason = evaluate_sensitive(
            op=op,
            obj=obj,
            ctx=ctx,
            grant=grant,
            deps_healthy_for_sensitive=self._deps_healthy_sensitive(deps),
        )

        # KMS region gate + crypto-erasure
        if allow and obj.data_tier in {"DATA_TIER_2", "DATA_TIER_3"}:
            wk = self._wrapped_keys.get(obj.object_id)
            if wk and not self.kms.can_decrypt(obj.object_id, wk, ctx.serving_region):
                allow = False
                reason = "DENY: KMS gate (wrong region or crypto-erased)"

        # Audit ALLOW + DENY
        self.ledger.append({
            "ts_utc": time.time(),
            "actor_user_id": ctx.actor_user_id,
            "actor_role": ctx.actor_role,
            "op": op,
            "object_id": obj.object_id,
            "data_tier": obj.data_tier,
            "home_region": obj.home_region,
            "serving_region": ctx.serving_region,
            "shard_id": shard,
            "placement_version": pv,
            "purpose": ctx.purpose,
            "grant_id": (grant.grant_id if grant else ""),
            "decision": "ALLOW" if allow else "DENY",
            "reason": reason,
        })

        return allow, reason

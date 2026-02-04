from __future__ import annotations
import time
from typing import Optional, Tuple

from .data_model_v3 import DataObject, ShareGrant, RequestContext

FAIL_CLOSED_DATA = {"DATA_TIER_2", "DATA_TIER_3"}

SAFE_READS = {"view_transaction_history", "view_profile_basic", "view_balance"}
SENSITIVE_OPS = {"transfer_money", "add_beneficiary", "export_data", "change_permissions"}

PURPOSE_ALLOWLIST = {
    "lending": {"export_data", "view_transaction_history"},
    "treatment": {"export_data", "view_transaction_history"},
    "payment": {"view_transaction_history"},
    "operations": {"view_transaction_history"},
    "ops": {"view_profile_basic", "view_transaction_history"},
}

def _grant_ok(now: float, g: ShareGrant) -> bool:
    return (not g.revoked) and (g.start_ts <= now <= g.end_ts)

def evaluate_sensitive(
    op: str,
    obj: DataObject,
    ctx: RequestContext,
    grant: Optional[ShareGrant],
    deps_healthy_for_sensitive: bool,
    now: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Sensitive path evaluation (Tier-2/3 vault).
    Safe reads are intentionally NOT allowed here (they must use a read-safe model).
    """
    now = now if now is not None else time.time()

    if not ctx.actor_user_id or not ctx.purpose:
        return False, "DENY: missing actor or purpose"
    if not obj.tenant_id:
        return False, "DENY: missing tenant"

    # Tier-2/3 fail closed if compliance dependencies are unhealthy
    if obj.data_tier in FAIL_CLOSED_DATA and not deps_healthy_for_sensitive:
        return False, f"DENY: deps unavailable for {obj.data_tier} (fail closed)"

    # Residency: Tier-2/3 must be served in home region
    if obj.data_tier in FAIL_CLOSED_DATA and ctx.serving_region != obj.home_region:
        return False, "DENY: residency requires home-region servicing"

    # Owner allowed after residency checks
    if ctx.actor_user_id == obj.owner_user_id:
        return True, "ALLOW: owner"

    # Safe reads should not touch sensitive vault
    if op in SAFE_READS:
        return False, "DENY: safe read must use read-model path"

    # Sensitive ops require admin
    if op in SENSITIVE_OPS:
        if ctx.actor_role == "admin":
            return True, "ALLOW: admin"

        if not grant:
            return False, "DENY: missing grant"
        if grant.object_id != obj.object_id or grant.grantee_user_id != ctx.actor_user_id:
            return False, "DENY: grant mismatch"
        if not _grant_ok(now, grant):
            return False, "DENY: grant expired or revoked"
        if ctx.purpose != grant.purpose:
            return False, "DENY: purpose mismatch"

        allowed = PURPOSE_ALLOWLIST.get(ctx.purpose, set())
        if op not in allowed:
            return False, "DENY: minimum-necessary (op not allowed for purpose)"

        return True, "ALLOW: grant+purpose+window OK"

    return False, "DENY: unknown op"

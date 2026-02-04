from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import hashlib, json, uuid

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@dataclass
class AuditEvent:
    event_id: str
    ts_utc: float
    actor_user_id: str
    actor_role: str
    op: str
    object_id: str
    data_tier: str
    home_region: str
    serving_region: str
    shard_id: str
    placement_version: int
    purpose: str
    grant_id: str
    decision: str
    reason: str
    policy_version: int
    prev_hash: str
    hash: str

class AuditLedger:
    """
    Tamper-evident audit chain.
    append() hashes a stable JSON payload and links it with prev_hash.
    verify_chain() must recompute the same payload (not the entire dataclass).
    """
    def __init__(self, policy_version: int = 1):
        self.policy_version = policy_version
        self._events: List[AuditEvent] = []
        self._last_hash = "GENESIS"

    def append(self, payload: Dict[str, Any]) -> AuditEvent:
        p = dict(payload)
        p["policy_version"] = self.policy_version
        p["prev_hash"] = self._last_hash

        stable = json.dumps(p, sort_keys=True)
        h = _sha256(stable)

        ev = AuditEvent(
            event_id=str(uuid.uuid4()),
            ts_utc=p["ts_utc"],
            actor_user_id=p["actor_user_id"],
            actor_role=p["actor_role"],
            op=p["op"],
            object_id=p["object_id"],
            data_tier=p["data_tier"],
            home_region=p["home_region"],
            serving_region=p["serving_region"],
            shard_id=p["shard_id"],
            placement_version=p["placement_version"],
            purpose=p["purpose"],
            grant_id=p.get("grant_id", ""),
            decision=p["decision"],
            reason=p["reason"],
            policy_version=self.policy_version,
            prev_hash=self._last_hash,
            hash=h,
        )
        self._events.append(ev)
        self._last_hash = h
        return ev

    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for e in self._events:
            p = {
                "ts_utc": e.ts_utc,
                "actor_user_id": e.actor_user_id,
                "actor_role": e.actor_role,
                "op": e.op,
                "object_id": e.object_id,
                "data_tier": e.data_tier,
                "home_region": e.home_region,
                "serving_region": e.serving_region,
                "shard_id": e.shard_id,
                "placement_version": e.placement_version,
                "purpose": e.purpose,
                "grant_id": e.grant_id,
                "decision": e.decision,
                "reason": e.reason,
                "policy_version": e.policy_version,
                "prev_hash": prev,
            }
            stable = json.dumps(p, sort_keys=True)
            if _sha256(stable) != e.hash:
                return False
            prev = e.hash
        return True

    def dump(self, limit: int = 25) -> None:
        for e in self._events[:limit]:
            print(asdict(e))

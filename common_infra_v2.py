# common_infra_v2.py
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Dict, Iterable, Optional, Tuple, Any

# 1) Stable shard membership 

ACTIVE_SHARDS = [f"shard-{i:03d}" for i in range(1, 65)]  # 64 logical shards

# 2) HRW / Rendezvous hashing 


def _u256(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)

def hrw_shard_for_user(user_id: str, shard_ids: Iterable[str]) -> str:
    best_sid = None
    best_score = None
    for sid in shard_ids:
        score = _u256(f"{user_id}:{sid}")
        if best_score is None or score > best_score:
            best_score = score
            best_sid = sid
    assert best_sid is not None
    return best_sid

# 3) Placement service (logical shard -> region/cell) 


@dataclass
class PlacementSnapshot:
    placement: Dict[str, Dict[str, str]]  # shard -> {"region":..., "cell":...}
    version: int
    fetched_at: float

class PlacementService:
    """
    In reality: strongly consistent metadata store (e.g., etcd/spanner).
    Here: in-memory + version increments.
    """
    def __init__(self, initial_placement: Dict[str, Dict[str, str]]):
        # should contain entries for all ACTIVE_SHARDS
        self._placement = dict(initial_placement)
        self._version = 1

    def get_snapshot(self) -> PlacementSnapshot:
        return PlacementSnapshot(
            placement=dict(self._placement),
            version=self._version,
            fetched_at=time.time()
        )

    def move_shard(self, shard_id: str, region: str, cell: str) -> None:
        self._placement[shard_id] = {"region": region, "cell": cell}
        self._version += 1

# 4) Dependencies + tier gating

@dataclass
class Dependencies:
    auth_ok: bool = True
    policy_ok: bool = True
    risk_ok: bool = True
    audit_ok: bool = True
    kms_ok: bool = True
    placement_ok: bool = True

OP_TIER = {
    "view_public": "TIER_0",
    "view_profile_basic": "TIER_1",
    "low_value_action": "TIER_1",
    "view_pii": "TIER_2",
    "export_data": "TIER_2",
    "change_permissions": "TIER_2",
    "high_value_action": "TIER_2",
    "issue_token": "TIER_2",
    "rotate_keys": "TIER_2",
    "transfer": "TIER_2",
}

REQUIRES = {
    "view_public": {"auth"},
    "view_profile_basic": {"auth"},
    "low_value_action": {"auth"},
    "view_pii": {"auth", "policy"},
    "export_data": {"auth", "policy", "audit", "kms"},
    "change_permissions": {"auth", "policy", "audit"},
    "high_value_action": {"auth", "policy", "risk", "audit"},
    "issue_token": {"auth", "policy", "risk"},
    "rotate_keys": {"auth", "policy", "kms", "audit"},
    "transfer": {"auth", "policy", "risk", "audit"},
}

SECURITY_CRITICAL = {
    "view_pii", "export_data", "change_permissions",
    "high_value_action", "issue_token", "rotate_keys", "transfer"
}

def deps_ok_for(op: str, deps: Dependencies) -> Tuple[bool, str]:
    tier = OP_TIER.get(op, "TIER_2")
    req = REQUIRES.get(op, {"auth", "policy"})

    if not deps.auth_ok:
        return False, "DENY: auth unavailable"

    if tier == "TIER_2":
        if "policy" in req and not deps.policy_ok:
            return False, "DENY: policy unavailable (Tier-2 fail closed)"
        if "risk" in req and not deps.risk_ok:
            return False, "DENY: risk unavailable (Tier-2 fail closed)"
        if "audit" in req and not deps.audit_ok:
            return False, "DENY: audit unavailable (Tier-2 fail closed)"
        if "kms" in req and not deps.kms_ok:
            return False, "DENY: KMS unavailable (Tier-2 fail closed)"
        return True, "ALLOW"

    # Tier-1 can degrade when risk down; still requires auth (+ any required deps)
    if tier == "TIER_1":
        if "policy" in req and not deps.policy_ok:
            return False, "DENY: policy unavailable"
        if "audit" in req and not deps.audit_ok:
            return False, "DENY: audit unavailable"
        if "kms" in req and not deps.kms_ok:
            return False, "DENY: KMS unavailable"
        if not deps.risk_ok:
            return True, "ALLOW_DEGRADED: Tier-1 (risk down)"
        return True, "ALLOW"

    return True, "ALLOW"

# 5) Coarse protections 


RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_PER_WINDOW = 60
HIGH_RISK_WINDOW_SEC = 600
HIGH_RISK_MAX_PER_WINDOW = 3

class CoarseProtections:
    def __init__(self):
        self._actions: Dict[str, deque] = defaultdict(deque)
        self._high_risk: Dict[str, deque] = defaultdict(deque)

    def _gc(self, q: deque, now: float, window: float) -> None:
        while q and now - q[0] > window:
            q.popleft()

    def check(self, user_id: str, op: str, now: float) -> Tuple[bool, str]:
        q = self._actions[user_id]
        self._gc(q, now, RATE_LIMIT_WINDOW_SEC)
        if len(q) >= RATE_LIMIT_MAX_PER_WINDOW:
            return False, "DENY: coarse rate limit"
        q.append(now)

        if op in SECURITY_CRITICAL:
            hq = self._high_risk[user_id]
            self._gc(hq, now, HIGH_RISK_WINDOW_SEC)
            if len(hq) >= HIGH_RISK_MAX_PER_WINDOW:
                return False, "DENY: coarse high-risk velocity"
            hq.append(now)

        return True, "OK"



# 6) Real idempotency 


def payload_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

class IdempotencyStore:
    """
    (user, op, idempotency_key) -> (payload_hash, response, ts)
    If retried with same payload_hash -> return same response.
    """
    def __init__(self):
        self._store: Dict[Tuple[str, str, str], Tuple[str, Any, float]] = {}

    def _gc(self, now: float, ttl_sec: int) -> None:
        expired = [k for k, (_, __, ts) in self._store.items() if now - ts > ttl_sec]
        for k in expired:
            del self._store[k]

    def get_or_record(
        self,
        user_id: str,
        op: str,
        idem_key: str,
        ph: str,
        compute_response_fn,
        now: float,
        ttl_sec: int = 24 * 3600
    ) -> Tuple[bool, Any, str]:
        self._gc(now, ttl_sec)
        if not idem_key:
            return False, None, "DENY: missing idempotency key"

        k = (user_id, op, idem_key)
        if k in self._store:
            prev_ph, resp, _ = self._store[k]
            if prev_ph != ph:
                return False, None, "DENY: idempotency key reused with different payload"
            return True, resp, "ALLOW: idempotent replay (cached response)"

        resp = compute_response_fn()
        self._store[k] = (ph, resp, now)
        return True, resp, "ALLOW: recorded idempotency"

# 7) Queue carries target shard + placement version


QUEUE_ITEM_TTL_SEC = 24 * 3600
QUEUE_DRAIN_RATE_PER_USER = 5

@dataclass
class WriteEvent:
    user_id: str
    action: str
    payload: str
    idem_key: str
    created_at: float
    target_shard: str
    placement_version: int

class WriteQueue:
    def __init__(self):
        self._q: Dict[str, deque] = defaultdict(deque)

    def enqueue(self, ev: WriteEvent) -> None:
        self._q[ev.user_id].append(ev)

    def drain(self, user_id: str, now: float, process_fn, rate_limit: int = QUEUE_DRAIN_RATE_PER_USER) -> Tuple[int, int]:
        q = self._q.get(user_id)
        if not q:
            return 0, 0

        processed = 0
        dropped = 0

        while q and (now - q[0].created_at) > QUEUE_ITEM_TTL_SEC:
            q.popleft()
            dropped += 1

        while q and processed < rate_limit:
            ev = q.popleft()
            if (now - ev.created_at) > QUEUE_ITEM_TTL_SEC:
                dropped += 1
                continue
            process_fn(ev)
            processed += 1

        if not q:
            self._q.pop(user_id, None)

        return processed, dropped


# 8) Routing (read-local / write-home) 


PLACEMENT_CACHE_TTL_SEC = 30

@dataclass
class CellHealth:
    cell_ok: Dict[str, bool] = field(default_factory=dict)

@dataclass
class User:
    user_id: str
    residency: str  # "us" | "eu" | "apac"

def residency_allows(user: User, region: str, op: str) -> bool:
    # baseline rule: strict for PII/export
    if op in {"view_pii", "export_data"}:
        return user.residency == region
    return True

class Router:
    def __init__(self, placement_svc: PlacementService):
        self.svc = placement_svc
        self._cache: Optional[PlacementSnapshot] = None

    def _snapshot(self, deps: Dependencies) -> Tuple[Optional[PlacementSnapshot], str]:
        now = time.time()

        if deps.placement_ok:
            snap = self.svc.get_snapshot()
            self._cache = snap
            return snap, "OK: placement fresh"

        if self._cache and (now - self._cache.fetched_at) <= PLACEMENT_CACHE_TTL_SEC:
            return self._cache, "OK: placement cached"

        return None, "DENY: placement unavailable and cache stale"

    def resolve_home(self, user_id: str, deps: Dependencies) -> Tuple[Optional[str], Optional[Dict[str, str]], Optional[int], str]:
        snap, msg = self._snapshot(deps)
        if not snap:
            return None, None, None, msg

        shard = hrw_shard_for_user(user_id, ACTIVE_SHARDS)
        return shard, snap.placement[shard], snap.version, "OK"

    def route_read(self, user: User, op: str, serving_region: str, deps: Dependencies) -> Tuple[bool, str]:
        ok, reason = deps_ok_for(op, deps)
        if not ok:
            return False, reason

        if not residency_allows(user, serving_region, op):
            shard, loc, _, msg = self.resolve_home(user.user_id, deps)
            if not shard:
                return False, msg
            return True, f"ALLOW: residency forces home-read via {loc['region']} {loc['cell']}"

        return True, f"ALLOW: read-local in {serving_region}"

    def route_write(self, user: User, op: str, deps: Dependencies, health: CellHealth) -> Tuple[str, str, Optional[str], Optional[int]]:
        ok, reason = deps_ok_for(op, deps)
        if not ok:
            return "FAIL", reason, None, None

        shard, loc, pv, msg = self.resolve_home(user.user_id, deps)
        if not shard:
            return "FAIL", msg, None, None

        cell = loc["cell"]
        if not health.cell_ok.get(cell, True):
            if op in SECURITY_CRITICAL:
                return "FAIL", f"DENY: home cell down ({cell}) for Tier-2", shard, pv
            return "QUEUE", f"QUEUE: home cell down ({cell}) for Tier-1", shard, pv

        return "WRITE_HOME", f"WRITE_HOME: {shard} via {loc['region']} {cell}", shard, pv



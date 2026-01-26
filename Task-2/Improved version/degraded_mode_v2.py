# degraded_mode_v2.py
import time
from common_infra_v2 import (
    ACTIVE_SHARDS, PlacementService, Router, Dependencies, CellHealth, User,
    CoarseProtections, IdempotencyStore, WriteQueue, WriteEvent, payload_hash
)

def make_demo_placement() -> dict:
    """
    Simple deterministic placement:
    - even shards go to us-cell-1
    - odd shards go to eu-cell-1
    This is enough to demonstrate routing + failure behavior.
    """
    placement = {}
    for i, s in enumerate(ACTIVE_SHARDS):
        placement[s] = {"region": "us", "cell": "us-cell-1"} if i % 2 == 0 else {"region": "eu", "cell": "eu-cell-1"}
    return placement

class Evaluator:
    def __init__(self, router: Router):
        self.router = router
        self.coarse = CoarseProtections()
        self.idem = IdempotencyStore()
        self.queue = WriteQueue()

    def write(self, user: User, op: str, payload: str, idem_key: str, deps: Dependencies, health: CellHealth):
        now = time.time()

        ok, why = self.coarse.check(user.user_id, op, now)
        if not ok:
            return False, why

        decision, route_msg, shard, pv = self.router.route_write(user, op, deps, health)
        if decision == "FAIL":
            return False, route_msg

        ph = payload_hash(payload)

        def compute_resp():
            return {"status": "ok", "op": op, "home_shard": shard}

        ok, resp, idem_msg = self.idem.get_or_record(user.user_id, op, idem_key, ph, compute_resp, now)
        if not ok:
            return False, idem_msg

        if decision == "QUEUE":
            self.queue.enqueue(WriteEvent(
                user_id=user.user_id,
                action=op,
                payload=payload,
                idem_key=idem_key,
                created_at=now,
                target_shard=shard,
                placement_version=pv
            ))
            return True, f"{route_msg} | {idem_msg} | QUEUED"

        return True, f"{route_msg} | {idem_msg} | EXECUTED resp={resp}"

    def drain(self, user_id: str):
        now = time.time()
        def process_fn(ev: WriteEvent):
            # demo: no-op (in real life: re-check placement/health and execute)
            pass
        return self.queue.drain(user_id, now, process_fn)

def main():
    svc = PlacementService(make_demo_placement())
    router = Router(svc)
    ev = Evaluator(router)

    health = CellHealth(cell_ok={"us-cell-1": True, "eu-cell-1": True})
    user = User("u-123", residency="eu")

    # Determine home cell
    shard, loc, pv, _ = router.resolve_home(user.user_id, Dependencies())
    home_cell = loc["cell"]

    print("\nDegraded Mode Simulation\n")
    print(f"User: {user.user_id} residency={user.residency}")
    print(f"Home shard: {shard} | home cell: {home_cell} | placement_version={pv}\n")

    # Scenario 1:If Home cell is down
    print("Scenario 1: Home cell DOWN")
    health.cell_ok[home_cell] = False

    for op in ["change_permissions", "export_data", "view_profile_basic", "low_value_action"]:
        ok, msg = ev.write(user, op, payload="payload", idem_key=f"k-{op}-1", deps=Dependencies(), health=health)
        print(f"{op:20} -> {ok} | {msg}")

    # Recover & drain
    print("\nRecover home cell and drain")
    health.cell_ok[home_cell] = True
    processed, dropped = ev.drain(user.user_id)
    print(f"drain -> processed={processed}, dropped={dropped}\n")

    # Scenario 2: Risk down + Tier-2
    print("Scenario 2: Risk DOWN + Tier-2 op (should fail closed)")
    ok, msg = ev.write(user, "issue_token", payload="p", idem_key="k-issue-1", deps=Dependencies(risk_ok=False), health=health)
    print(f"{'issue_token':20} -> {ok} | {msg}\n")

    # Scenario 3: Policy down + Tier-1/Tier-2 contrast
    print(" Scenario 3: Policy DOWN + Tier-1 vs Tier-2")
    deps = Dependencies(policy_ok=False)
    ok1, msg1 = ev.write(user, "view_profile_basic", payload="p", idem_key="k-prof-1", deps=deps, health=health)
    ok2, msg2 = ev.write(user, "view_pii", payload="p", idem_key="k-pii-1", deps=deps, health=health)
    print(f"{'view_profile_basic':20} -> {ok1} | {msg1}")
    print(f"{'view_pii':20} -> {ok2} | {msg2}\n")

    # Scenario 4: Idempotent retry returns same response
    print(" Scenario 4: Idempotent retry returns cached response ")
    ok1, msg1 = ev.write(user, "low_value_action", payload="p", idem_key="k-same-1", deps=Dependencies(), health=health)
    ok2, msg2 = ev.write(user, "low_value_action", payload="p", idem_key="k-same-1", deps=Dependencies(), health=health)
    print(f"{'first':20} -> {ok1} | {msg1}")
    print(f"{'retry':20} -> {ok2} | {msg2}\n")

if __name__ == "__main__":
    main()

from __future__ import annotations
import time

from common_infra_v2 import ACTIVE_SHARDS, PlacementService, Router, Dependencies

from task3.data_model_v3 import DataObject, ShareGrant, RequestContext
from task3.audit_ledger_v3 import AuditLedger
from task3.kms_mock_v3 import KMSMock
from task3.deletion_manager_v3 import DeletionManager
from task3.enforcement_gateway_v3 import EnforcementGateway, ShareStore

def make_demo_placement():
    # deterministic placement for demo
    placement = {}
    for i, s in enumerate(ACTIVE_SHARDS):
        placement[s] = {"region": "eu", "cell": "eu-cell-1"} if i % 2 == 0 else {"region": "us", "cell": "us-cell-1"}
    return placement

def main():
    svc = PlacementService(make_demo_placement())
    router = Router(svc)
    ledger = AuditLedger(policy_version=3)

    gw = EnforcementGateway(router, ledger, KMSMock(), ShareStore(), DeletionManager())

    # Seed read models (Tier-1)
    owner = "owner-eu"
    gw.read_models.set_balance(owner, 1250.50)
    gw.read_models.add_txn(owner, "TXN#1 coffee $5.25")
    gw.read_models.add_txn(owner, "TXN#2 rent $900.00")
    gw.read_models.set_profile(owner, {"name": "EU Owner", "plan": "gold"})

    # Create a regulated Tier-3 object 
    obj = DataObject(object_id="doc-eu-001", data_tier="DATA_TIER_3", home_region="eu", tenant_id="tenant-1", owner_user_id=owner)
    gw.create_object(obj)

    # Share grant to US lender for lending purpose
    now = time.time()
    grant = ShareGrant(
        grant_id="g-1",
        object_id=obj.object_id,
        owner_user_id=obj.owner_user_id,
        grantee_user_id="lender-us",
        purpose="lending",
        start_ts=now,
        end_ts=now + 7 * 24 * 3600,
    )
    gw.share(grant)

    # Contexts
    lender_us = RequestContext(actor_user_id="lender-us", actor_role="lender", actor_residency="us", serving_region="us", purpose="lending")
    owner_ctx_degraded = RequestContext(actor_user_id=owner, actor_role="user", actor_residency="eu", serving_region="us", purpose="ops")

    print("\nSCENARIO 1: Degraded deps → Safe reads still allowed (read-model)")
    bad_deps = Dependencies(policy_ok=False, risk_ok=False, audit_ok=False, kms_ok=False)  
    print("view_transaction_history:", gw.handle_safe_read("view_transaction_history", owner, "tenant-1", owner_ctx_degraded, bad_deps))
    print("view_profile_basic:", gw.handle_safe_read("view_profile_basic", owner, "tenant-1", owner_ctx_degraded, bad_deps))
    print("view_balance:", gw.handle_safe_read("view_balance", owner, "tenant-1", owner_ctx_degraded, bad_deps))

    print("\nSCENARIO 2: Degraded deps → Sensitive ops FAIL CLOSED")
    print("transfer_money:", gw.handle_sensitive("transfer_money", obj, lender_us, bad_deps))
    print("add_beneficiary:", gw.handle_sensitive("add_beneficiary", obj, lender_us, bad_deps))

    print("\nSCENARIO 3: Residency enforcement (US vs EU)")
    print("export_data from US:", gw.handle_sensitive("export_data", obj, lender_us, Dependencies()))
    lender_via_eu = RequestContext(actor_user_id="lender-us", actor_role="lender", actor_residency="us", serving_region="eu", purpose="lending")
    print("export_data via EU:", gw.handle_sensitive("export_data", obj, lender_via_eu, Dependencies()))

    print("\nSCENARIO 4: Deletion (tombstone + derived cleanup + crypto-erasure)")
    gw.derived.put(obj.object_id, "ocr_text", "example derived OCR text")
    gw.gdpr_delete(obj)
    print("after delete export_data:", gw.handle_sensitive("export_data", obj, lender_via_eu, Dependencies()))
    print("derived after delete:", gw.derived.get(obj.object_id))

    print("\nAUDIT CHAIN VALID:", ledger.verify_chain())
    print("\nAUDIT SAMPLE:")
    ledger.dump(limit=30)

if __name__ == "__main__":
    main()

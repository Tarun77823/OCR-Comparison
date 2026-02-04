from __future__ import annotations
import time

from common_infra_v2 import ACTIVE_SHARDS, PlacementService, Router, Dependencies

from task3.data_model_v3 import DataObject, ShareGrant, RequestContext
from task3.audit_ledger_v3 import AuditLedger
from task3.kms_mock_v3 import KMSMock
from task3.deletion_manager_v3 import DeletionManager
from task3.enforcement_gateway_v3 import EnforcementGateway, ShareStore

def make_demo_placement():
    placement = {}
    for i, s in enumerate(ACTIVE_SHARDS):
        placement[s] = {"region": "eu", "cell": "eu-cell-1"} if i % 2 == 0 else {"region": "us", "cell": "us-cell-1"}
    return placement

def build():
    svc = PlacementService(make_demo_placement())
    router = Router(svc)
    ledger = AuditLedger(policy_version=9)
    gw = EnforcementGateway(router, ledger, KMSMock(), ShareStore(), DeletionManager())
    return gw, ledger

def test_safe_reads_work_when_policy_down_self_only():
    gw, ledger = build()
    gw.read_models.set_balance("u1", 10.0)

    ctx_self = RequestContext("u1", "user", "us", "us", "ops")
    deps = Dependencies(policy_ok=False, risk_ok=False, audit_ok=False, kms_ok=False)
    ok, _ = gw.handle_safe_read("view_balance", "u1", "t1", ctx_self, deps)
    assert ok is True

    ctx_other = RequestContext("u2", "user", "us", "us", "ops")
    ok, _ = gw.handle_safe_read("view_balance", "u1", "t1", ctx_other, deps)
    assert ok is False

def test_sensitive_fails_closed_when_deps_down():
    gw, ledger = build()
    obj = DataObject("o1", "DATA_TIER_3", "eu", "t1", "owner-eu")
    gw.create_object(obj)
    ctx = RequestContext("owner-eu", "admin", "eu", "eu", "ops")
    deps = Dependencies(policy_ok=False, risk_ok=False, audit_ok=False, kms_ok=False)
    ok, _ = gw.handle_sensitive("transfer_money", obj, ctx, deps)
    assert ok is False

def test_residency_blocks_sensitive_outside_home_region():
    gw, ledger = build()
    obj = DataObject("o2", "DATA_TIER_3", "eu", "t1", "owner-eu")
    gw.create_object(obj)

    now = time.time()
    gw.share(ShareGrant("g1", obj.object_id, obj.owner_user_id, "lender", "lending", now, now + 1000))

    ctx_us = RequestContext("lender", "lender", "us", "us", "lending")
    ok, _ = gw.handle_sensitive("export_data", obj, ctx_us, Dependencies())
    assert ok is False

    ctx_eu = RequestContext("lender", "lender", "us", "eu", "lending")
    ok, _ = gw.handle_sensitive("export_data", obj, ctx_eu, Dependencies())
    assert ok is True

def test_deletion_blocks_and_crypto_erasure_blocks_decrypt():
    gw, ledger = build()
    obj = DataObject("o3", "DATA_TIER_3", "eu", "t1", "owner-eu")
    gw.create_object(obj)
    gw.gdpr_delete(obj)

    ctx_eu = RequestContext("owner-eu", "admin", "eu", "eu", "ops")
    ok, _ = gw.handle_sensitive("export_data", obj, ctx_eu, Dependencies())
    assert ok is False

def test_audit_chain_valid():
    gw, ledger = build()
    gw.read_models.set_balance("u9", 9.0)
    ctx = RequestContext("u9", "user", "us", "us", "ops")
    ok, _ = gw.handle_safe_read("view_balance", "u9", "t9", ctx, Dependencies(policy_ok=False))
    assert ok is True
    assert ledger.verify_chain() is True

def main():
    test_safe_reads_work_when_policy_down_self_only()
    test_sensitive_fails_closed_when_deps_down()
    test_residency_blocks_sensitive_outside_home_region()
    test_deletion_blocks_and_crypto_erasure_blocks_decrypt()
    test_audit_chain_valid()
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    main()

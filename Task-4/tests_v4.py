import unittest
from data_model_v4 import *
from kms_v4 import *
from audit_ledger_v4 import *
from policy_engine_v4 import *
from enforcement_gateway_v4 import *


class SimpleStorage:

    def __init__(self):
        self.objects = {}
        self.grants = {}

    def put_object(self, obj):
        self.objects[obj.object_id] = obj

    def get_object(self, obj_id):
        return self.objects.get(obj_id)

    def get_grant(self, obj_id, user_id):
        return None


class TestTask4(unittest.TestCase):

    def setUp(self):
        self.storage = SimpleStorage()
        self.kms = KmsV4()
        self.audit = AuditLedgerV4()
        self.policy = PolicyEngineV4()

        self.gateway = EnforcementGatewayV4(
            self.storage,
            None,
            self.kms,
            self.policy,
            self.audit
        )

        self.kms.ensure_key("doc")

        enc = self.kms.encrypt("doc", b"data")

        obj = DataObject(
            object_id="doc",
            tenant_id="tenant1",
            owner_id="owner",
            home_region="EU",
            data_tier="TIER3",
            encrypted_blob=enc
        )

        self.storage.put_object(obj)

    def test_tenant_isolation(self):

        ctx = RequestContext(
            user_id="attacker",
            role="Agent",
            tenant_id="tenant2",
            purpose="lending_underwriting",
            serving_region="EU"
        )

        d, _ = self.gateway.handle(ctx, "view_document_content", "doc")

        self.assertEqual(d.reason, "tenant_mismatch")

    def test_residency(self):

        ctx = RequestContext(
            user_id="owner",
            role="Owner",
            tenant_id="tenant1",
            purpose="lending_underwriting",
            serving_region="US"
        )

        d, _ = self.gateway.handle(ctx, "view_document_content", "doc")

        self.assertEqual(d.reason, "wrong_region")

    def test_proxy_required(self):

        ctx = RequestContext(
            user_id="owner",
            role="Owner",
            tenant_id="tenant1",
            purpose="lending_underwriting",
            serving_region="EU",
            client_region="US",
            via_proxy=False
        )

        d, _ = self.gateway.handle(ctx, "view_document_content", "doc")

        self.assertEqual(d.reason, "proxy_required")

    def test_success(self):

        ctx = RequestContext(
            user_id="owner",
            role="Owner",
            tenant_id="tenant1",
            purpose="lending_underwriting",
            serving_region="EU",
            client_region="US",
            via_proxy=True
        )

        d, _ = self.gateway.handle(ctx, "view_document_content", "doc")

        self.assertTrue(d.allow)

    def test_audit(self):

        self.assertTrue(self.audit.verify_chain())


if __name__ == "__main__":
    unittest.main()
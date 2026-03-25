import time

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

    def put_grant(self, grant):
        self.grants[grant.grant_id] = grant

    def get_grant(self, obj_id, user_id):
        for g in self.grants.values():
            if g.object_id == obj_id and g.agent_id == user_id:
                return g
        return None


# Setup
store = SimpleStorage()
kms = KmsV4()
audit = AuditLedgerV4()
policy = PolicyEngineV4()

gateway = EnforcementGatewayV4(store, None, kms, policy, audit)


# Creating document
kms.ensure_key("doc1")
enc = kms.encrypt("doc1", b"SECRET_DATA")

obj = DataObject(
    object_id="doc1",
    tenant_id="tenantA",
    owner_id="owner1",
    home_region="EU",
    data_tier="TIER3",
    encrypted_blob=enc
)

store.put_object(obj)


# Scenario 1
print("\nScenario 1 — Tenant Isolation")

ctx = RequestContext(
    user_id="attacker",
    role="Agent",
    tenant_id="tenantB",
    purpose="lending_underwriting",
    serving_region="EU"
)

d, _ = gateway.handle(ctx, "view_document_content", "doc1")

print("Expected: tenant_mismatch")
print("Actual:", d.reason)


# Scenario 2
print("\nScenario 2 — Residency Proxy")

ctx = RequestContext(
    user_id="owner1",
    role="Owner",
    tenant_id="tenantA",
    purpose="lending_underwriting",
    serving_region="EU",
    client_region="US",
    via_proxy=False
)

d, _ = gateway.handle(ctx, "view_document_content", "doc1")

print("Expected: proxy_required")
print("Actual:", d.reason)


# Scenario 3
print("\nScenario 3 — Valid Access")

ctx = RequestContext(
    user_id="owner1",
    role="Owner",
    tenant_id="tenantA",
    purpose="lending_underwriting",
    serving_region="EU",
    client_region="US",
    via_proxy=True
)

d, data = gateway.handle(ctx, "view_document_content", "doc1")

print("Expected: allow")
print("Actual:", d.reason)


# Scenario 4
print("\nScenario 4 — Audit Chain")

print("Audit Valid:", audit.verify_chain())
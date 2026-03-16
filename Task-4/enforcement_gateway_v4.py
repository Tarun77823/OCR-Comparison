import time
from audit_ledger_v4 import AuditLedgerV4
from data_model_v4 import Decision

class EnforcementGatewayV4:

    def __init__(self, storage, kms, policy, audit):

        self.storage = storage
        self.kms = kms
        self.policy = policy
        self.audit = audit

        self.deps_ok_policy = True
        self.deps_ok_kms = True

    def handle(self, ctx, operation, object_id):

        obj = self.storage.get(object_id)

        grant = self.storage.get_grant(object_id, ctx.user_id)

        if not self.deps_ok_policy or not self.deps_ok_kms:
            return Decision.DENY("dependency_unavailable")

        decision = self.policy.evaluate(ctx,operation,obj,grant)

        if decision.allow and operation == "view_document_content":

            try:
                data = self.kms.decrypt(
                    obj.object_id,
                    obj.encrypted_blob,
                    ctx.serving_region,
                    obj.home_region
                )
            except:
                return Decision.DENY("kms_failure")

            return decision,data

        return decision,None
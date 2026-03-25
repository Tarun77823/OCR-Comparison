import time

from data_model_v4 import Decision
from audit_ledger_v4 import AuditEvent


class EnforcementGatewayV4:
    

    def __init__(self, storage, placement, kms, policy, audit):

        self.storage = storage
        self.placement = placement
        self.kms = kms
        self.policy = policy
        self.audit = audit

        self.deps_ok_policy = True
        self.deps_ok_kms = True

    def handle(self, ctx, operation, object_id=None):

        obj = None
        grant = None

        if object_id:
            obj = self.storage.get_object(object_id)

            if obj:
                grant = self.storage.get_grant(object_id, ctx.user_id)

        if not self.deps_ok_policy or not self.deps_ok_kms:

            decision = Decision.DENY("dependency_unavailable")

            self._log_event(ctx, operation, decision, obj)

            return decision, None
        decision = self.policy.evaluate(ctx, operation, obj, grant)

        if decision.allow and operation == "view_document_content":

            try:
                data = self.kms.decrypt(
                    obj.object_id,
                    obj.encrypted_blob,
                    ctx.serving_region,
                    obj.home_region
                )

            except Exception as e:

                decision = Decision.DENY("kms_failure")

                self._log_event(ctx, operation, decision, obj)

                return decision, None

            self._log_event(ctx, operation, decision, obj)

            return decision, data

        self._log_event(ctx, operation, decision, obj)

        return decision, None
    def _log_event(self, ctx, operation, decision, obj):

        event = AuditEvent(
            timestamp=time.time(),
            actor_id=ctx.user_id,
            role=ctx.role,
            tenant_id=ctx.tenant_id,
            operation=operation,
            decision="ALLOW" if decision.allow else "DENY",
            reason=decision.reason,
            object_id=obj.object_id if obj else None,
            request_id=ctx.request_id
        )

        self.audit.append(event)
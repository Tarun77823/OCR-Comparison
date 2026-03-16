import time
from data_model_v4 import Decision

class PolicyEngineV4:

    PURPOSE_RULES = {
        "leasing_application_review": {"view_document_content"},
        "lending_underwriting": {"view_document_content","export_document"},
    }

    def evaluate(self, ctx, operation, obj, grant):

        if obj.deleted:
            return Decision.DENY("object_deleted")

        if ctx.tenant_id != obj.tenant_id:
            return Decision.DENY("tenant_mismatch")

        if ctx.serving_region != obj.home_region:
            return Decision.DENY("wrong_region")

        if ctx.client_region and ctx.client_region != obj.home_region:
            if not ctx.via_proxy:
                return Decision.DENY("proxy_required")

        if ctx.user_id == obj.owner_id:
            return Decision.ALLOW("owner_access")

        if grant is None:
            return Decision.DENY("missing_grant")

        if grant.revoked:
            return Decision.DENY("grant_revoked")

        if ctx.purpose != grant.purpose:
            return Decision.DENY("purpose_mismatch")

        if operation not in grant.allowed_ops:
            return Decision.DENY("operation_not_allowed")

        return Decision.ALLOW("grant_valid")
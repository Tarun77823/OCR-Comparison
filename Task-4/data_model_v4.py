from dataclasses import dataclass, field
from typing import Optional, Set, Dict

@dataclass
class RequestContext:
    user_id: str
    role: str
    tenant_id: str
    purpose: str
    serving_region: str
    client_region: Optional[str] = None
    via_proxy: bool = False
    request_id: Optional[str] = None


@dataclass
class DataObject:
    object_id: str
    tenant_id: str
    owner_id: str
    home_region: str
    data_tier: str
    encrypted_blob: bytes
    deleted: bool = False


@dataclass
class ShareGrant:
    grant_id: str
    object_id: str
    agent_id: str
    purpose: str
    start_time: float
    end_time: float
    allowed_ops: Set[str]
    revoked: bool = False


@dataclass
class RequestPackage:
    request_id: str
    tenant_id: str
    owner_id: str
    purpose: str
    docs: Set[str] = field(default_factory=set)


@dataclass
class Decision:
    allow: bool
    reason: str

    @staticmethod
    def ALLOW(reason="allow"):
        return Decision(True, reason)

    @staticmethod
    def DENY(reason):
        return Decision(False, reason)
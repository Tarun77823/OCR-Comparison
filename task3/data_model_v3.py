from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DataObject:
    object_id: str
    data_tier: str          
    home_region: str         
    tenant_id: str
    owner_user_id: str

@dataclass(frozen=True)
class ShareGrant:
    grant_id: str
    object_id: str
    owner_user_id: str
    grantee_user_id: str
    purpose: str             
    start_ts: float
    end_ts: float
    revoked: bool = False

@dataclass(frozen=True)
class RequestContext:
    actor_user_id: str
    actor_role: str       
    actor_residency: str
    serving_region: str
    purpose: str

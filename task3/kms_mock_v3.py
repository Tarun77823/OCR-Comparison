from __future__ import annotations
import os, hashlib
from dataclasses import dataclass
from typing import Set

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class WrappedKey:
    region: str
    key_id: str
    wrapped_data_key: str

class KMSMock:
    def __init__(self):
        self._keys = {"us": "kms-us-001", "eu": "kms-eu-001", "apac": "kms-apac-001"}
        self._revoked_objects: Set[str] = set()

    def generate_data_key(self) -> str:
        return _sha(os.urandom(16).hex())

    def wrap(self, region: str, data_key: str) -> WrappedKey:
        key_id = self._keys[region]
        return WrappedKey(region=region, key_id=key_id, wrapped_data_key=_sha(f"{key_id}:{data_key}"))

    def revoke_object(self, object_id: str) -> None:
        self._revoked_objects.add(object_id)

    def can_decrypt(self, object_id: str, wrapped: WrappedKey, serving_region: str) -> bool:
        if object_id in self._revoked_objects:
            return False
        return wrapped.region == serving_region

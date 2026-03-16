import hashlib
import json
from dataclasses import dataclass
from typing import List, Optional


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_json(data) -> str:
    return json.dumps(data, sort_keys=True)


@dataclass
class AuditEvent:

    timestamp: float
    actor_id: str
    role: str
    tenant_id: str
    operation: str
    decision: str
    reason: str

    object_id: Optional[str] = None
    request_id: Optional[str] = None

    prev_hash: str = ""
    hash: str = ""


class AuditLedgerV4:
  

    def __init__(self):
        self.events: List[AuditEvent] = []

    def append(self, event: AuditEvent):

        prev_hash = self.events[-1].hash if self.events else ""

        event.prev_hash = prev_hash

        payload = canonical_json({
            "timestamp": event.timestamp,
            "actor_id": event.actor_id,
            "role": event.role,
            "tenant_id": event.tenant_id,
            "operation": event.operation,
            "decision": event.decision,
            "reason": event.reason,
            "object_id": event.object_id,
            "request_id": event.request_id,
            "prev_hash": prev_hash
        })

        event.hash = sha256(payload)

        self.events.append(event)

    def verify_chain(self) -> bool:
       

        prev_hash = ""

        for event in self.events:

            payload = canonical_json({
                "timestamp": event.timestamp,
                "actor_id": event.actor_id,
                "role": event.role,
                "tenant_id": event.tenant_id,
                "operation": event.operation,
                "decision": event.decision,
                "reason": event.reason,
                "object_id": event.object_id,
                "request_id": event.request_id,
                "prev_hash": event.prev_hash
            })

            expected_hash = sha256(payload)

            if event.prev_hash != prev_hash:
                return False

            if event.hash != expected_hash:
                return False

            prev_hash = event.hash

        return True
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import time

@dataclass
class Tombstone:
    object_id: str
    deleted_at: float
    reason: str

class DeletionManager:
    
    def __init__(self):
        self.tombstones: Dict[str, Tombstone] = {}
        self.cleanup_queue: List[str] = []

    def request_delete(self, object_id: str, reason: str = "erasure") -> None:
        self.tombstones[object_id] = Tombstone(object_id, time.time(), reason)
        self.cleanup_queue.append(object_id)

    def is_deleted(self, object_id: str) -> bool:
        return object_id in self.tombstones

    def run_cleanup_batch(self, max_items: int = 25) -> List[str]:
        processed = []
        while self.cleanup_queue and len(processed) < max_items:
            processed.append(self.cleanup_queue.pop(0))
        return processed

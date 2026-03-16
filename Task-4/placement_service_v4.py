import hashlib
from dataclasses import dataclass
from typing import List, Tuple


def stable_hash(value: str) -> int:
    
    h = hashlib.sha256(value.encode()).hexdigest()
    return int(h[:16], 16)


@dataclass
class PlacementResult:
    shard_id: str
    placement_version: str


class PlacementServiceV4:
    

    def __init__(self, shard_ids: List[str]):
        if not shard_ids:
            raise ValueError("Shard list cannot be empty")

        self.shards = shard_ids
        self.version = self.compute_version(shard_ids)

    def compute_version(self, shards: List[str]) -> str:
        joined = "|".join(sorted(shards))
        return hashlib.sha256(joined.encode()).hexdigest()[:12]

    def update_shards(self, new_shards: List[str]):
        
        if not new_shards:
            raise ValueError("Shard list cannot be empty")

        self.shards = new_shards
        self.version = self.compute_version(new_shards)

    def place_object(self, tenant_id: str, object_id: str) -> PlacementResult:
        

        best_score: Tuple[int, str] = (-1, "")

        for shard in self.shards:
            score = stable_hash(f"{tenant_id}:{object_id}:{shard}")

            if score > best_score[0]:
                best_score = (score, shard)

        return PlacementResult(
            shard_id=best_score[1],
            placement_version=self.version
        )
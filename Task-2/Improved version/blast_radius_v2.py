# blast_radius_v2.py
from common_infra_v2 import ACTIVE_SHARDS

TOTAL_USERS = 1_000_000
REGION_DISTRIBUTION = {"us": 0.40, "eu": 0.35, "apac": 0.25}
CELLS_PER_REGION = 32

def region_outage(region: str) -> int:
    return int(TOTAL_USERS * REGION_DISTRIBUTION[region])

def shard_outage() -> int:
    return int(round(TOTAL_USERS / len(ACTIVE_SHARDS)))

def cell_outage_estimate(region: str) -> int:
    return max(1, int(region_outage(region) / CELLS_PER_REGION))

def main():
    print("\nBlast Radius (first-order estimates)\n")
    print(f"Total users: {TOTAL_USERS:,}")
    print(f"Active shards: {len(ACTIVE_SHARDS)}")
    print(f"Cells per region: {CELLS_PER_REGION}\n")

    for r in REGION_DISTRIBUTION:
        ri = region_outage(r)
        ci = cell_outage_estimate(r)
        print(f"{r.upper()}: region={ri:,} | single-cell≈{ci:,} | reduction≈{ri/ci:.1f}x")

    print(f"\nSingle shard outage ≈ {shard_outage():,} users")
    print("cell estimate assumes uniform placement; hotspots can skew real impact.\n")

if __name__ == "__main__":
    main()

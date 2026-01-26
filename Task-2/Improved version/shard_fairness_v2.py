# shard_fairness_v2.py
from collections import Counter
from common_infra_v2 import ACTIVE_SHARDS, hrw_shard_for_user

def zipf_weights(n: int, s: float = 1.15):
    w = [1.0 / (k ** s) for k in range(1, n + 1)]
    z = sum(w)
    return [x / z for x in w]

def fairness_uniform(users: int = 100_000):
    counts = Counter()
    for i in range(users):
        uid = f"user-{i}"
        sid = hrw_shard_for_user(uid, ACTIVE_SHARDS)
        counts[sid] += 1

    avg = users / len(ACTIVE_SHARDS)
    mn = min(counts.values())
    mx = max(counts.values())

    print("\nShard Fairness \n")
    print(f"Users: {users:,} | Shards: {len(ACTIVE_SHARDS)} | Avg/shard: {avg:.2f}")
    print(f"Min: {mn} | Max: {mx} | Skew max/avg: {mx/avg:.3f}")

def fairness_zipf(users: int = 200_000, s: float = 1.15):
    user_to_shard = {}
    for i in range(users):
        uid = f"user-{i}"
        user_to_shard[uid] = hrw_shard_for_user(uid, ACTIVE_SHARDS)

    weights = zipf_weights(users, s=s)
    load = Counter()
    for i in range(users):
        uid = f"user-{i}"
        load[user_to_shard[uid]] += weights[i]

    avg = sum(load.values()) / len(ACTIVE_SHARDS)
    mn = min(load.values())
    mx = max(load.values())

    print("\nShard Load Skew \n")
    print(f"Users: {users:,} | Shards: {len(ACTIVE_SHARDS)} | Zipf s: {s}")
    print(f"Avg load/shard: {avg:.6f}")
    print(f"Min load/shard: {mn:.6f} | Max load/shard: {mx:.6f} | Skew max/avg: {mx/avg:.3f}")

    print("\nTop 5 busiest shards:")
    for sid, v in load.most_common(5):
        print(f"  {sid}: load={v:.6f}")

def main():
    fairness_uniform(100_000)
    fairness_zipf(200_000, s=1.15)

if __name__ == "__main__":
    main()

#Different phases
PHASES = [
    {"name": "Early",  "users": 100_000,   "regions": 1,  "req_per_user_per_day": 20},
    {"name": "Growth", "users": 5_000_000, "regions": 4,  "req_per_user_per_day": 25},
    {"name": "Global", "users": 50_000_000,"regions": 10, "req_per_user_per_day": 30},
]

# Simple assumptions
REQUESTS_PER_VCPU_PER_SECOND = 50    
SECONDS_PER_DAY = 86400

BASE_COST_PER_REGION = 1000           
REPLICATION_MULTIPLIER = 0.6     

def estimate_vcpus(total_requests_per_day):
    req_per_sec = total_requests_per_day / SECONDS_PER_DAY
    vcpus = req_per_sec / REQUESTS_PER_VCPU_PER_SECOND
    return max(1, int(vcpus) + 1)

def estimate_cost(regions):
    compute = regions * BASE_COST_PER_REGION
    replication = compute * REPLICATION_MULTIPLIER * (regions - 1) / max(1, regions) 
    total = compute + replication
    return int(compute), int(replication), int(total)

print("Scaling & Cost Analysis (rough model)\n")

for p in PHASES:
    total_requests = p["users"] * p["req_per_user_per_day"]
    vcpus = estimate_vcpus(total_requests)
    compute_cost, repl_cost, total_cost = estimate_cost(p["regions"])

    print(f"phase: {p['name']}")
    print(f"users: {p['users']:,}")
    print(f"Regions: {p['regions']}")
    print(f"Requests/day: {total_requests:,}")
    print(f"Estimated vCPUs needed: {vcpus}")
    print(f"Compute cost (units/day): {compute_cost}")
    print(f"Replication cost (units/day): {repl_cost}")
    print(f"Total cost (units/day): {total_cost}\n")

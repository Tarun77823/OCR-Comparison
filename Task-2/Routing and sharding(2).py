# This script simulates how requests are routed in a multi-region system

import random
from collections import Counter

# Available regions
REGIONS = ["US", "EU", "APAC"]

#  health status of regions
# EU is down to show failover behavior
region_health = {
    "US": True,
    "EU": False,
    "APAC": True
}

def route_request(request_type, nearest_region, home_region):
    """
    Routing rules:
    - READ  -> nearest healthy region
    - WRITE -> home region if healthy
    - If home region is down -> queue write
    """
    if request_type == "READ":
        if region_health.get(nearest_region):
            return nearest_region
    
        for region in REGIONS:
            if region_health.get(region):
                return region
        return "NO_REGION_AVAILABLE"

    else: 
        if region_health.get(home_region):
            return home_region
        return "QUEUE_WRITE"

def generate_random_request():
    request_type = "READ" if random.random() < 0.8 else "WRITE"
    nearest_region = random.choice(REGIONS)
    home_region = random.choice(REGIONS)
    return request_type, nearest_region, home_region

# Generate traffic
results = Counter()

for _ in range(1000):
    req_type, nearest, home = generate_random_request()
    destination = route_request(req_type, nearest, home)
    results[destination] += 1

print("Routing Simulation Results (1000 requests):\n")
for destination, count in results.items():
    print(f"{destination}: {count}")

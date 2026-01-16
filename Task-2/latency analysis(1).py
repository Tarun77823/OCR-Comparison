# This script shows how latency adds up across system components

scenarios = {
    "local_cache_hit": {
        "DNS": 20,
        "TLS": 30,
        "API_Gateway": 10,
        "Auth_Service": 8,
        "Cache": 2
    },
    "local_cache_miss": {
        "DNS": 20,
        "TLS": 30,
        "API_Gateway": 10,
        "Auth_Service": 8,
        "Cache": 5,
        "Storage": 40
    },
    "cross_region_call": {
        "DNS": 20,
        "TLS": 30,
        "API_Gateway": 10,
        "Auth_Service": 8,
        "Cross_Region_Network": 120,
        "Storage": 40
    },
    "edge_plus_region": {
        "DNS": 20,
        "TLS": 30,
        "Edge_Auth": 3,
        "API_Gateway": 10,
        "Regional_Cache": 5
    }
}

def total_latency(steps):
    return sum(steps.values())

print("Latency Analysis (ms)\n")

for name, steps in scenarios.items():
    print(f"Scenario: {name}")
    for step, time in steps.items():
        print(f"  {step}: {time} ms")
    print(f"  TOTAL: {total_latency(steps)} ms\n")

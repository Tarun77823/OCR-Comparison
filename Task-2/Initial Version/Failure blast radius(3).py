# This script analyzes how many users are affected during failures

TOTAL_USERS = 1_000_000

# User distribution across regions
REGION_DISTRIBUTION = {
    "US": 0.4,
    "EU": 0.35,
    "APAC": 0.25
}

def region_failure(failed_region):
    affected_users = int(TOTAL_USERS * REGION_DISTRIBUTION[failed_region])
    unaffected_users = TOTAL_USERS - affected_users
    return affected_users, unaffected_users

def service_failure(service_name):
    """
    Simulated impact of different service failures
    """
    if service_name == "AUTH":
        available_percent = 0.05  
    elif service_name == "VAULT":
        available_percent = 0.70 
    elif service_name == "METADATA":
        available_percent = 0.40
    else:
        available_percent = 0.90

    available_users = int(TOTAL_USERS * available_percent)
    impacted_users = TOTAL_USERS - available_users
    return available_users, impacted_users


print("Region Failure Analysis")
failed_region = "EU"
affected, unaffected = region_failure(failed_region)
print(f"Region Failed: {failed_region}")
print(f"Users Affected: {affected}")
print(f"Users not Affected: {unaffected}")

print("\nService Failure Analysis")
for service in ["AUTH", "VAULT", "METADATA"]:
    available, impacted = service_failure(service)
    print(f"\nService Down: {service}")
    print(f"Users still served: {available}")
    print(f"impacted Users: {impacted}")

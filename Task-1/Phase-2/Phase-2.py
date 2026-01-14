#importing Libraries
import math
#meausred from Phase-1
SECONDS_PER_IMAGE = 0.6638  # from timing summary
#Rough cost per overhead
OVERHEAD = 1.25
#Cost assumptions (rough)
CPU_COST_PER_VCPU_HOUR = 0.04      
API_COST_PER_IMAGE = 0.01          

SECONDS_PER_DAY = 86400

VOLUMES = [
    ("1/day", 1),
    ("1/min", 1 * 60 * 24),
    ("1,000/min", 1000 * 60 * 24),
    ("100,000/min", 100000 * 60 * 24),
]

def workers_needed(images_per_day: int) -> int:
    sec = images_per_day * SECONDS_PER_IMAGE * OVERHEAD
    return max(1, math.ceil(sec / SECONDS_PER_DAY))

def library_cost_per_day(workers: int) -> float:
    return workers * CPU_COST_PER_VCPU_HOUR * 24

def api_cost_per_day(images_per_day: int) -> float:
    return images_per_day * API_COST_PER_IMAGE

def flags(workers: int, api_cost: float) -> str:
    f = []
    if workers >= 500:
        f.append("BREAK: huge worker fleet")
    elif workers >= 50:
        f.append("WARN: many workers")
    if api_cost >= 100000:
        f.append("BREAK: API cost explosion")
    elif api_cost >= 1000:
        f.append("WARN: high API spend")
    return " | ".join(f) if f else "OK"

def main():
    print("\nPHASE 2-Cost & Scaling Reality\n")
    print("Measured from Phase-1")
    print(f"  seconds per image = {SECONDS_PER_IMAGE}")
    print("\nAssumptions(rough):")
    print(f"  overhead = {OVERHEAD}")
    print(f"  cost to use 1vcpu per hour = ${CPU_COST_PER_VCPU_HOUR}")
    print(f"  api cost per image = ${API_COST_PER_IMAGE}\n")

    print(f"{'Volume':12} {'Images/day':12} {'Workers':8} {'Library $/day':14} {'API $/day':14} {'Notes'}")
    print("-" * 74)

    for label, imgs_day in VOLUMES:
        w = workers_needed(imgs_day)
        lib = library_cost_per_day(w)
        api = api_cost_per_day(imgs_day)
        note = flags(w, api)
        print(f"{label:12} {imgs_day:<12,} {w:<8} ${lib:<13,.2f} ${api:<13,.2f} {note}")

if __name__ == '__main__':
    main()

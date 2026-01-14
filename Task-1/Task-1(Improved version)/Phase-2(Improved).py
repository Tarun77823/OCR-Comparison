import math
import os

# from Phase-1
SECONDS_PER_IMAGE = 0.6638
OVERHEAD = 1.25

# COSTS (rough)
CPU_COST_PER_VCPU_HOUR = 0.04
API_COST_PER_IMAGE = 0.01

SECONDS_PER_DAY = 86400

# scaling volumes
VOLUMES = [
    ("1/day", 1),
    ("1/min", 1 * 60 * 24),
    ("1,000/min", 1000 * 60 * 24),
    ("100,000/min", 100000 * 60 * 24),
    ("250M/day", 250_000_000),
]

# big worker model 
VCPU_PER_WORKER = 32        
EFFICIENCY = 0.85               

def per_vcpu_images_per_day() -> float:
    sec = SECONDS_PER_IMAGE * OVERHEAD
    return SECONDS_PER_DAY / max(sec, 1e-9)

def per_worker_images_per_day() -> float:
    # bigger worker handles more images/day
    return per_vcpu_images_per_day() * VCPU_PER_WORKER * EFFICIENCY

def workers_needed(images_per_day: int) -> int:
    cap = per_worker_images_per_day()
    return max(1, math.ceil(images_per_day / cap))

def library_cost_per_day(workers: int) -> float:
    # cost = workers * vcpu * hourly cost * 24 hours
    return workers * VCPU_PER_WORKER * CPU_COST_PER_VCPU_HOUR * 24

def api_cost_per_day(images_per_day: int) -> float:
    return images_per_day * API_COST_PER_IMAGE

def throughput_images_per_sec() -> float:
    # overall single vcpu throughput
    return 1.0 / max(SECONDS_PER_IMAGE * OVERHEAD, 1e-9)

def flags(workers: int, lib_cost: float) -> str:
    if workers >= 10000:
        return "BREAK: huge fleet (orchestration required)"
    if lib_cost >= 1_000_000:
        return "WARN: compute spend high"
    return "OK"

def print_orchestration_layer():
    print("\nOrchestration layer:")
    print("Storage: S3 / Azure Blob / GCS")
    print("Queue: SQS / PubSub / Kafka")
    print("Orchestrator: Airflow / Prefect / Step Functions")
    print("Workers: Kubernetes jobs / Batch / ECS")
    print("Result store: DB +logs")
    print("Dead-letter queue: bad images\n")

def main():
    print("\nPHASE 2 - Cost + Scaling + Orchestration\n")

    print(f"Measured:")
    print(f"  seconds/image = {SECONDS_PER_IMAGE}")
    print(f"  overhead = {OVERHEAD}")

    print(f"\nBig worker assumption:")
    print(f"  vCPU per worker = {VCPU_PER_WORKER}")
    print(f"  efficiency factor = {EFFICIENCY}")
    print(f"  images/day per worker ≈ {per_worker_images_per_day():,.0f}")

    # latency + throughput
    latency = SECONDS_PER_IMAGE * OVERHEAD
    tput = throughput_images_per_sec()
    print(f"\nPerformance:")
    print(f"  latency (sec/image) ≈ {latency:.3f}")
    print(f"  throughput (images/sec per vCPU) ≈ {tput:.2f}")

    print_orchestration_layer()

    print(f"{'Volume':12} {'Images/day':12} {'Workers':8} {'Library $/day':16} {'Notes'}")
    print("-" * 70)

    for label, imgs_day in VOLUMES:
        w = workers_needed(imgs_day)
        lib = library_cost_per_day(w)
        note = flags(w, lib)
        print(f"{label:12} {imgs_day:<12,} {w:<8} ${lib:<15,.2f} {note}")

if __name__ == "__main__":
    main()

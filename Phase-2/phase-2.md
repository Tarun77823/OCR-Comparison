# Phase 2 – Cost & Scaling Reality
# Purpose
The goal of Phase 2 is to understand how OCR systems behave when the volume increases, both in terms of cost and system design. This phase focuses on how scaling is not only a technical problem but also a cost and operational problem.

# Numbers from Phase 1
Images processed: 17
Total time: 11.29 seconds
Average time per image: 0.6638 seconds
I used this value for all caluculations below

# Assumptions:The numbers used below are approximate and are used only to understand trends.(ROUGH)
Overhead factor: 1.25 (queueing, retries)
# Library-first OCR:
1 worker = 1 vCPU
Cost assumed: $0.04 per vCPU-hour
# Managed Vision API:
Cost assumed: $0.01 per image
These are just reasonable assumptions.

# Cost Estimates at Different Volumes
Volume	               Images per day	               Library-first workers	             Library-first cost/day	                     Managed vision cost/day
1/day	                   1	                                       1	                                 $0.96	                                       $0.01
1/min	                   1,440	                                 1	                                 $0.96	                                       $14.40
1,000/min	             1,440,000                                14	                                 $13.44	                                    $14,400
100,000/min	             144,000,000	                           1,384	                              $1,328	                                    $1,440,000

# For workers i used the formula below:
workers ≈ (images per day × time per image × overhead) / seconds per day

# What Becomes Expensive First
Managed vision APIs become expensive first because the pricing is per image. As volume increases, the total cost grows very quickly.
Library-first OCR is cheaper per image, but at very high scale it requires a large number of workers, which increases infrastructure and maintenance cost.

# What Becomes Operationally Complex
Managing queues when images arrive faster than they can be processed
Autoscaling worker machines without causing delays
Handling retries and failures without duplicating results
Monitoring latency, error rates, and queue depth
Storing and managing a very large number of OCR outputs

# Where Each Approach Starts to Break
Managed vision starts to break from a cost perspective at high volume.
Library-first OCR starts to break from an operations perspective when the worker count becomes very large.

# Architecture Diagram (Phase 2)
[Client]
   |
   v
[Ingestion API]
   |-------------> [Reject / Validate Bad Files]
   v
[Image Storage]
   v
[Queue]
   |
   +--> [Worker Pool] --> [OCR Processing] --> [Results Storage]
   |                         |
   |                         +--> [Retry Queue]
   |                         |
   |                         +--> [Dead Letter Queue]
   |
   +--> [Monitoring & Alerts]

# Final Takeaways
At small scale, both approaches work fine.
At larger scale, cost, reliability, and operations become more important than just OCR accuracy.
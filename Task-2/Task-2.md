# Task 2 — Infrastructure & System Sharding at Global Scale (MeCentral)
### Executive Summary 
This document proposes a region-based infrastructure sharding strategy for MeCentral, supported by simulation-based analysis of latency, routing behavior, failure blast radius, and scaling cost. The design prioritizes low latency, strong failure isolation, operational simplicity, and incremental scalability. More complex architectures such as global active-active writes and cell-based systems are intentionally deferred to later stages to avoid unnecessary operational risk.


# Modeling Assumptions and Scope
The Python scripts used in this task are analysis tools, not production implementations.
-Latency values represent approximate, order-of-magnitude delays commonly seen in distributed systems.
-Cost values are expressed in arbitrary units to compare growth trends, not real cloud pricing.
-Traffic patterns and user distributions are simplified to make tradeoffs easier to reason about.
The purpose of these models is to support architectural decisions, not to provide exact capacity planning.


# Relationship to Task 1
Task 1 focused on analyzing performance and cost at the individual workflow level. Task 2 extends that work to a global context, examining how those workflows behave across regions under latency, failures, and scaling pressure. Insights from Task 1 directly informed decisions around caching, routing, and replication in this design.


### Part 1 - Latency Analysis
# What this part addresses
In global systems, latency is not just database access time. It is the sum of DNS resolution, TLS handshakes, gateway hops, service calls, caching behavior, storage access, and sometimes cross-region network calls.
# What was done
A Python script models multiple request scenarios:
-Local cache hit
-Local cache miss
-Cross-region dependency
-Edge validation with regional reads
# Key insight
Cross-region calls dominate end-to-end latency. Even when services are fast, a single synchronous cross-region dependency can add more delay than all local processing combined.
# This supports:
-routing users to the nearest region
-performing authentication and caching close to users
-avoiding synchronous cross-region calls on common request paths
# Supporting script:(<latency analysis(1).py>)


### Part 2 — Traffic Routing and Sharding 
# What this part addresses
When a request arrives, the system must decide:
-which region should handle it
-how to balance latency and correctness
-how to behave during failures
# Routing strategy analyzed
The routing simulation models the following rules:
-READ requests → nearest healthy region
-WRITE requests → user’s home region
-Home region unavailable → queue writes or enter read-only  mode
# Why this matters
Reads are typically safe to serve from multiple regions, while writes require a single source of truth to avoid conflicts and corruption. The simulation shows that this strategy preserves correctness while maintaining availability for read traffic.
# Supporting script:(<Routing and sharding(2).py>)


### Part 3 — Availability and Blast Radius
# What this part addresses
Failures are inevitable. The key question is how much of the system is affected when something breaks (blast radius).
# What was analyzed
Two categories of failures were simulated:
-Region failure — only users primarily served by that region are affected.
-Service failure — different services have different impact levels.
Authentication failures have the largest blast radius, while vault or metadata failures can allow partial functionality.
# Key insight
Strong isolation boundaries (regions, clusters, or cells) significantly reduce blast radius. Graceful degradation is far preferable to total system outages.
# Supporting script:(<Failure blast radius(3).py>)


### Part 4 — Scaling Trajectory and Cost 
# What this part addresses
Scaling is not only about handling more users. It also increases replication traffic, operational burden, and cost.
# What was done
A Python model estimates:
-request growth as users increase
-compute needs across phases
-replication overhead as regions increase
Three phases were analyzed:
-Early (10k–100k users)
-Growth (1M–10M users)
-Global (50M+ users)
# Key insight
Compute scales roughly with traffic, but replication and operational complexity scale with the number of regions. This supports adding regions gradually and keeping early architectures simple.
# Supporting script:(<scaling cost analysis(4).py>)


###  High-Level Infrastructure Layout 

User
  |
  v
Geo Routing (DNS / Anycast)
  |
  v
 -----------------------------
|        Region (US)          |
|                             |
|  Edge Auth + Cache          |
|        |                    |
|  API Gateway                |
|        |                    |
|  Core Services              |
|  (Auth, Vault, Metadata)    |
|        |                    |
|  Regional Cache             |
|        |                    |
|  Regional Storage           |
 -----------------------------
          |
          v
   Async Replication / Events
          |
------------------------------
|     Other Regions          |
------------------------------


### Security Considerations
Authentication and identity services are treated as critical dependencies because incorrect behavior can lead to unauthorized access or data leakage.
# To reduce latency without weakening security:
-Token validation can occur at the edge using signed tokens.
-Sensitive authorization and policy enforcement remain regional.
# During failures, the system should fail closed:
-block writes and sensitive operations rather than risk corruption
-treat identity records and audit logs as hard-state data requiring durable storage.
Control-plane access is tightly restricted, and cached configurations allow data-plane services to continue operating during control-plane outages.


### Design Decisions and Tradeoffs
Several alternatives were intentionally not chosen for the baseline design:
-Global active-active writes were avoided due to high consistency complexity and difficult failure handling.
-Cell-based architectures were deferred because they introduce significant operational overhead and are better suited for later stages.
-Synchronous cross-region dependencies were minimized due to their dominant impact on latency and failure coupling.
These choices prioritize clarity, predictable failure modes, and operational simplicity.

### Key Tradeoffs Summary
   # Decision	                                        Benefit	                                              Tradeoff
Regional sharding	                          Low latency, isolated failures	                        Replication complexity
Read-local routing	                                 Fast global reads	                                Eventual consistency
Write-home model	                                 Strong correctness	                           Slower writes during failover
Multi-layer caching	                            Performance and cost savings	                   Cache invalidation complexity
Deferred cell architecture	                          Simpler early ops	                           Less isolation than full cells


### Final Infrastructure Sharding Design Summary 
MeCentral should use a region-based infrastructure sharding model as its baseline.

Each region operates as a mostly independent unit, serving nearby users to minimize latency and containing failures within regional boundaries. Read requests are routed to the nearest healthy region, while write requests are routed to a user’s home region to preserve correctness. When the home region is unavailable, writes are safely queued or the system enters a controlled read-only mode.

Caching is applied at multiple layers (edge, regional, service-local) to reduce storage load and improve performance. Authentication and audit logging are treated as high-criticality components with strict failure behavior.

This design is realistic to operate, cost-aware, and provides a clear path to more advanced isolation models as the system grows.


### Future Work and Next Steps
If MeCentral continues to scale, future improvements would include:
-Introducing cell-based isolation for high-risk or high-traffic tenants
-Improving cross-region observability and tracing
-Defining formal SLOs and latency budgets
-Hardening control-plane safety and configuration management
-Evaluating selective active-active writes for low-risk data only
These decisions should be driven by real traffic patterns and incident data rather than theoretical optimization.
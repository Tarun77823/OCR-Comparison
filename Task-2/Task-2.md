# Task 2 — Infrastructure & System Sharding at Global Scale (Security-First)

## Executive Summary
At global scale, infrastructure sharding is not “split by region.” It’s a set of decisions about:
- **Correctness**: where authoritative writes land
- **Performance**: where reads are served
- **Security**: what fails closed vs what degrades
- **Blast radius**: how to prevent incidents from becoming global

This design uses:
- **Identity-based sharding** (stable user home shard for correctness)
- **Regions** for performance (read-local when safe)
- **Cells** as the primary isolation boundary (deployment + fault containment)
- **Tiered failure policy**: degrade only safe ops; fail closed for sensitive ops

Key principle:
> Shards protect correctness & security. Regions optimize performance. Cells bound blast radius.

---

## Assumptions (Explicit)
- Partial failures are normal (dependency outages, cell outages, region brownouts).
- Security-sensitive decisions require stronger consistency than general content.
- Compliance/data residency exists; routing must respect residency constraints.

---

## (1) Sharding Models: What Can Be Partitioned?
You can shard:
- **Traffic** (GSLB/DNS, anycast ingress)
- **Compute** (stateless services by region/cell)
- **State** (datastores; identity metadata; user content)
- **Control plane** (policy, placement metadata, deployment management)

### Model comparison
|           Model                 |                 Pros                     |                        Cons                                        |         
| Region-based sharding           | low latency locally                      | high blast radius, user travel breaks correctness, unsafe failover |
| Active-active global writes     | low latency writes                       | conflict resolution complexity, security + correctness hard        |
| Read-local                      | fast reads + correct writes              | writes may queue/fail if home unavailable                          |
| Cells                           | small blast radius, safe rollouts        | higher initial architecture discipline                             |

---

## (2) Latency: Where Time Goes
Latency drivers:
- handshake (TLS) + gateway
- cross-region RPC (dominant)
- cache misses and storage IO
- auth/policy checks

Rules:
- Verify tokens close to users (regional/edge)
- Serve non-sensitive reads from regional cache/replicas
- Route writes to the **user’s home shard**
- Keep policy/authz/session revocation on a strongly consistent path (or home)

---

## (3) Failure Domains and Isolation
We assume:
- cell failures, AZ failures
- dependency outages: auth, policy, risk engine, audit, KMS
- region outages

Isolation hierarchy:
Instance → AZ → **Cell** → Shard → Region → Global

Goal:
- incidents stop at **Cell** or **Shard**, not global.

---

## (4) Proposed Topology
User
|
Global DNS / GSLB
|
Nearest healthy Region
|
Ingress/API Gateway
|
Auth token verify + coarse rate limiting
|
Cell Router
|--- READ path: regional cache/replica (if residency allows)
|--- WRITE path: resolve home shard -> home cell -> primary DB


---

## (5) Efficient User Sharding (Identity-Based)
### Stable home shard
Assign once at creation time:
- **home_shard = HRW(user_id, ACTIVE_SHARDS)** (Rendezvous hashing)

Why HRW instead of modulo?
- `hash % N` reshuffles a huge fraction of users when N changes.
- HRW minimizes movement when adding/removing shards.

### Placement service (decouple “which shard” vs “where it lives”)
- Shard membership is stable (**ACTIVE_SHARDS**).
- Placement maps shard → region/cell and can change during evacuation/moves.

---

## (6) Cells as the Primary Blast Radius Boundary
- Each region is divided into many **cells**
- A cell is the deployment + monitoring + recovery boundary
- Shards are placed into cells; cell outage affects only shards in that cell

---

## (7) Security-First Failure Policy (Fail Closed)
We classify operations:

- **Tier-0**: public reads
- **Tier-1**: basic reads / low-value actions (can degrade with guardrails)
- **Tier-2**: PII, exports, permission changes, token issuance, high-value actions (fail closed)

### Dependency failure matrix
| Dependency Down | Tier-1 | Tier-2 |
|---|---|---|
| Auth | DENY | DENY |
| Policy | DENY | DENY |
| Risk engine | ALLOW degraded + coarse limits | DENY for sensitive/high-risk |
| Audit | allow safe reads only | DENY exports/perm changes |
| KMS | read-only if possible | DENY export/rotate/crypto |
| Placement | allow short cached routing | writes blocked if cache stale |

---

## (8) Write Unavailability Behavior (Home Unavailable)
- Writes do **not** reroute to other shards.
- If home cell down:
  - Tier-2 ops: **fail closed**
  - Tier-1 ops: **queue** with per-user FIFO ordering

Queue semantics:
- per-user FIFO
- TTL on queued events
- rate-limited drain on recovery
- idempotency required for writes
- queued events carry target shard + placement version

---

## (9) Data Residency
- Sensitive reads (PII/export) must not be served outside residency boundary.
- Read routing enforces residency: if serving region violates residency, route to home region.

---

## (10) Validation (Simulations)
Python simulations validate:
- blast radius (region vs cell vs shard)
- security gating across dependency failures
- degraded mode behavior (queue vs fail closed)
- sharding fairness (HRW distribution + traffic skew)
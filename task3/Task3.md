# Internship Task-3  
## Global Data Residency, Tiered Security Gating & Resilient Operations

## (1) Problem Statement — From First Principles

At the most basic level, any system does only two things:
-Store information  
-Retrieve information  

In a small, single-region system, this is trivial:  
data goes into one place, and the application reads it back.

At global scale, this model breaks down.

When users and data are distributed across regions, the system must now handle:

1. Latency — users are far from where data lives  
2. Scale — millions of users, billions of requests  
3. Security — not all data can be accessed by everyone  
4. Compliance — data belongs to the user, not the platform  

Modern regulations (GDPR-style data ownership, HIPAA-style access controls) require:

- Data to remain in specific geographic regions  
- Access to be purpose-limited and auditable  
- Immediate denial after deletion requests  
- Proof that enforcement decisions were actually applied  

Task-3 demonstrates how to design and enforce these guarantees without destroying system availability.

---

## (2) Why Task-1 Exists — Cost, Scale & Tiered Decisions

Task-1 focused on OCR processing and scaling reality.

It demonstrated that:
- Cost scales linearly with volume  
- Blindly using expensive AI everywhere does not scale  
- Systems must choose cheap paths first and escalate only when necessary 

This introduced three critical concepts:

1. Tiered decision making  
2. Confidence-based escalation  
3. Cost-aware architecture  

These ideas directly reappear in Task-3 as:
- Safe vs sensitive operations  
- Degraded-mode vs fail-closed behavior  
- Selective enforcement instead of global shutdowns  

---

## (3) Why Task-2 Exists — Global Routing & Failure Domains

Task-2 established the execution fabric required for Task-3.

It introduced:
- Deterministic sharding (HRW / rendezvous hashing)  
- Placement service with versioning  
- Read-local / write-home routing  
- Tier-based security gates  
- Degraded-mode queueing  
- Blast-radius reduction  

This allows the system to:
- Know where data lives 
- Know where requests must execute 
- Fail safely during partial outages  

Task-3 builds directly on this routing and dependency model.

---

## (4) Core Principle of Task-3

 Not all operations are equal.

A resilient system must distinguish between low-risk and high-risk actions.

### Safe operations (low risk)
- View balance  
- View transaction history  
- View basic profile  

### Sensitive operations (high risk)
- Transfer money  
- Add beneficiary  
- Export data  
- Change permissions  

During outages or dependency failures:

|        **Operation Type**        |        **Behavior**         |
| Safe reads                       |    Allowed (degraded mode)  |
| Sensitive operations             |    Denied (fail closed)     |

This ensures usability without violating trust or compliance.

---

## (5) Data Classification Model

Each data object is assigned a data tier:

| Tier                  | Meaning                      |
| DATA_TIER_0           | Public                       |
| DATA_TIER_1           | Low-risk personal data       |
| DATA_TIER_2           | Sensitive personal data      |
| DATA_TIER_3           | Regulated / highly sensitive |

Rules enforced:
- Tier-2 and Tier-3 fail closed.
- Tier-0 and Tier-1 may degrade
- Protecting sensitive data always takes priority over availability

---

## (6) Residency Enforcement

Sensitive data must remain in its home region.

Example:
- EU user data must be processed and decrypted only in the EU  

Enforcement is done by:
- Task-2 routing (home shard resolution)  
- Region-bound encryption keys  
- Explicit residency checks during enforcement  

Even with permission, data cannot be decrypted outside its home region.

---

## (7) Purpose-Based Access Control

Access is defined not only by who, but also by why.

Each request declares a purpose, such as:
- lending  
- payment  
- operations  

Rules:
- Grants are time-bounded  
- Grants are purpose-bound  
- Only minimum-necessary operations are allowed  

This prevents:
- Over-privileged access  
- Lateral data misuse  
- Silent scope expansion  

---

## (8) Degraded Mode vs Fail-Closed Behavior

The system supports two execution modes:

### Degraded Mode
- Used for safe reads  
- Maintains usability  
- No irreversible changes  

### Fail-Closed Mode
- Used for sensitive operations  
- Blocks execution when dependencies are unhealthy  
- Preserves security and compliance  

---

## (9) Deletion & Crypto-Erasure

When a user requests deletion:

1. A tombstone is written immediately  
2. All future access is denied  
3. Derived data is cleared  
4. Encryption keys are rendered unusable  

This guarantees:
- Immediate compliance  
- No data resurrection  
- Safe background cleanup  

---

## (10) Auditability & Evidence

Every decision (ALLOW or DENY) is written to a tamper-evident audit ledger.

Each audit event includes:
- User, role, purpose  
- Operation and decision  
- Region, shard, placement version  
- Cryptographic hash linking to the previous event  

The audit chain is verifiable and immutable.

---


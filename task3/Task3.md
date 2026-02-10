# Task-3 — Global Data Residency, Compliance & Tiered Resilience
##  Executive Summary

At small scale, systems are simple: data goes in, data comes out.

At global scale, this breaks due to:
- Latency (distance between users and data)
- Scale (volume of users and requests)
- Security (fraud, insider risk, abuse)
- Compliance (GDPR, HIPAA, financial regulations)

This design demonstrates how real production systems handle these constraints by:
- Separating safe reads from sensitive operations
- Enforcing data residency at runtime
- Failing closed for high-risk actions
- Remaining usable during partial outages
- Producing tamper-evident audit evidence
- Supporting right-to-erasure without breaking the system

All concepts are backed by working code + tests, and are built directly on Task-1 and Task-2.

## 1. Why Task-1 and Task-2 exist

### Task-1 → Local-First, Confidence-Based Decisions
Task-1 established:
- Local processing first
- Escalation only when confidence is insufficient
- Cost-aware scaling

Task-3 applies the same idea:
- Serve low-risk reads locally
- Escalate high-risk actions to stricter enforcement
- Deny when confidence (policy, audit, KMS, risk) is insufficient

### Task-2 → Infrastructure Foundation
Task-3 directly uses Task-2 primitives:
- HRW shard assignment
- Placement service (shard → region / cell)
- Router returns (shard_id, placement_version)
- Dependency health gates
- Degraded-mode routing

**Task-3 answers why Task-2 matters**:
- Compliance enforcement is impossible without correct routing, placement evidence, and controlled degradation.

## 2. Data Classification & Risk Model

| **Tier**                       | **Description**                               |
|--------------------------------|-----------------------------------------------|
| DATA_TIER_0                    | Public / non-sensitive data                   |
| DATA_TIER_1                    | Low-risk user data (profiles, balances)       |
| DATA_TIER_2                    | Sensitive personal data                       |
| DATA_TIER_3                    | Regulated data (financial, medical, identity) |


## 3. Residency & Compliance Rules 

| **Tier** | **Storage**                   | **Who May Access**     | **Time Bounds**         | **Retention & Deletion** |
|----------|-------------------------------|------------------------|-------------------------|--------------------------|
| T0       | Global replication            | Anyone                 | None                    | Cache TTL                |
| T1       | Multi-region read replicas    | Authenticated users    | Short policy TTL        | Remove read models       |
| T2       | Stored in home region         | Owner                  | Time-bounded grants     | Tombstone                |
| T3       | Home region only              | Owner                  | Strict windows          | Tombstone                |

**Key Rule:**  
T2 and T3 fail closed when compliance dependencies are unavailable.

## 4. Tiered Operations Model (Banking Example)

### Allowed During Partial Outage (Tier-1)
- view_balance
- view_transaction_history
- view_profile_basic

### Blocked During Partial Outage (Tier-2)
- transfer_money
- add_beneficiary
- export_data
- change_permissions

**Reasoning:**  
User experience is preserved while preventing fraud or regulatory violations.

## 5. Architecture & Enforcement Points (ASCII Diagram)
Client
|
[Edge / Gateway]
|-- auth (must succeed)
|
|-- Tier-1 Safe Reads ------------------> [Read Models]
| (replicated, local)
|
|-- Tier-2 Sensitive Ops --> [Policy Engine]
|
v
[Residency Gate]
|
[Task-2 Router]
(shard_id + placement_version)
|
[KMS Region Gate]
|
[Home-Region Storage]

ALL allow/deny decisions →
[Audit Ledger]
(hash-chained, immutable)

## 6. Audit Event Schema

### Event Types
- CREATE / UPLOAD
- READ
- EXPORT
- SHARE_GRANT
- SHARE_REVOKE
- DELETE_REQUESTED
- DELETE_COMPLETED
- POLICY_CHANGE
- KEY_REVOKE

### Required Fields
- event_id
- timestamp
- actor_id / actor_role
- object_id
- data_tier
- home_region
- serving_region
- shard_id
- placement_version
- purpose
- decision (ALLOW / DENY)
- reason
- policy_version
- prev_hash
- hash

### Integrity Guarantee
- Events are hash-chained
- Any modification breaks verification
- Chain validation enforced by tests

## 7. Deletion & Right-to-Erasure

Deletion is handled safely using:
1. Tombstone → immediate deny
2. Derived cleanup → indexes, embeddings, OCR outputs
3. Crypto-erasure → KMS key invalidation

This ensures deleted data cannot be resurrected from backups.

## 8. Tradeoffs

### Performance
- Home-region enforcement increases latency
- Read replicas mitigate UX impact

### Cost
- KMS, audits, routing metadata add overhead
- Accepted cost for compliance

### UX
- Sensitive actions blocked during outages
- Safer than allowing violations

### Operational Complexity
- Requires consistent placement metadata
- Requires strict audit hygiene

## 9. MVP Recommendation

### Implement First
1. Tiered operation gating
2. Residency enforcement
3. Audit schema + hash chaining
4. Tombstone deletion

### Defer
- Fine-grained ABAC policies
- Jurisdiction-specific retention rules
- Multi-party approvals

## 10. Scenario Walkthroughs (Required)

### Scenario 1 — EU Owner → US Lender
- Data is DATA_TIER_3, home = EU
- US access denied locally
- Allowed only via EU proxy
- KMS decrypt allowed only in EU
- Audit logs shard + placement_version


### Scenario 2 — US Patient → Medical Clinic
- Purpose = treatment
- Minimum-necessary access enforced
- Export and resharing denied
- Access time-bounded and audited

### Scenario 3 — Property Management (3 Agents)
- Tenant boundary enforced
- Agents share within tenant only
- Cross-property access denied
- Audit ties access to tenant_id

### Scenario 4 — Storage Breach
- Attacker gets encrypted blobs only
- No KMS unwrap outside region
- Crypto-erasure prevents decrypt
- Evidence exists in audit + KMS logs

## 11. Code & Execution
python -m task3.scenario_runner_v3
python -m task3.tests_v3

## Final Statement
This system reflects how real banking, healthcare, and regulated SaaS platforms are built:

- Availability without recklessness
- Security without total outages
- Compliance enforced by architecture, not documents
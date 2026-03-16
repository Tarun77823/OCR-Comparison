## Task 4 — Tenant Isolation, Request Package Sharing, and Residency-Safe Proxy Access
## 1. Overview

Task-4 extends the system designed in Task-1, Task-2, and Task-3 by implementing secure sharing of sensitive documents while preserving strong tenant isolation and compliance guarantees.

The system simulates a multi-tenant document platform such as a property management, lending, or compliance system where documents must be securely shared between parties like property owners, agents, and lenders.

This task introduces several new capabilities:

• strict tenant isolation enforcement
• request package sharing workflows
• residency-safe proxy access for cross-region sharing
• revocation and deletion guarantees
• tamper-evident auditing

The architecture builds directly on previous tasks:

Task-1 introduced document ingestion and OCR routing.
Task-2 introduced multi-tenant storage and shard placement.
Task-3 introduced policy enforcement, residency rules, and cryptographic deletion.

Task-4 integrates those capabilities into a secure document sharing architecture.

## 2. System Architecture

All requests pass through a single Enforcement Gateway which acts as the security control point.

Client / API
     |
     v
+-----------------------------+
| Enforcement Gateway         |
|-----------------------------|
| Authentication              |
| Tenant Isolation Gate       |
| Policy Engine               |
| Residency Enforcement       |
| Placement Service           |
| KMS Decryption Gate         |
| Audit Logging               |
+-----------------------------+
             |
             v
      +------------------+
      | Storage Layer    |
      | (Sharded)        |
      +------------------+
             |
             v
        Encrypted Objects

This architecture ensures that all sensitive operations pass through a single enforcement boundary.

## 3. Data Model
RequestContext

Every request carries a context object describing the caller and environment.

Fields include:

user_id – identity of the caller
role – user role (Owner, Agent, Lender)
tenant_id – tenant boundary
purpose – reason for access
serving_region – region where enforcement runs
client_region – geographic location of the caller
via_proxy – indicates proxy-routed request
request_id – optional request package identifier

The RequestContext ensures that every decision is evaluated with full security information.

DataObject

Represents a stored document.

Fields include:

object_id
tenant_id
owner_id
home_region
data_tier
encrypted_blob
deleted

Each document belongs to a single tenant and a single home region.

ShareGrant

Represents a temporary permission to access a document.

Fields include:

grant_id
object_id
agent_id
purpose
start_time
end_time
allowed_operations
revoked

Share grants enforce time-bound and purpose-bound access control.

RequestPackage

A RequestPackage groups multiple documents for sharing.

Example workflow:

Owner creates a request package

Owner adds documents to the package

Owner creates a share grant for an agent or lender

The recipient accesses the documents through the package

This allows secure sharing of multiple documents within a single controlled workflow.

## 4. Tenant Isolation

Tenant isolation is enforced as a strict security boundary.

Rule:

If the request tenant does not match the object tenant, access is denied.

Example:

Tenant A attempting to access a document belonging to Tenant B will always be rejected even if a share grant exists.

This rule ensures that data belonging to one tenant can never be accessed by another tenant.

## 5. Data Residency Enforcement

Sensitive data must only be accessed from its designated region.

Rule:

The serving region must match the object home region.

Example:

A document stored in the EU region cannot be directly served from a US region gateway.

This protects compliance with regulations such as GDPR and regional data sovereignty requirements.

## 6. Residency-Safe Proxy Access

Cross-region sharing is supported using a residency-safe proxy architecture.

Example scenario:

An EU property owner needs to share documents with a US lender.

Instead of serving the document in the US region, the request is routed to the EU enforcement gateway.

Request parameters:

client_region = US
serving_region = EU
via_proxy = True

The document remains in the EU region while still allowing the lender to access the document through controlled proxy routing.

This design preserves residency guarantees while enabling legitimate cross-region collaboration.

## 7. Purpose-Bound Access Control

Every request must declare a valid purpose.

Examples:

leasing_application_review
lending_underwriting
treatment

Each purpose allows a specific set of operations.

Example:

leasing_application_review allows viewing document content.

lending_underwriting allows viewing and exporting documents.

If the request purpose does not match the grant purpose, access is denied.

This enforces the principle of minimum necessary access.

## 8. Encryption Model

The platform uses envelope encryption.

Encryption process:

A Data Encryption Key (DEK) encrypts the document.

The DEK is encrypted using the KMS master key.

Storage contains only encrypted data and wrapped keys.

This ensures that storage compromise does not expose plaintext data.

## 9. Crypto-Erasure

Deletion and revocation are implemented using cryptographic erasure.

When access must be revoked:

the encryption key is revoked.

Without the key, encrypted data becomes permanently unreadable.

This mechanism provides strong guarantees for:

secure deletion
breach containment
compliance enforcement

## 10. Key Rotation

Encryption keys can be rotated periodically to improve security.

Key rotation process:

Generate a new encryption key

Re-encrypt the document

Store the updated encrypted object

Regular key rotation reduces long-term cryptographic risk.

## 11. Degraded Mode Security

The system remains secure even when certain components fail.

If security dependencies become unavailable, the system fails closed for sensitive operations.

Example behavior:

If the policy engine becomes unavailable, Tier-2 and Tier-3 operations are denied.

If the KMS service is unavailable, sensitive reads are blocked.

Tier-1 metadata reads may remain available for system visibility.

This ensures that system failures do not compromise security.

## 12. Idempotency

Mutation operations support idempotency keys to prevent duplicate operations caused by retries.

For example:

create_share_grant can include an idempotency key.

If the same request is retried, the system returns the original result instead of creating a duplicate grant.

This prevents accidental duplication of access permissions.

## 13. Audit Ledger

Every operation is recorded in a tamper-evident audit log.

Each audit entry contains:

actor identity
operation performed
decision (allow or deny)
object identifier
region information
timestamp

Audit entries are chained using cryptographic hashes.

Each entry includes the hash of the previous entry, forming an append-only chain.

This ensures that any tampering with audit history can be detected.

## 14. Security Scenarios Tested

The system is validated through several scenarios.

Scenario 1: Tenant Isolation
A user from a different tenant attempts to access a document.
The request is denied.

Scenario 2: Residency Proxy Access
A US lender accesses an EU document through the proxy model.
Access is allowed only when routed through the EU enforcement gateway.

Scenario 3: Grant Revocation
A share grant is revoked.
Subsequent access attempts are denied.

Scenario 4: Storage Breach Simulation
An attacker obtains encrypted storage blobs but cannot decrypt them without KMS keys.

## 15. Execution Instructions

To run the demonstration scenarios:

python scenario_runner_v4.py

To run automated tests:

python tests_v4.py

These scripts simulate sharing workflows, tenant isolation checks, and residency enforcement.
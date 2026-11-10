---
document_feature_design:
  schema_version: 1
  role: primary
  source_inventory: "#source-inventory"
---

# ADR: retain export notifications in a database outbox

| Field | Value |
| --- | --- |
| Decision status | Proposed; no acceptance evidence supplied |
| Implementation status | Unknown; no repository supplied |
| Deployment status | Unknown; no deployment evidence supplied |
| Decision date | Unknown |
| Last verified | 2026-11-10T14:54:11+00:00; teaching fixture version 1 |
| Owners | Unknown |
| Source roots | Supplied teaching proposal, version 1 |
| Source baseline | Retained proposal linked in the source inventory |

## Overview

An export becoming ready must leave a notification obligation that survives a
process crash. The proposal is to store that obligation beside the export in a
database outbox, then let a background sender deliver it. This document is a filled
teaching example, not an accepted decision or a claim about deployed software.

## Architectural reference

**Decision and rationale:** propose committing the export's ready state and its
outbox row in the same transaction. Durability across the commit-to-send gap is the
dominant criterion. A sender then retries using a stable idempotency key. This
provides a durable retry obligation; exactly-once delivery remains unestablished
because the provider's deduplication behavior is unknown.

**Alternatives and consequences:** an in-process callback is simpler but can lose
the notification after a crash. A managed broker could support later scale, but
adds infrastructure and still needs a reliable database handoff. The outbox adds
polling, retry and cleanup responsibilities. These comparisons come from the
proposal; no historical approval or performance measurement is inferred.

**Validation and revisit conditions:** planned checks should crash the process
after the transaction and verify eventual sending, then retry an ambiguous provider
response to establish duplicate behavior. No tests have been executed for this
fictional service. Revisit the choice if measured backlog fails the notification
objective or a shared messaging service changes the operating cost. A numerical
throughput threshold and the provider guarantee require further evidence.

## Evidence status and gaps

### Source inventory

The retained [proposal, version 1](proposal.md) supplies the durability requirement,
approach, alternatives and revisit triggers. It is the complete source for this
repository-free example. Source verification for this example: 2026-11-10T14:54:11+00:00.
Retained proposal SHA-256: `b0ba4d10ca4dfbeea8149eac30ea83b1412aa20d68de6648672dcc1b6362db0b`.

Approval, implementation, deployment, ownership and provider deduplication remain
unknown. Assign an owner before accepting the decision. If accepted later, retain
its rationale while updating implementation facts; a changed choice needs a
superseding decision under the destination's ADR conventions.

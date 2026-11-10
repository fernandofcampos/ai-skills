# Export notification proposal, version 1

This is a fictional teaching fixture, not a real project decision.

The export service should create a durable notification obligation when an export
becomes ready. The proposed approach writes the export's ready state and an outbox
row in one database transaction. A background sender submits notifications with a
stable idempotency key and retries transient failures.

The required outcome is eventual notification after a committed ready transition,
including a process crash before sending. Duplicate requests to the provider are
possible. Whether the provider deduplicates them has not been established.

An in-process callback is simpler but loses the obligation on a crash. A managed
message broker is another option but would add infrastructure and still needs a
reliable handoff from the database. No throughput requirement or benchmark is
supplied. Revisit the database outbox if measured backlog cannot meet the eventual
notification objective or an existing shared messaging service removes its costs.

This is a proposal awaiting a decision. No implementation repository, approval or
deployment evidence is supplied. The owner of the decision and document is unknown.

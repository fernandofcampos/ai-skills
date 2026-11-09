# Reusable architecture and review handoff

The design owns definitions, accepted rationale, the review map, invariants and
scenario definitions. The review record owns questions, independent evidence,
dispositions and material differences for a particular source and criteria snapshot.
Neither artifact substitutes for reading authoritative requirements or code.

## Reuse by reference

Record the design's path and immutable revision/blob or retained content hash,
then link only the applicable sections or stable IDs. Check relevant entry points,
contracts and one representative path at the reviewed source snapshot. A concise
applicability statement is enough when they still fit. Keep the design's original
baseline; do not relabel it as the PR head or rewrite it to make reuse appear fresh.

Reuse map/unit IDs where useful. A review overlay needs only the definition link,
review-specific question, affected paths, evidence locator and disposition. It
does not reproduce purpose, dependencies, invariants, starting states and expected
outcomes already defined in the design. Record a changed scenario's delta beside
its link. Each changed path still needs precise evidence in the canonical inventory.
Independent verification means testing claims against source, not rewriting them.

A small context gap can be resolved with a provisional paragraph in the review
record in either mode: state the bounded question, observed path/ownership,
source evidence, assumption and remaining uncertainty. Label it descriptive and
provisional, never an accepted design decision. Use the companion for a material
architectural gap that needs durable explanation or an explicit documentation
deliverable. Provisional context cannot waive deep investigation or challenges.

## Criteria and context freshness

Treat the review baseline as both **source snapshots and criteria snapshots**.
For material requirements and decisions, retain the relevant content (or an
accessible immutable version), authority/status, source link, version/content hash
and retrieval time. A timestamp or mutable URL by itself does not preserve the
criteria used. A bounded excerpt with enough surrounding decision context is
sufficient; do not archive an entire private ticket collection unnecessarily.
Keep snapshots in the source inventory or review record once, and link them.

On every resumption, and before the final verdict, refresh material accepted
requirements and architectural context independently of Git changes. Compare the
actual content and authority with the retained version. A new proposal, resolved
comment or author's explanation is not automatically an accepted decision. When
authority is ambiguous, retain the proposal and the exact unresolved decision;
when refresh is unavailable, report the last verified criteria and the coverage
limit instead of asserting that nothing changed.

Record a brief change assessment: previous/current criteria identity, accepted
change or proposal, affected conclusions/units/scenarios, and retained conclusions
with a reason. Reopen only affected investigation and integration evidence. An
accepted change can invalidate a verdict at an unchanged Git head; this is criteria
drift, not necessarily a regression introduced by the PR. Do not overwrite the
previous verdict or historical acceptance record. Unaffected requirements and
source evidence can be reused with explicit applicability reasoning.

For source-only follow-up revisions, use a fresh exact inventory, inspect the
delta and affected consumers, and transfer unaffected evidence with its original
snapshot plus rationale. Unchanged bytes alone are insufficient. No broader design
rewrite or repeated whole-review pass is needed when the remaining obligations
are resolved. Stop after the bounded reassessment and qualified verdict.

# Behavioral depth for consequential or very large changes

Read after selecting `deep` investigation. Keep Astra/xhigh as the single lead
and focused reviewers under the shared model policy. Apply these requirements
within the review workflow, retaining valid evidence on follow-up passes.

## Define the investigations

Identify the critical behavioral boundaries from the actual change and its
unchanged consumers. A boundary is an enforceable contract across state, components
or external effects, not a directory. For each, record its paths/symbols, invariant,
owner, concrete failure hypothesis, assumptions being challenged, and evidence
needed to resolve the question. Use stable IDs and the
[investigation template](../assets/behavioral-investigation-template.md).

Choose relevant cases, such as concurrent ownership, partial persistence, stale
authorization, ambiguous external effects, compatibility, accounting limits and
release of retained obligations. Examine alternative event orderings and boundary
values where they matter. Do not impose a catalog of payment/recovery scenarios
on unrelated changes. Follow the actual callers and guards at base and head;
distinguish an unreachable state from one the current admission path accepts.

For each relevant admitted input class, establish the promised successful outcome
and trace it through selection/routing and execution. Test compatibility and
availability separately from safety: a safe refusal can still violate that
contract. Include the authority for expected behavior and distinguish unsupported
inputs, supported inputs that regress, and requirements-dependent cases. A
negative-only test does not demonstrate that any valid input can succeed.

Separate author-provided regression evidence from independent investigation.
Read the test assertions and fixture assumptions: what state is pre-seeded, which
component is mocked, what ordering is assumed, and what missing negative case
could invalidate the contract? A targeted experiment should challenge that
assumption through the connected path when practical. Use a positive control to
rule out unrelated setup failures. A source trace is sufficient when it resolves
the hypothesis; tests are not a quota. Record defect hypotheses as supported,
refuted by a specific guard/trace, or inconclusive. No finding is a valid outcome.

Budget review attention explicitly for these investigations and lead integration.
Environment setup and CI checks support this work; running more existing suites
does not discharge it. Do not shrink necessary investigation to hit an arbitrary
duration. Respect user time/scope limits and report partial depth when they bind.

## Work in bounded batches

A batch should resolve one contract or a small connected group and produce an
inspectable checkpoint before the reviewer takes on another question. Size it by
reasoning complexity, uncertainty and context use, not a fixed number of files.
Split work when a packet mixes independent contracts, repeatedly truncates source,
or cannot preserve a useful handoff before a context reset. Large classes may need
several batches; several mechanical files may share one explained transformation.

Record the actual file-to-symbol/scenario mapping, outcome, evidence, unread
regions and next step. Keep the lead's central inventory authoritative. Incremental
handoffs make interruption recoverable and let available reviewers take unfinished
independent batches without repeating completed investigation.

## Independent challenge pass

For every critical boundary in a deep review, require a separate challenge after
the primary investigation. It is targeted falsification of the contract, not a
second vote or another general scan of every file. A challenge must identify an
assumption and try to disprove it through a different relevant ordering, input,
consumer or failure condition; re-running the same regression is insufficient.

When delegation is available, assign a fresh reviewer for that boundary. Prefer a
fresh context with raw code, exact snapshots, authoritative requirements, neutral
contract/question and validation resources. Initially withhold the primary
findings and proposed conclusions to reduce anchoring. Never withhold known
execution hazards, access limits or safety constraints. Record what was withheld
and any reason independence was limited. After its initial independent result is
saved, share earlier findings for lead-led reconciliation and deduplication.

Reuse freed capacity sequentially rather than creating an additional permanent
team. A reviewer may challenge a different boundary it did not primarily review;
record any prior exposure. The lead retains integration and independently verifies
candidate findings. If tools, capacity or explicit user constraints prevent a
fresh reviewer, the lead conducts a separately recorded challenge pass and states
that it is not independent review. If even that pass cannot be completed, retain
a partial review. Do not silently drop the challenge obligation or start a second
lead. If challenge results expose new contracts or inadequate primary work, reopen
only the affected batches and integration scenarios.

## Completion gate

Before claiming comprehensive completion, the lead verifies:

- Every material changed area is accounted for, with explicit mapping for grouped
  evidence and no unresolved truncated source region.
- Every identified critical boundary has a resolved primary investigation and
  challenge, with hypothesis, challenged assumption, actual evidence, outcome and
  lead verification. Evidence should distinguish source reasoning, existing tests
  and new experiments. Inspect the boundary inventory itself for omissions.
- Material uncertainty and conflicting requirements are resolved or the verdict
  explicitly remains partial. A verified open defect does not prevent review
  completion; an inconclusive required investigation does.
- Admitted-but-refused cases have a functional disposition backed by requirements,
  an explicit compatibility decision, or an unresolved question. Safety alone
  cannot close them; relevant existing discussions are reconciled after blind work.
- Cross-unit scenarios are checked directly by the lead, with no blanket transfer
  of coverage from successful tests or worker completion messages.

Use the [run manifest](run-record.md) to preserve these obligations and validate
their structure. A helper can detect missing recorded investigations, but cannot
discover omitted boundaries or judge whether an experiment challenges the right
assumption. A low finding count, even zero, neither proves shallow review nor
justifies repeating reviews until more defects appear. Completion depends on the
investigation evidence and honest remaining limits.

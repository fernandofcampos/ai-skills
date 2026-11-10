<!-- Review narrative. Adapt and remove instructions/placeholders. Keep local by
default. run.json embeds authoritative per-file status; avoid a second conflicting file list.
For a different coverage format, retain the same snapshot and evidence semantics.
Link canonical snapshots, configuration and timing instead of repeating them.
Omit unused tables; preserve applicable evidence on focused follow-ups. -->

# [PR or change]: review record

## Snapshot and scope

- **PR / repository:** [Identity, local source root, and PR link when available]
- **Target base / comparison base / head:** [Exact revisions; one set per repository]
- **Verified at and freshness source:** [Time with timezone; host metadata or local-only limitation]
- **Requested scope and delivery:** [Entire PR or named subset; local report or authorized publication]
- **Coverage record:** [Link to canonical run.json embedded inventory, or justified equivalent comparison]
- **Run manifest / installed versions:** [run.json or equivalent skill/template/helper hashes captured at start; conditional references actually used; do not relabel earlier versions]
- **Lead routing check:** [Current-task role, model/effort configuration source; reuse current Astra/xhigh or existing lead, or specific reason delegation was necessary]

- **Latest committed checkpoint / record method:** [Canonical run path, receipt ID/revision; helper or manual fallback, preserved prior record and reason; discrepancies or uncommitted handoffs remain explicit]

## Scope and reassessment history

- **Scope / assessment:** [Concrete impact, interactions, uncertainty and explicit user limits; investigation depth is independent of delegation and coverage completion]
- **Previous review / preserved record:** [Initial review, or prior record/version link retained before reassessment]
- **Reassessment:** [Time, exact comparison, changed sources/criteria, newly discovered evidence and required investigation; or initial assessment]
- **Evidence carried forward / reopened:** [Valid checkpoints retained with reason; affected claims, callers, scenarios and gaps reopened; fresh inventory and prior snapshot link if revisions changed]
- **Investigation depth:** [standard / deep with actual behavioral evidence; very large interacting behavior and insufficient prior depth require deep; mechanical volume alone does not]

## Linked requirements and decisions

| Ticket / document and link | Immutable version or retained content/hash / retrieval time | Read status and reason | Requirements / acceptance criteria / decision authority | Review units / evidence / remaining gap |
| --- | --- | --- | --- | --- |
| [Relevant linked source, or explicitly no relevant links] | [Identifiable source snapshot] | [Read / unavailable / unread / outside scope, with reason] | [Actual content; distinguish accepted decisions, proposals and descriptions] | [Where checked and what remains unverified] |

[Read relevant sources even when a marked design supplies enough architecture.
Follow additional links only when material. PR paraphrases do not establish ticket
coverage. Record unavailable sources without blocking independent code review.]

| Existing review collection / thread | Retrieved time / pagination / read status | Initial blind result if applicable | Disposition at reviewed head / evidence / remaining question |
| --- | --- | --- | --- |
| [Review threads including material resolved/outdated replies, review summaries and PR comments] | [Complete / unread remainder / unavailable; private review still reads discussions] | [Saved initial pass before exposure, or ordinary review] | [Valid / fixed / duplicate / rejected / unresolved; author claims checked against source and decision authority] |

## Architectural context

- **Sources / decisions:** [Authoritative links and revisions or identifiable snapshots; separate accepted decisions from descriptive drafts]
- **Discovery and reuse:** [Marked primary path and blob/revision, schema version, applicability evidence and context work skipped; or ordinary discovery/fallback reason. A marker alone does not establish freshness or review coverage.]
- **Assessment:** [Reused / Created / Refreshed / Limited; applicability checks against the review snapshot, reason for this disposition, and material gaps or code/design conflicts]
- **Review-local draft:** [Link when generated, exact source baselines, canonical references, and semantic/structural validation results or limitations; omit when unnecessary]

[Link existing map, invariant, and scenario definitions. Preserve accepted intent
when implementation diverges; a draft alone does not establish review coverage.]

## Whole-change model and review plan

[Summarize intended before/after behavior, verified execution path, major dependencies,
and material uncertainties. Link the reused or prepared architecture context;
define a concise provisional model here when it resolves a small context gap, or
when a separate draft is unavailable or forbidden. Record status as an observed guarantee, requirement, assumption, or gap.
Include enforcement responsibility and evidence.]

| Unit / design definition link | Changed or uncovered behavior / entry points | Review-specific question / invariant link | Evidence / disposition | Reviewer / next action |
| --- | --- | --- | --- | --- |
| [Existing R1 or new unit; link definitions instead of copying them] | [Only material delta; paths/symbols needed for coverage] | [Question this review resolves] | [Precise independent check / result] | [Assigned reviewer if any; next step] |

## Behavioral investigations and depth

| Critical boundary / contract and actual paths | Primary batch / hypothesis / challenged assumption | Outcome and precise evidence | Challenge batch / reviewer / independence | Lead check / remaining obligation |
| --- | --- | --- | --- | --- |
| [B1; enforceable cross-component contract, including unchanged consumers] | [H1; failure hypothesis and fixture/ordering assumption to test] | [Supported / Refuted / Inconclusive; source trace or connected experiment and control] | [H2; fresh reviewer initially without prior findings, exposure/safety constraints; or separate lead pass and reason] | [Evidence meaning verified; unresolved work keeps depth partial] |

[Use bounded batches and behavioral-investigation-template.md or equivalent.
Link explicit file-to-symbol/scenario mappings; a broad assignment or passing
regressions alone does not resolve a boundary. Deep requires primary and challenge
for every critical boundary. Inspect this boundary list for omissions; no bug quota.]

## Validation environment and shared test plan

- **Setup owner / state:** [Lead or designated owner; ready / preparing / blocked; source review can continue]
- **Runtime and dependency provenance:** [Versions, manifest/lock baseline, installed dependency compatibility and smoke check]
- **Runtime alignment:** [Project requirement and reviewed config/CI/container source; chosen lane and exact executable/version probe before installation; package manager/hooks/checks use it; ready / limited / source-only with affected conclusions and reruns]
- **Registry and artifact resolution:** [Sanitized effective/expected registry and config source, exact locked artifact/version/integrity, compatible runtime/cache evidence; task-local routing changes if justified]
- **Isolation and preparation:** [Checkout/export/venv/container; compatible read-only reuse or attempted installation command/result; caches/build outputs; install-hook/test-service effects considered]
- **Setup limitations / recovery:** [Missing access/tooling, changed harness or other limits; one coordinated repair and affected reviewers]

| Setup attempt / time | Artifact / sanitized route / method | Result / saved evidence | Changed condition before retry / smoke check |
| --- | --- | --- | --- |
| [Attempt ID; observed interval or unknown] | [Exact artifact, locked integrity and provenance] | [Failure classification or success] | [Distinct evidence justifying another attempt; no identical retry loop] |

| Check / purpose | Category | Owner | Revision / environment / output | Status / result and what it establishes |
| --- | --- | --- | --- | --- |
| [Suite or bounded experiment] | [Regression / integration-contract / investigative reproduction] | [One primary owner] | [Exact revision, isolated setup, log/results path] | [Planned / running / passed / failed / blocked; for reproduction: defect reproduced / not reproduced / inconclusive] |

[Run a small setup check before parallel suites. Report environment failures to the
setup owner. Record repeated runs as replacements/rechecks, not additional coverage.]

## Review coordination

- **Lead / execution mode:** [Designated lead identity; requested and runtime-confirmed settings or not exposed; parent intake coordinator if applicable; selective delegation or sequential review and rationale]
- **Lead-owned work:** [Primary flow, consequential cross-unit scenarios, unassigned areas, coverage reconciliation, and verification/consolidation of findings]

Apply the installed shared model policy; this table records execution and does
not configure models. Reuse an existing execution record instead of duplicating
it. Separate requested settings from runtime evidence; preserve escalation and
fallback limitations. A documentation-author handoff never creates another lead.

| Role / task | Selection and concrete reason | Requested model / effort | Agent identity / execution evidence | Runtime-confirmed settings or not exposed | Result / handoff |
| --- | --- | --- | --- | --- | --- |
| [Lead, documentation or reviewer assignment] | [Reused / lead-direct / delegated; applicable context or unresolved question] | [Exact model and effort, or not requested] | [Identity and invocation/tool evidence] | [Confirmed evidence or not exposed] | [Artifact, escalation or limitation] |

<!-- Use the following reviewer-handoff table when delegating code review; omit
that table for a sequential review. Retain the execution record above in both
cases. The lead alone updates the canonical run.json. Reviewers write
distinct handoffs. -->

| Unit / reviewer | Assigned snapshot and scope | Handoff and actual scope / gaps | Lead verification and disposition |
| --- | --- | --- | --- |
| [R1 / reviewer identity] | [Exact revisions, question, dependencies, evidence destination] | [Handoff section/locator, paths/symbols/scenarios, proposed file dispositions, supported conclusions, candidates, categorized checks, remaining gaps] | [Evidence checked; findings accepted/deduplicated/rejected/unresolved; gaps completed/reassigned/open] |

[Commit one atomic checkpoint after each lead-verified handoff or bounded pass:
coverage, hypotheses and timing together. Record receipt ID/revision and reconcile
the narrative against canonical dispositions; never infer review from agent completion.]

## Timing, progress and interruptions

| Phase / owner | Start / end or current state | Last saved evidence / expected next checkpoint | Wait or failure / bounded observation / next action |
| --- | --- | --- | --- |
| [Context, setup, behavioral batch, challenge, integration or consolidation] | [Timezone-aware boundaries; observed / evidence-backed retrospective / unknown; logging time is separate] | [Artifact locator, observed progress and next check time] | [Known running / waiting / blocked / complete; preserve failed attempts and unfinished scope] |

- **End-to-end and lead timing:** [Coordinator intake and source, lead start/complete, delivery-ready, user-visible delivery if observed; total and lead interval separately, otherwise unknown/lower bound; manifest creation is not intake]
- **Phase overlap and delivery gap:** [Setup, investigation, consolidation and delivery preparation intervals; overlaps not additive; unexplained gaps unclassified; final response time unavailable until observed]
- **Truncated source / follow-up:** [Exact omitted regions and retrieval evidence; unresolved regions retain partial coverage]
- **Evidence-audit warnings:** [Repeated primary claims / legacy evidence; verified group mappings or unresolved gaps, not wording changes to silence warnings]
- **Interruption handling:** [Completed evidence preserved; permissible resumed work; no retries/rerouting of platform-blocked actions; unexecuted experiments remain unverified]

## Integration scenarios and evidence

| Scenario definition / units / invariants | Tested variant or delta | Expected outcome authority / changed expectation | Lead verification, evidence, and result | Status / remaining gap |
| --- | --- | --- | --- | --- |
| [S1 definition link; R1; I1] | [Exact variant checked; describe inputs/order only when absent or changed in the definition] | [Criteria snapshot link; any changed success/refusal expectation and responsible component] | [Connected admission → routing → execution trace/test; positive control; safety and functional outcome assessed separately] | [Unreviewed / Partial / Reviewed; ambiguous intent retained as requirements-dependent candidate] |

## Findings and unresolved questions

| Finding | Trigger, code path, and consequence | Introduced by this change? | Evidence and location | Disposition |
| --- | --- | --- | --- | --- |
| [F1; severity justified by impact] | [Reachable scenario and observable failure] | [Yes / Pre-existing / Unresolved] | [Revision, file/symbol/line, reproduction or code trace] | [Open / Fixed and reverified / Question; rationale] |

[Keep unverified suspicions and unavailable evidence identifiable as questions or
coverage gaps. The lead verifies and consolidates findings by root cause and impact;
agent agreement is not proof. A reviewed unit can still have an open finding.
Safe refusal alone cannot dismiss an admitted-but-failing supported workflow.]

## Revision updates and handoff

[On resumption, refresh accepted criteria and context even at unchanged Git revisions.
Retain prior/current criteria snapshots and distinguish proposals from authoritative
changes. For each meaningful source or criteria update, link the previous record,
record the delta, affected units and interactions, conclusions carried forward with evidence
and rationale, and checks rerun. Record the context reassessment and link a new draft
version if refreshed; preserve prior evidence and baselines. Reassess delegation,
record outstanding/stale assignments and handoff dispositions, and preserve
unresolved questions and next actions.]

## Validation results

- **Existing regressions:** [Distinct suites/tests and failures, skips or deselections; supporting artifacts]
- **Integration / contract checks:** [Local services, fork or external scope; exact baseline and limits]
- **Investigative reproductions:** [Finding ID, hypothesis/assertion, observed defect reproduced / not reproduced / inconclusive, positive control when useful; a passing bug assertion is evidence of a defect]
- **Harness / environment differences:** [Changes, mocks, initial environment failures, final rerun evidence, remaining limits]

[Keep categories distinct. Do not aggregate defect reproductions into a green-test
headline or claim that all tests passed when setup failed or tests were not run.]

## Verdict and coverage limits

[State the exact reviewed snapshot and scope, verified findings, checked
interactions, categorized validation results and limits, exclusions or remaining
gaps, and whether code/integration review is complete or partial. Separately state
requirements verification, including any unread/unavailable linked ticket or document. Distinguish no findings from a complete
review, and review completion from merge/deployment status.]

- **File/integration accounting:** [Complete / partial, helper result and semantic evidence check]
- **Investigation depth:** [standard / deep; complete / partial; boundary hypotheses/challenges and lead integration verified; unresolved material questions prevent comprehensive completion]
- **Execution-policy conformance:** [Supported invocation/configuration or specific limitation, separately from substantive completeness; no inferred backend confirmation]
- **Run check and provenance:** [Structural run-helper result, actual configuration evidence, version/timing limits; helper success cannot prove reasoning quality or omitted-boundary coverage]
- **Record consistency / fallback:** [Canonical coverage and narrative reconciled; structural validation passed / failed / unavailable, separate from review completeness; same-schema manual limitations, preserved evidence and no invented helper success]
- **Durable delivery:** [Report/archive path; integrity and portable evidence-reference check; original record hashes, preserved probes and selected outputs; excluded caches/dependencies, source checkout requirements and any archive failure]

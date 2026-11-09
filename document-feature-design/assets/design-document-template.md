---
document_feature_design:
  schema_version: 1
  role: primary
  source_inventory: "#source-inventory"
  review_map: "#review-map-and-suggested-order"
  critical_invariants: "#critical-invariants"
  integration_scenarios: "#integration-scenarios"
---

<!--
Adapt to the repository and decision size; retain both reading layers, even if
brief. Remove instructions, placeholders, and immaterial sections. Keep the
canonical decision in the primary document if technical detail moves to a
companion. Update the discovery pointers to the actual sections; omit pointers
for immaterial omitted content. Validate the completed document, not this
unfinished template.

Keep model routing and author/lead execution evidence in the local validation
record (assets/design-validation-template.md in the installed skill), or in the
existing PR review record. Apply the shared references/model-policy.md there;
do not add model settings to discovery metadata or architectural decisions.
-->

# [Feature name]: [decision summary]

| Field | Value |
| --- | --- |
| Decision status | [Draft / Proposed / Accepted / Rejected / Superseded] |
| Implementation status | [Not started / Partial / Complete / Unknown] |
| Deployment status | [Not applicable / Not deployed / Partial / Deployed / Unknown] |
| Decision date | [YYYY-MM-DD or Unknown] |
| Last verified | [ISO date, time, and timezone] |
| Owners | [Decision and document owners, or Unknown] |
| Source roots | [Repository identities or supplied proposal identifiers] |
| Source baseline | [Exact snapshot identifiers, or a link to the source inventory below] |
| Supersedes / superseded by | [Decision links, or None] |

## Part I — Feature and decision overview

### Problem and intended outcome

[Explain the problem from first principles, why it matters, desired outcomes, and non-goals. State the decision requested from reviewers or the decision already made. Include prior behavior only where it explains the problem.]

### Design and primary workflow

[Explain the mental model, essential terminology, main components, ownership boundaries, and a representative end-to-end flow. Use a diagram if helpful. Distinguish proposed from implemented behavior.]

### Why this approach

[Summarize the dominant decision criteria, selected approach, important tradeoffs, risks, and adoption implications. Link to the canonical decision record below rather than repeating its rationale.]

## Part II — Architectural reference

### Architectural decisions

<!-- Keep new decision records canonical here for a single document. Summarize
and link existing authoritative ADRs instead of duplicating their records.
If splitting, retain the decision record or authoritative ADR link in the primary
and move supporting technical detail to the companion. Repeat for distinct decisions. -->

#### [Decision name]

- **Status and decision evidence:** [Decision status and source establishing it; identify proposals and inferred rationale explicitly]
- **Context and criteria:** [Constraint or tension, dominant decision criteria, and their relative importance]
- **Decision:** [Chosen approach and its scope]
- **Rationale and alternatives:** [Compare credible alternatives against the criteria, including the existing approach when relevant; distinguish recorded rationale from present analysis]
- **Consequences:** [Benefits, costs, risks, constraints, and follow-on obligations]
- **Reversibility and revisit conditions:** [What changing course entails, assumptions the choice depends on, and concrete triggers for reconsideration; label proposed thresholds]

### Sources and evidence status

#### Source inventory

| Source ID and identity | Exact baseline and snapshot kind | Relevant evidence / what it establishes | Verified at |
| --- | --- | --- | --- |
| [Repository or proposal identity] | [Exact revision; for working-tree content also retained patch/snapshot path, digest, and affected paths; for a proposal, version or identifiable dated/content snapshot] | [Repository-qualified paths and symbols, or specification sections] | [ISO date, time, and timezone] |

<!-- Include identifiable versions or retained snapshots for material accepted
criteria, with authority/status. Link them from decisions, invariants and scenarios;
keep review-specific evidence and status outside this document.
Use one entry per repository/source snapshot. Record relevant untracked
files in retained snapshots. A branch, PR number, or mutable URL alone is not
a baseline. Link claims and decisions to this inventory without repeating it. -->

#### Evidence status, assumptions, and conflicts

[Record material assumptions, inferences, conflicts, unverified claims, and unresolved gaps with sources and resolution or owner when known. State explicitly if none were identified. Keep fully supported claims beside their evidence in the narrative instead of duplicating them here. For proposals, bound any implementation search to the inspected sources.]

### Components, contracts, and state

| Component or contract | Current / planned status | Responsibility and owned state | Dependencies and guarantees | Source reference |
| --- | --- | --- | --- | --- |
| [Component or interface] | [Current / Planned / Partial / Unknown] | [Ownership and responsibility] | [Boundary and relevant contract] | [Repository-qualified path and symbol, or established planned location] |

[Explain material schemas, configuration, persistence, lifecycle transitions, and compatibility constraints. Add a state diagram or transition table where useful.]

### Review map and suggested order

<!-- Useful for substantial or cross-component changes; condense or omit for a
small ADR. Group by behavior, not arbitrary file counts. Link definitions below
or existing authoritative sections. Keep live PR coverage in a review record. -->

| Unit and purpose | Read first: paths / symbols or planned components | Dependencies and review order | Critical invariants / integration scenarios | Verification entry points |
| --- | --- | --- | --- | --- |
| [R1: behavior and reason it changes] | [Source-qualified entry points; label planned locations] | [Prerequisites; independent or joint review] | [Links to I1 / S1 or existing definitions] | [Tests, traces, or planned validation] |

### Detailed flows and correctness

[Trace the main path and material alternate paths. Explain ordering, concurrency, and idempotency where relevant; link critical invariants instead of repeating them.]

#### Critical invariants

| Invariant and scope | Status and responsible component | Enforcement evidence or gap | Observable violation and validation |
| --- | --- | --- | --- |
| [I1: condition that must hold, including the relevant lifecycle boundary] | [Implemented / Required / Assumed / Unresolved; enforcing component] | [Source-qualified symbol, contract, or missing enforcement] | [What failure looks like; test evidence or planned check] |

### Failure and recovery behavior

| Failure or invariant violation | Detection | Automatic behavior | Recovery / rollback and owner | Evidence or gap |
| --- | --- | --- | --- | --- |
| [Material failure] | [Signal] | [Retry, fallback, or stop] | [Durable recovery responsibility and operator action if needed] | [Supporting source or unresolved validation] |

### Integration scenarios

<!-- Select representative cross-unit paths and consequential failure/recovery
cases from this design. Reuse scenario definitions if they already exist. -->

| Scenario and linked units / invariants | Starting state, trigger, and ordering | Expected observable outcome and responsible components | Evidence or planned validation / gap |
| --- | --- | --- | --- |
| [S1: scenario; links to R1 / I1] | [Initial state and events, including a failure boundary when material] | [Durable state, external effect, and recovery responsibility where relevant] | [Existing test/trace and result, or proposed check and unresolved evidence] |

### Operations, rollout, and validation

[Cover only material security/privacy, performance/capacity, observability, compatibility, migration, rollout gates, success criteria, and rollback constraints. Separate observed results from proposed targets.]

| Behavior or risk | Current evidence or planned validation | Verification entry point | Known gap / owner |
| --- | --- | --- | --- |
| [Behavior or risk] | [Observed evidence or planned check] | [Test, command, fixture, or source] | [Gap or None] |

[Link the review map and scenarios to relevant checks without duplicating them. Record open questions and future work with an owner or decision point when known.]

### Document maintenance

[Identify which material is the historical decision record and which architecture is current only at the stated baseline. Name the update owner or unresolved ownership, refresh triggers, and supersession policy. Preserve accepted rationale when implementation facts change; link any superseding decision and companion in both directions.]

# Authoring and validation guide

## Resolve scope and destination

Infer the feature, sources, source roots, destination, and delivery endpoint from the request and context. Ask only when a missing choice materially changes scope, accuracy, or destination; otherwise state the assumption. Inspect applicable guidance and existing documents for naming, metadata, links, diagrams, and ADR mutation conventions.

Resolve a relative destination against the documented project root: prefer the user's explicit root, then the repository containing the supplied sources. With multiple repositories, identify each source root and choose one destination root; ask if the destination remains ambiguous. Prefer the established documentation location, otherwise `<project-root>/docs/design/<feature-slug>.md`.

For a proposal without a repository, use the supplied specification or conversation as the source. Record its identifier, version or dated snapshot and verification time. Use an explicit destination, otherwise the workspace's deliverable location; do not invent a repository or require code discovery. The destination root for validation is the folder containing the deliverable, not an implied source repository.

Inspect the destination before writing. Update an existing document only when the request or project context identifies it as the target; preserve unrelated changes. Default to a local draft. A requested commit, push, or PR authorizes its necessary Git prerequisites only for the intended documentation changes; a lower endpoint does not authorize a later one. Stop if a prerequisite conflicts with explicit instructions or cannot be isolated. External publication does not authorize Git history.

## Establish evidence and its limits

- Separate decision, implementation, and deployment status. Branch code establishes behavior at that snapshot; it does not establish acceptance or deployment.
- Refresh mutable sources when current state matters. For **each repository**, record its identity, exact revision, snapshot kind, relevant source paths, and verification time. Read the recorded revision, checking that the inspected files match it. When intentionally including uncommitted changes, identify the base revision and retain a scoped patch or source snapshot with a content digest and affected paths, including relevant untracked files. Never attribute dirty working-tree content solely to `HEAD` or silently clean the user's checkout. Preserve sensitive evidence in an appropriately restricted location.
- For material accepted requirements and decisions, preserve an identifiable criteria version or retained content snapshot, authority/status and verification time. On resumption, reassess these and relevant architectural context even if code revisions are unchanged; distinguish accepted changes from proposals and preserve historical decisions. Follow the shared [handoff and freshness contract](review-handoff.md).
- For non-repository sources, record a version or identifiable dated/content snapshot. Label inaccessible or stale evidence as unverified. A PR number, branch name, or mutable URL alone is not a reproducible baseline.
- Classify material claims as confirmed behavior at the baseline, approved decision, proposal, inference, or unresolved. Cite authoritative sources beside current-behavior and approved-decision claims. Use code, tests, configuration, schemas, and runtime evidence for behavior; specifications and recorded decisions for intent and rationale. Do not invent approval, owners, or historical rationale.
- Keep one source inventory. Use a separate evidence-status section for material assumptions, inferences, conflicts, and gaps, with resolution or owner when known; state explicitly if none were identified. Do not repeat every supported claim in that section.

For a code-backed feature, trace a primary path and material failure or recovery paths end to end. Investigate boundaries, state ownership, contracts, invariants, concurrency, and operational consequences only as they affect the design. Stop when the relevant paths, status claims, and decisions have evidence or a clearly bounded gap. Inspect adjacent systems only if their behavior could change a decision or material consequence.

For a proposal, search supplied code roots only when available and relevant. Report “not found in the inspected sources,” “sources unavailable,” or “not investigated” as appropriate; a bounded search cannot prove that implementation does not exist elsewhere. Continue from sufficient proposal evidence.

After this bounded context assessment, the lead selects the authoring path using the shared policy. Pass exact sources, decisions, gaps, destination and validation expectations to an assigned author. The author returns the artifact and evidence; the lead verifies the material claims and requested delivery. Do not repeat the full investigation merely to use a second model.

Use repository-relative paths and symbols, qualified as `<repo>:<path>#<symbol>` across repositories. Use immutable source links when useful; avoid machine-local paths in the delivered document.

## Build the two reading layers

Follow the repository's presentation conventions. Use [assets/design-document-template.md](../assets/design-document-template.md) when there is no suitable existing structure. Remove instructional comments, placeholders, and irrelevant sections. Sections and tables are aids, not a coverage quota.

For each primary Markdown design created or updated, add the versioned `document_feature_design` frontmatter namespace defined in [references/discovery-metadata.md](discovery-metadata.md). Merge existing metadata and point to the actual source inventory and applicable review sections, including companion sections when needed. This lets a reviewer discover and reuse the document without repeating context preparation. Keep one source inventory; the marker is navigation metadata, not a claim of freshness or approval. Supporting companions do not duplicate the marker. If destination conventions prohibit frontmatter, preserve them and disclose that automatic marker discovery is unavailable.

Keep the overview and **decision record in the primary document**. For a new decision, the primary document owns the canonical record; when an authoritative ADR already exists, summarize and link to it instead of creating a competing record. In a single document, detailed new decisions normally live in Part II, with summaries and links from Part I. If a repository ADR format or a distinct audience warrants a companion reference, retain the decision record or authoritative ADR link in the primary document and link both ways; the companion owns supporting technical detail. Do not duplicate canonical rationale.

**Overview:** Give a new engineer enough context to understand the problem, goals and non-goals, terminology, design, main components and workflow, benefits, important costs, risks, and adoption implications. State what reviewers are being asked to decide for a proposal, or what was decided for an accepted record. Summarize the decisive constraints and tradeoffs, linking to their full treatment. A substantial feature may need a 10–20 minute reading path; a small ADR can use a few paragraphs. Preserve both conceptual layers without padding or forcing literal “Part I” and “Part II” headings.

**Architectural reference:** Include the detail needed to trace the design into components, contracts, state transitions, invariants, failure/recovery behavior, and source evidence. Cover security, performance, observability, compatibility, migration, rollout, rollback, and validation where material. Distinguish implemented guarantees from planned contracts and validation. Prefer an explicit gap over speculative detail. Orient reviewers to critical paths, sensitive assumptions, and verification entry points. There is no read-time target for this layer.

## Support implementation review

For substantial or cross-component designs, include a review map in the architectural reference. Group by behavior or contract, with a suggested reading order, purpose, entry files and symbols, dependencies, and verification entry points. Identify which units can be examined separately and which require a joint review. Use stable identifiers or links to connect units, invariants, and integration scenarios without repeating their descriptions. Keep this proportional: a small ADR can express the same information in a few sentences or omit an immaterial map.

- **Critical invariants:** state the condition that must hold, its scope and relevant lifecycle boundary, the component responsible for enforcing it, and the enforcement and validation evidence. Distinguish an implemented guarantee from a design requirement, assumption, or unresolved gap. Describe the observable consequence if it fails. Link existing invariant definitions instead of creating a competing list.
- **Integration scenarios:** trace representative behavior across units, including material failure or recovery boundaries. Record the starting state, trigger and ordering, expected observable outcome, responsible components, linked invariants, and existing evidence or planned validation. Choose scenarios from the actual design risks, such as a crash after an external success but before durable recording, competing owners, compatibility during rollout, or rollback after a schema change; do not add this entire catalog indiscriminately.

Use the shared [review handoff](review-handoff.md) to keep definitions reusable by reference. Review-specific questions, evidence, dispositions and scenario deltas belong in the review record; a small descriptive gap can use a concise provisional model there without a new design. A sufficient existing design needs no rewrite unless an edit was requested.

The map guides investigation; it is not proof of implementation correctness or complete PR coverage. For proposals, identify planned components and validation without inventing paths or test results. Keep live reviewer assignments, reviewed-file status, PR base/head revisions, findings, and rerun history in a PR-specific review record. For an actual large-PR review, the companion [review-large-pr skill](../../review-large-pr/SKILL.md) provides that workflow; writing a design alone does not require executing it.

## Make decisions assessable and maintainable

Preserve ADR essentials: status, context, decision, rationale, alternatives, and consequences. Strengthen consequential decisions with:

- **Decision criteria:** identify the constraints that dominate the choice and compare credible alternatives against them, including retaining the existing approach when relevant. Explain priorities and tradeoffs; avoid invented scores or claiming alternatives were historically considered without evidence.
- **Revisit conditions:** state the assumptions the choice depends on, how reversible it is, and concrete changes that warrant reconsideration. Use supported thresholds when available; label proposed thresholds and unknowns. Apply this to consequential decisions, not every implementation detail.
- **Document lifecycle:** distinguish the historical decision record from the architecture described at the current baseline. Identify the update owner or unresolved ownership and relevant refresh triggers. Update implementation facts and source baselines without rewriting the rationale for an accepted decision. Use a superseding decision for a changed choice unless repository policy or the user requires another treatment. Preserve dates and links so outdated descriptions and superseded decisions remain distinguishable.

These refinements can be concise prose within the existing decision record; they do not require three extra sections.

## Validate and deliver

Review meaning before relying on automation: the primary overview must stand alone; the decision must follow from its criteria and evidence; the two layers must complement each other; historical decisions, observed behavior, proposals, and gaps must remain distinct. Check diagrams and references against the actual source snapshots and review the final diff.

When a review map is included, trace its entry points to the stated sources, check invariant/scenario links, and verify that the scenarios cover the consequential interactions between units. Confirm enforcement and test claims directly; mark proposed or missing evidence explicitly. These are semantic checks, not requirements for literal headings or a fixed number of rows.

For Markdown, run the bundled structural validator in a Python environment with dependencies from [scripts/requirements.txt](../scripts/requirements.txt). If needed, create a temporary virtual environment and install with `python -m pip install -r <skill-dir>/scripts/requirements.txt`; do not change the system Python environment.

```bash
python <skill-dir>/scripts/validate_design_document.py <document> --project-root <destination-root> --require-discovery-metadata [--companion <path>]
```

It checks document containment, titles, primary metadata and overview placement, discovery metadata and its navigation targets, reference/evidence sections, template leftovers, and local Markdown links. Omit `--require-discovery-metadata` only for legacy documents or destinations that prohibit frontmatter; present markers are still checked. It accepts table, list, or YAML metadata and common heading names. For different repository names, map roles explicitly, for example `--section 'overview=Context' --section 'reference=Technical design' --section 'evidence=Evidence and caveats'`. Use `--help` for metadata aliases and anchor options. Unsupported formats require the repository or destination's own checks; a skip is not successful validation.

Fix errors and review warnings; `--strict` makes warnings fail. Run applicable repository documentation, link, and rendering checks. Structural success does **not** establish factual correctness, approval, deployment, source-to-claim coverage, snapshot identity, or sound rationale. Check those directly. Renderer-specific anchors can be delegated with `--anchors skip` only when separately checked with the destination renderer; report that limitation.

When maintaining this skill's validator or template, run `python <skill-dir>/scripts/test_validate_design_document.py` for the document regression suite.

Verify the artifact at its requested destination. Report its path, source roots and exact baselines, verification time, checks, material gaps, and requested delivery actions completed. Include only intended changes in Git delivery.

Record the lead and any delegated handoffs. Detailed model/effort telemetry is optional; supplied observations must distinguish requested settings from runtime confirmation. Missing metadata does not block a source-grounded document. Model preference cannot replace semantic or structural validation.

Before external publication, determine the audience and visibility and remove secrets, personal/customer data, sensitive evidence, and internal-only detail the destination should not expose. Request confirmation if visibility or sensitivity remains materially uncertain. Follow destination conventions and verify the published result.

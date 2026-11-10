---
name: document-feature-design
description: Create or update source-grounded feature designs, RFCs, and ADRs with an accessible overview and traceable architectural detail. Use for architecture and decision documentation, not routine PR summaries, release notes, runbooks, or API references.
---

# Document Feature Design

Explain the problem, decision, constraints, alternatives and consequences. Connect
claims to evidence and state when the decision should be revisited. Scale the
document to the decision: a short ADR can provide both an accessible explanation
and enough technical detail in a few paragraphs.

## Establish scope and evidence

Reuse the current or designated lead under the [shared model policy](references/model-policy.md).
Read project preferences once; do not spawn another lead to match a model name.
Delegate substantial bounded authoring when useful and permitted; this skill requests
that selective delegation. Assigned authors do not start another lead or delegate again.
Keep the [complete sibling installation](references/paired-installation.md).

Infer the feature, supplied sources, destination and requested delivery endpoint.
Follow repository conventions and preserve unrelated edits. Default to a local
draft in the established documentation location, otherwise `docs/design/` under
the source repository. A repository-free proposal uses its supplied specification
and the workspace's deliverable location; do not invent a repository.

Read the [authoring guide](references/authoring-guide.md) for scope, source inspection
and validation. Record exact source baselines and identifiable criteria snapshots;
preserve a scoped snapshot for relevant uncommitted changes. Trace the material
source paths, contracts and failure/recovery behavior. Mark missing evidence explicitly.
Separate accepted decisions, observed implementation, deployment evidence and inference.

## Write the smallest complete document

Use an existing repository format, the [feature template](assets/design-document-template.md),
or the [filled concise ADR](examples/concise-adr.md). Remove unused sections and
placeholders. Preserve status, context, decision, rationale, credible alternatives,
consequences and material revisit conditions. Never invent approval or historical rationale.

Keep the primary overview understandable on its own and the canonical decision or
authoritative ADR link in the primary document. Put supporting technical detail in
the same document or a linked companion. Avoid repeating definitions and rationale.
For substantial designs, provide the review map, critical invariants and integration
scenarios needed to inspect consequential behavior; a small ADR can express these in prose.

Add [discovery metadata](references/discovery-metadata.md) to primary Markdown
documents unless destination conventions prohibit frontmatter. Link the actual
source inventory and applicable sections. Metadata provides navigation, not approval.
Use the [handoff contract](references/review-handoff.md) when a review reuses the design.
Refresh implementation descriptions without silently rewriting accepted decisions.

## Validate meaning, then structure

Check claims, status, decision criteria, alternatives, diagrams and source links
against the recorded evidence. Distinguish planned validation from executed checks.
Follow the authoring guide for isolated validator dependencies and repository checks:

```bash
python <skill-dir>/scripts/validate_design_document.py <document> --project-root <destination-root> --require-discovery-metadata
```

Fix errors and assess warnings. Structural success cannot establish factual accuracy,
approval, deployment or sound rationale. Keep actual validation evidence in an existing
report or the [validation record](assets/design-validation-template.md); detailed model
and timing diagnostics are optional. Requested settings are not runtime confirmation.

Verify the artifact at the requested destination and complete the authorized delivery.
Report its location, source baselines, meaningful checks and material gaps. Publication
requires authority from the request and appropriate destination visibility; local
authoring alone does not authorize posting, merging or deployment.

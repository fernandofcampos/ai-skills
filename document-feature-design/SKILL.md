---
name: document-feature-design
description: Write or maintain a source-grounded feature design, RFC, or architecture decision record (ADR). Use for a proposed decision, an implemented feature's architecture, or a material architecture gap discovered in review.
---

# Document a feature design

Deliver a document a new engineer can use to understand the decision and a maintainer can trace to its sources. Default to a local draft in the requested or established documentation location, falling back to `docs/design/`. A proposal without a repository uses the supplied specification and the workspace's deliverable location.

## Establish what the sources support

- **Proposal.** Identify the dated or versioned brief and the decision still open. Label planned behavior and validation. Name an owner or approver only when a source assigns that authority. Leave it unknown when the brief identifies only the audience.
- **Code-backed design.** Pin each source revision and trace a representative path plus material failure or recovery behavior. Retain a scoped patch or content snapshot for relevant uncommitted work. Distinguish what the code implements, what was accepted, and what is deployed.
- **Update or review handoff.** Preserve accepted rationale, refresh facts and criteria at the new baseline, and link the authoritative decision. In a PR review, return a review-local draft to the existing lead unless tracked documentation changes were requested. [Handoff and freshness](references/review-handoff.md)

Keep the current lead. An assigned author returns the artifact, source identities and validation results to that lead. For standalone project work, read `.ai-skills.json` once if present. Apply role preferences and direct user overrides when choosing a worker. [Model preferences](references/model-policy.md)

## Write and verify the decision

Keep the overview and canonical decision or ADR link in the primary document. Explain the deciding constraint, credible alternatives, consequences and a concrete reason to revisit. A short decision can fit in a few paragraphs. A substantial design also needs entry points, critical invariants and cross-component scenarios. Use the repository's format or adapt the [feature template](assets/design-document-template.md). A [concise ADR](examples/concise-adr.md) illustrates the smaller form.

Keep one source inventory with baselines and verification time. Add the discovery marker to primary Markdown documents where the destination permits frontmatter. Check material claims and links against the sources, then run the validator with its declared dependencies. [Discovery metadata](references/discovery-metadata.md)

```bash
python <skill-dir>/scripts/validate_design_document.py <document> --project-root <destination-root> --require-discovery-metadata
```

If the destination prohibits frontmatter, omit the marker and its flag. Use section aliases for repository headings and destination-native checks for other formats. [Authoring and validation guide](references/authoring-guide.md#validate-and-deliver)

Fix validation errors, assess warnings and verify the artifact at the authorized endpoint. Report its location, supporting sources, executed checks and remaining gaps.

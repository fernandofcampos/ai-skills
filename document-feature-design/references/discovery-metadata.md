# Design discovery metadata, version 1

Put this namespace in the YAML frontmatter of each primary Markdown design created
or updated with document-feature-design. Merge it with existing frontmatter; keep
repository metadata and the canonical source inventory. Supporting companions link
back to the primary and do not repeat this marker.

```yaml
---
document_feature_design:
  schema_version: 1
  role: primary
  source_inventory: "#source-inventory"
  review_map: "#review-map-and-suggested-order"
  critical_invariants: "#critical-invariants"
  integration_scenarios: "#integration-scenarios"
---
```

`document_feature_design` is a literal top-level key, not a code example or nested
field. Do not repeat keys or use YAML merges in this namespace. `schema_version`
must be the integer `1`; `role` must be `primary`.
`source_inventory` is required and points to the existing inventory identifying
source scope, exact snapshots, and verification time. The three review pointers
are optional for designs where that material is immaterial; omit absent fields
instead of using null, placeholders, or invented content. Substantial designs
normally provide all three. Several pointers may identify one concise section.
No other fields are defined in version 1.

Pointers are quoted local Markdown links with a nonempty fragment, relative to the
primary document (for example `details.md#critical-invariants`), or root-relative
to the documented destination root. They must resolve to real sections within that
root. Adjust them to repository headings and companion placement; do not rename
sections just to match this example. Do not duplicate source revisions, decision
status, or verification dates in the marker. A document committed alongside code
may cite the earlier inspected commit or retained working-tree snapshot; it need
not predict the commit that will contain itself.

This is a discovery and navigation contract, not proof of authorship, approval,
freshness, validation, correctness, or complete review coverage. Do not add a
`review_ready` flag or treat the marker as an instruction to skip code review.
A reviewer compares the identified scope and source evidence with the actual PR
snapshot before reusing the context. Old source revisions are assessed for
material differences rather than rejected solely for not matching the PR head.

On reuse, navigate directly to the identified overview, inventory, map, invariants,
and scenarios. When these are sufficient and applicable, skip broader context
discovery, design generation, and a repeated full design-validator run. Record the
document path/blob or revision and the applicability evidence in the review record.
Broken links, unsupported versions, missing relevant context, or material drift
fall back to normal context assessment; an unmarked document may still suffice.
For several marked designs, select or combine relevant scopes and resolve conflicts
rather than trusting the first match.

Keep definitions and their identifiers here; reviewers add questions, evidence and dispositions by reference under the [handoff contract](review-handoff.md). Refresh material criteria and context even when the code and marker are unchanged.

The structural validator checks this namespace and its pointers when present.
Use `--require-discovery-metadata` for a newly generated or updated primary;
legacy unmarked documents remain valid without that flag. Pointer validity does
not establish that the destination contains adequate or current evidence.

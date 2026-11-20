---
name: review-large-pr
description: Review a complex or cross-component pull request, perform an explicitly requested deep review, or resume either at a new revision. Use when findings need whole-change reasoning and traceable coverage. Routine small PRs can use ordinary review.
---

# Review a large PR

Deliver impact-ranked findings, a verdict scoped to the inspected revisions, and a portable evidence record. Review the submitted change as one unit. Keep source edits and publication within the user's authorization.

## Choose the starting point

- **Assigned reviewer.** Investigate the assigned contract at the supplied revisions. Return paths, evidence, conclusions and gaps to the lead. The lead owns the canonical run and integration verdict.
- **Follow-up.** Open the prior record first. Refresh the code comparison and accepted criteria, even at an unchanged head. Preserve the prior verdict, reopen affected paths and consumers, and explain why each retained conclusion still applies. Use a new inventory for changed revisions. [Resuming a review](references/review-completion.md)
- **New review.** Resolve the actual target base and head, inspect repository guidance, and start a record outside the checkout. Use Git objects or an isolated checkout to preserve dirty work. For multiple repositories or unsupported comparisons, record each baseline and the integration boundary. [Review commands](references/quickstart.md) · [Multi-repository checkpoints](references/checkpoint-records.md)

```bash
python3 <skill-dir>/scripts/review_run.py start --repo <checkout> --base <target-base> --head <head> --output <new-review-folder>
```

Keep the current or designated lead. Start captures project model preferences. Consult the shared policy for overrides or bounded delegation, and the run record for optional diagnostics. [Model preferences](../document-feature-design/references/model-policy.md) · [Diagnostics](references/run-record.md)

## Investigate and record

Read linked requirements and material PR discussions. Retain the criteria, authority and revision or content snapshot. Trace before/after behavior through changed paths and relevant unchanged consumers. Reuse an applicable design by reference. Record a small context gap in the review, or use the companion skill for a material architecture gap. [Source and validation rules](references/review-foundations.md) · [Architecture discovery and integration](references/full-review-workflow.md)

Use `assess` to record the depth and validation choice. Mechanical volume alone can receive a standard review. Substantial interactions, consequential uncertainty or an explicit deep request require a primary investigation and a separate challenge for each critical boundary. Verify challenges against source and disclose independence limits. [Deep investigation](references/behavioral-depth.md)

Save evidence after each verified pass. Use `record` for individual paths or integration, and `checkpoint` for batches. Give each reviewed path a locator and conclusion. Preserve unread regions and unresolved questions as gaps.

## Deliver

Verify each finding's trigger, reachable consequence and location. Reconcile the full inventory and integration coverage, refresh material criteria and remote PR revisions where available, and distinguish existing tests from independent checks. Fill the report before packaging it.

```bash
python3 <skill-dir>/scripts/review_run.py finish <review-folder>/run.json
```

Link the verified report. If evidence is missing, deliver the supported findings with the exact coverage limit. The archive check verifies record structure and evidence links. The lead owns the verdict. [Partial reviews and delivery](references/durable-delivery.md)

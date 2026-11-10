---
name: review-large-pr
description: Review large or complex pull requests with whole-change reasoning, integration checks, revision-specific coverage, and durable evidence. Use for substantial interacting changes, explicit deep reviews, and resumed reviews that need traceable coverage; not routine small-PR review, standalone design authoring, or implementation.
---

# Review Large PR

Review the cohesive change as one delivery unit. Keep the work bounded and resumable,
and ground findings in reachable behavior at exact source revisions. Do not require
a stack of smaller PRs or rewritten commits. Complexity comes from interactions and
uncertainty; an explicit deep review can concern a compact consequential change.

## Start with one lead and one record

Reuse the current or already designated lead. Read the [shared model policy](../document-feature-design/references/model-policy.md)
once: project preferences and explicit user choices override defaults. Missing model
metadata does not require a new lead or prevent a complete review. Assigned workers
retain their role and never start another lead.

Infer the repository, PR, requested scope and report destination. Read applicable
repository guidance and the [source and validation rules](references/review-foundations.md).
Review is read-only unless the user also authorizes fixes or publication; scratch
evidence is allowed. Preserve dirty source and read the recorded revisions.

Use the [quickstart](references/quickstart.md) to create a task-owned evidence folder
outside the checkout with one command:

```bash
python <skill-dir>/scripts/review_run.py start --repo <checkout> --base <target-base> --head <head> --output <review-folder>
```

This pins the comparison, creates an unreviewed inventory, captures project model
preferences and writes a report template. It does not fetch PR metadata, assess
depth or claim coverage. Refresh actual remote revisions separately when available.
For multiple repositories or unsupported comparisons, use the
[checkpoint workflow](references/checkpoint-records.md) or equivalent explicit records
with the limitation stated. Keep the complete [sibling installation](../document-feature-design/references/paired-installation.md).

## Investigate the whole change

Follow the [complete workflow](references/full-review-workflow.md): assess existing
architectural context, build the whole-change model, investigate behavioral units
and directly check their interactions. Reuse designs by reference. Use the companion
documentation skill only for material context gaps or requested authoring.

Read linked requirements and relevant PR discussions; retain source/criteria snapshots,
authority and access limits. Separate accepted intent, descriptions, proposals and
inference. A URL or PR paraphrase is not evidence of reading a ticket.

Assess `standard` or `deep` from actual behavior. Substantial interacting changes,
consequential uncertainty and explicit deep requests require the
[deep investigation and challenge gate](references/behavioral-depth.md). Mechanical
volume alone does not. Select tests and source traces that resolve actual risks;
prepare isolated compatible environments when execution is needed.

Delegate bounded independent investigations when useful and permitted by the user
and runtime. This skill requests that selective delegation; it does not require a
team for every change. Keep one lead accountable for integration, verification and
the final verdict. Record exact worker scope and evidence; agreement is not proof.

## Save verified work and resume precisely

Use `assess` and `record` from the quickstart for routine updates. Use `checkpoint`
for batch evidence, critical boundaries and challenge results. Save after each
verified pass; only the lead updates the canonical run. Every reviewed path needs
a precise evidence locator and conclusion. Retain unread source and unresolved
hypotheses as gaps, including when a tool truncates output.

Follow [coverage and resumption rules](references/review-completion.md) before
continuing earlier work. Refresh material criteria even at an unchanged head.
Preserve prior snapshots and verdicts; reopen affected claims and justify evidence
carry-forward. A focused follow-up stays in this workflow and does not require a
new team, design document or whole-PR rerun.

## Complete and deliver

Reconcile the full inventory and integration coverage, verify findings, refresh
criteria and actual PR revisions, and disclose limits. A reviewed file may contain
a defect; unresolved required investigation prevents a comprehensive verdict.
Separate existing regression results, integration checks and investigative probes.
Rank actionable findings by impact with trigger, consequence and source evidence.

Fill the report and run:

```bash
python <skill-dir>/scripts/review_run.py finish <review-folder>/run.json
```

This checks required review records, follows referenced evidence and verifies a
portable archive. Report structural validation separately from semantic completeness.
For partial reviews or special packaging, use [durable delivery](references/durable-delivery.md);
deliver useful findings with explicit gaps rather than manufacturing completion.

Detailed phase timing, liveness and model telemetry are optional. See
[run diagnostics](references/run-record.md) only when requested or useful. Use
`check --require-diagnostics` to audit those observations separately. Missing telemetry
cannot waive missing review evidence, and preferred model settings cannot establish quality.

Use the [filled review](examples/large-pr-review.md) and [follow-up](examples/follow-up.md)
for output guidance. When changing helpers, run their `test_*.py` suite and the paired
installation check; use the repository evaluation workflow to assess actual agent outcomes.

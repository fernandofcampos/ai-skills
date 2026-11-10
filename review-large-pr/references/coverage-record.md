# Coverage record and helper

For new reviews, use this helper to create a seed inventory, then import it into
schema-2 `run.json` via the [canonical checkpoint workflow](checkpoint-records.md).
The embedded inventory becomes authoritative; do not keep updating the seed.
The standalone update/check commands below remain supported for legacy records.


Use this reference when initializing, checkpointing or checking a local Git review. The helper uses only Python's standard library and Git. It never fetches refs, reads tickets, installs dependencies or edits source. Keep one record per repository/comparison; the lead alone writes it.

Coverage and investigation depth are separate. Record depth and its behavioral
rationale in the narrative and canonical run; this helper accounts for paths and
evidence without judging whether the investigation is sufficient. Group related
paths into meaningful units with precise citations; every changed path and
relevant interaction still needs its own disposition.

When new risks emerge at the same snapshot, retain the current inventory and valid
checkpoints, preserve the previous narrative, and reopen evidence affected by the
new risk or dependency. If revisions changed, create a fresh inventory and retain
the old record; reassess carried-forward claims rather than editing snapshot
metadata. A depth assessment alone neither clears nor certifies existing coverage.

## Initialize and check

Create a task-owned scratch directory before initializing records; the helper
expects the output's parent directory to exist.

```bash
python <skill-dir>/scripts/review_coverage.py init --repo <checkout> --base <target-base> --head <head> --output <scratch>/coverage.json
python <skill-dir>/scripts/review_coverage.py check <scratch>/coverage.json --repo <checkout> --base <current-base> --head <current-head>
python <skill-dir>/scripts/review_coverage.py check <scratch>/coverage.json --repo <checkout> --base <current-base> --head <current-head> --require-complete
python <skill-dir>/scripts/review_coverage.py check <scratch>/coverage.json --repo <checkout> --base <current-base> --head <current-head> --audit-evidence --require-complete
```

Committed submodule pointers are inventoried with `--ignore-submodules=none`, overriding local/global ignore settings without changing user configuration.

Initialization refuses to overwrite a record. Refresh host metadata separately before supplying current refs: local refs alone do not prove remote freshness. The inventory includes renames (both paths), deletions, binary paths and submodules. Unsupported comparisons such as multiple merge bases require equivalent explicit records; do not change the review scope to make the helper pass.

## Record a verified checkpoint

After verifying a handoff or finishing a bounded pass, replace the selected file's review disposition without rewriting the inventory:

```bash
python <skill-dir>/scripts/review_coverage.py record <scratch>/coverage.json --repo <checkout> --base <base> --head <head> --path src/worker.py --status reviewed --unit R2 --evidence-file handoffs/r2.md --locator 'R2 / resume_job / scenario S3' --claim 'Recovery refreshes unavailable state before retrying; cold-start trace checked.'
python <skill-dir>/scripts/review_coverage.py record <scratch>/coverage.json --repo <checkout> --base <base> --head <head> --integration --status reviewed --evidence-file review-record.md --locator 'Integration scenarios S1-S4' --claim 'Lead verified the cross-unit traces and reconciled remaining findings.'
```

These are illustrative paths and conclusions, not evidence to copy into a real review. The command replaces that target's `status`, `units` (files only), `evidence` and `notes`; supply all evidence to retain, rather than assuming it appends. Repeat `--unit` or `--evidence` for additional unit IDs or free-text evidence. `--evidence-file`, `--locator` and `--claim` form one precise local citation and must be supplied together. Use `--notes` for limitations or exclusion rationale. Integration takes no `--unit`; include relevant units in the narrative/evidence.

`record` verifies the current comparison and complete inventory before atomically saving the result. A failed validation leaves the existing file unchanged. It preserves other dispositions, snapshot metadata and extra narrative fields. Use the exact inventory path, including a deleted file's old location or a renamed file's new location. To reopen a file, use `--status partial` or `unreviewed` and record why. A changed comparison needs a fresh inventory plus explicit reassessment; never relabel the old snapshot. Keep any earlier review evidence needed to inspect a superseded conclusion.

For one completed behavioral batch, use `record-batch <record> --input <batch.json>`
with the same `--repo`, `--base`, `--head`. Input is an object with `files` (an array
of distinct `{path, units, status, evidence, notes}` entries), optional `integration`
(`{status, evidence, notes}`), or both. It validates the existing record and whole
proposed result before atomic replacement; duplicate/unknown paths and metadata
edits fail without a write. Each file retains its own mapped evidence; this is not
a broadcast-reviewed command. The lead applies verified worker batches promptly.

## Evidence and compatibility

Schema version 1 accepts existing nonempty evidence strings and precise objects:

```json
{
  "path": "handoffs/r2.md",
  "locator": "R2 / resume_job / scenario S3",
  "claim": "The inspected retry path actively refreshes its dependency."
}
```

Object paths refer to local files, relative to the coverage record's directory or absolute. The checker verifies their existence and nonempty locator/claim. Keep remote source identities and retrieval evidence in the review record; free-text evidence can point there. The checker does **not** interpret symbol/section/line locators, validate the truth of claims, or read external URLs. Legacy strings remain supported, with existence/precision checked manually. New records should prefer precise citations when evidence is local. A single artifact may support several files if the locator and claim identify what was reviewed for each.

For shared evidence, explicitly map each path to a symbol, scenario, assertion or
mechanical transformation in the cited artifact. `--audit-evidence` warns when
three or more reviewed paths share the same primary structured claim (ignoring
case/whitespace), or have only free-text evidence. Common supplementary citations
do not trigger repetition warnings. This is a heuristic, not a semantic gate:
legitimate groups remain valid, legacy records still pass, and distinct wording
does not prove distinct investigation. Record the lead's warning disposition and
inspect the mapping; do not rewrite prose merely to silence a warning.

Keep the shared model policy's execution table in the review record. A coverage
evidence object may link to it, but successful validation does not attest the
requested or actual model, reasoning effort, delegation or semantic lead review.
The helper does not start agents or change model configuration; existing records
without execution metadata remain valid and are not retroactively certified.

Manual editing is also supported: edit only per-file `units`, `status`, `evidence`, `notes`, plus `integration`. Leave snapshot and path/change metadata untouched. For several citations, use a list of evidence objects and/or legacy strings.

## Meaning of completion

File states: `unreviewed`, `partial`, `reviewed`, `excluded`. Reviewed files require unit IDs and evidence; exclusions require rationale and prevent a full-coverage pass. Integration states: `unreviewed`, `partial`, `reviewed`, `not_applicable`; the last needs a reason. Reviewed integration requires evidence.

Without `--require-complete`, a structurally valid unfinished record remains resumable and is reported as incomplete. With it, all files must be reviewed and integration reviewed or justified as not applicable. A reviewed file can contain an open defect. Structural completion is only inventory/accounting: it does not establish source freshness, evidence quality, requirements access, test correctness, approval or absence of bugs. Report code/integration coverage separately from requirements and validation limits.

For deep investigation, keep the critical-boundary hypothesis/challenge ledger in the
[run record](run-record.md) and narrative. Complete file accounting cannot override
an inconclusive material investigation, missing challenge or unread truncated
region. Neither helper determines the number of bugs a review ought to find.

When maintaining the helper, run `python <skill-dir>/scripts/test_review_coverage.py`.

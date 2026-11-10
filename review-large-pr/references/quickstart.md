# Start, record and finish a review

These commands use Python's standard library and Git. They do not fetch refs,
choose review depth, run tests, spawn agents or publish anything. Run them from
any directory with the installed skill path. Choose durable evidence storage
outside the source checkout; preserve an existing run rather than overwrite it.

## Start once

```bash
python <skill-dir>/scripts/review_run.py start --repo <checkout> --base <target-base> --head <head> --output <task-workspace>/reviews/change-123
```

The folder contains `run.json` with exact revisions and an unreviewed inventory,
and `review-record.md` to fill. Project preferences are captured from
`.ai-skills.json`; use `--policy <file>` to select a different file. The current
lead is reused; no runtime model is inferred from those preferences.

Refresh remote PR metadata separately. Working-tree changes are not included.
For a changed source snapshot, start a new folder and explicitly reassess earlier
evidence. For an in-progress unchanged snapshot, continue the existing run.

## Assess actual work

After inspecting the change and relevant consumers, record depth and validation
needs. A source-only assessment requires a concrete explanation:

```bash
python <skill-dir>/scripts/review_run.py assess <review-folder>/run.json --depth standard --reason "Mechanical API rename; connected consumers inspected" --source-only "Source traces resolve this rename without runtime-dependent behavior"
```

Use `--depth deep` when the workflow requires it. Source-only evidence can resolve
a deep hypothesis, but cannot waive its primary/challenge obligations. When
execution is needed, use `--environment <entry.json>` instead of `--source-only`;
prepare its runtime and provenance under the [environment rules](review-context-and-environment.md).
The entry uses the existing environment schema from [checkpoints](checkpoint-records.md).

## Record verified evidence

Write the evidence first, then record each distinct path's actual conclusion:

```bash
python <skill-dir>/scripts/review_run.py record <review-folder>/run.json --path src/consumer.py --status reviewed --unit R1 --evidence-file review-record.md --locator "R1 / consumer.load" --claim "All inspected consumers use the renamed API with unchanged return semantics"
python <skill-dir>/scripts/review_run.py record <review-folder>/run.json --integration --status reviewed --evidence-file review-record.md --locator "Integration / S1" --claim "Lead traced producer output through the affected consumers"
```

These are illustrative claims, not evidence to copy. A disposition replaces that
path's prior fields; supply all evidence to retain, using batch checkpoints for
multiple citations. The command creates the receipt envelope and current revision
under a writer lock. `--expected-revision N` rejects a stale update; reconcile the
current record before retrying. Multi-repository runs require `--repository-id`.

Use [atomic checkpoint JSON](checkpoint-records.md) for batch file mappings,
boundaries, investigation/challenge results, or optional diagnostics. Do not mark
files reviewed from a worker completion message or suite total alone.

## Finish once

Fill the report, remove its incomplete-template marker, reconcile source/criteria
freshness and stop evidence writers. Then:

```bash
python <skill-dir>/scripts/review_run.py finish <review-folder>/run.json
```

The default destination is the new sibling `<review-folder>-archive`; choose
`--output <new-durable-folder>` to change it. Finish validates substantive review
records and automatically follows structured evidence and supported Markdown
links from the run/report. It never scans the whole folder or downloads URLs.
Use `--include <file>` for unlinked probes and `--json-record <file>` for additional
structured records. Ordinary JSON fixtures remain byte-for-byte opaque.

The archive contains original bytes, a portable evidence view and verified hashes.
Link its `files/review-record.md` in delivery. Git source and installed skills remain
external provenance. Check unsupported links and content sensitivity yourself;
[durable delivery](durable-delivery.md) explains those limits and partial delivery.

## Recover without losing work

| Problem | Next step |
| --- | --- |
| Invalid/missing Git ref | Resolve the intended commits through authorized host tooling, then retry start with those refs. |
| Existing run/output | Resume its run.json, or choose a new folder; never delete prior evidence to make start/finish pass. |
| Missing evidence | Save the real evidence or leave the affected path partial. Use explicit evidence repair for a known same-content move. |
| Outside-root evidence | Stage it under the evidence root and preserve its identity; do not rewrite historical pointers silently. |
| Incomplete run | Use check to identify gaps, then assess, record or checkpoint only verified work. A substantive partial review can still be delivered through the archive helper with its limitations stated. |
| Connector-specific access failure | Check available authorized CLI/API access before concluding the account lacks permission. An explicit platform denial is not permission to bypass a blocked action. |
| Unknown model/timing metadata | Continue the review; diagnostics are optional. Never invent settings or timestamps. |

Use `start --diagnostics` only when phase/lifecycle timing is useful. Record actual
phase completion and lead endpoints through checkpoints; finish does not invent
or close them. `check --require-complete --require-diagnostics` opts into both gates.

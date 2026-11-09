# Canonical checkpoints and fallback

Use one schema-2 `run.json` as the current source of coverage, investigations,
environment decisions and timing. The narrative explains the evidence and links
this record. Do not maintain a second independently updated file-status table.
Only the lead commits assessments; workers write distinct evidence artifacts.

## Start and attach scope

At the first observed intake, create the durable parent folder, then:

```bash
python <skill-dir>/scripts/review_run.py begin --output <run>/run.json --owner coordinator --role coordinator
```

If helper execution is unavailable, capture intake with the available host clock
immediately and preserve that observation for the manual record. Do not wait for
scope discovery or final consolidation to start timing. If it was already missed,
record the earlier endpoint as unknown; do not backdate a later observation.

Here `<run>` is the evidence directory. If packaging is planned, choose a sibling
archive destination under the same task-owned parent; it cannot be inside `<run>`.

An established Astra/xhigh lead working directly uses `--role lead`; this records
its observed start and one review phase. Neither role flag configures a model.
If earlier intake is known, use `--intake-at <ISO-time> --intake-source <evidence>`.
Use `--intake-unknown --intake-source <reason>` if recovering an unmeasured start.
For an already-running lead, likewise use `--lead-at <ISO-time> --lead-source
<evidence>` or `--lead-unknown --lead-source <reason>`. The automatically started
phase covers work from this bootstrap onward; earlier phases need their own
source-backed or explicitly unknown observations. Do not label bootstrap time as
the beginning of earlier lead work.
Never label this command as the original user-request time without evidence.

Pass the canonical path to the lead. Its first checkpoint records `lead_start`,
closes the coordinator intake phase and starts its context/review phase. Use
source-backed timestamps if the transition happened earlier. The coordinator
retains ownership of its observations but hands the sole writer role to the
lead during review, then receives it back at handoff.

Create an inventory with `review_coverage.py init` for each exact comparison.
Import it once with a stable repository ID. Imports rebase evidence pointers and
embed immutable snapshots; the seed inventory is historical from then on.
An import may include `files` and/or `integration` dispositions from an already
verified pass in the same entry. They are validated and saved atomically with the
import; an existing repository ID still cannot be reimported or relabeled.
Record lead configuration, mode/depth and the environment decision as established.
The complete assessment/investigation fields are in [run-record.md](run-record.md).

```json
{
  "id": "scope-1",
  "expected_revision": 0,
  "actor": "lead",
  "note": "Pinned inventory; bounded behavior assessment saved",
  "coverage": [{"id": "service", "import": "coverage-seed.json"}],
  "assessment": {
    "mode": "light",
    "selection_reason": "One bounded transformation and its consumer",
    "depth": {"level": "standard", "reason": "Connected source trace resolves the affected contract"}
  }
}
```

This is a partial example, not a completion claim. Add actual `lead` evidence and
lifecycle observations; never copy invented configuration. Paths in checkpoint
fields resolve from the canonical record's directory, not the input file.

```bash
python <skill-dir>/scripts/review_run.py checkpoint <run>/run.json --input <run>/scope-1.json
```

## Save a verified pass

Save the evidence artifact, then submit one checkpoint containing the pass's
changed dispositions, hypotheses, environment changes and phase observations.
Read the latest `revision`; each request has a unique `id`, `expected_revision`,
`actor` and `note`. Optional fields:

- `coverage`: entries with `id` plus `files` and/or `integration`, using the
  [coverage batch fields](coverage-record.md). Imported snapshots cannot be patched.
- `assessment`: `mode`, `selection_reason`, `lead`, `depth`.
- `boundaries`, `investigations`, `truncations`, `environments`: full entries
  upserted by ID. Unmentioned entries persist. Preserve failed attempts using
  distinct IDs; resolve uncertainty with evidence, not deletion.
  A light pass normally needs no boundary/investigation ledger: use the narrative's
  precise file and integration evidence. If recording an investigation, supply its
  referenced boundary in the same checkpoint or an earlier one.
- `events`: `owner` (defaults to actor), `phase`, `state`, `note`, optional
  `expect_seconds`. Start phases before work, close them with verified outcomes;
  phases may overlap and are never automatically closed.
- `milestones`: `name` (`lead_start`, `lead_complete`, `delivery_ready`, `delivered`;
  `intake` is already recorded by begin). Events/milestones default to observed
  now; use `at` plus `source`, or `unknown_time: true` plus `source`, for earlier
  boundaries. Delivery requires a host-observed `at` and source.
- `limitations`: append concise limitations. `recording`: helper/manual method
  and reason when transitioning to or from manual recording.

The helper validates the complete candidate before one atomic replacement.
An OS-held lock prevents concurrent writers and releases on process exit; its
empty `.lock` file is not an active writer and is not an archive artifact.
Receipts retain request hashes, changes and committed revisions. Retrying the
identical ID/payload is a no-op even if later checkpoints exist; a changed payload
or stale revision fails. Read current state and reconcile stale proposals rather
than forcing them through. Invalid evidence or a failed replacement changes none
of coverage, investigations or timing. This is interruption resilience, not an
authorization to retry an action rejected by platform policy.

At handoff, explicitly close completed phases, record `lead_complete`, and run:

```bash
python <skill-dir>/scripts/review_run.py check <run>/run.json --require-complete
```

Or use `checkpoint --require-complete` to validate the proposed final checkpoint
before saving it. A partial review can still record its actual completion time;
strict review checks remain incomplete. Do not defer useful delivery to manufacture
missing timing. Unknown endpoints must be explicitly recorded with a reason.
The coordinator records `delivery_ready` after consolidation; actual delivery is
recorded later only if observable, in a supplement if the archive was already sent.

For a small direct review, use one narrative as the evidence artifact, one review
phase, a scope/assessment checkpoint and a completion checkpoint when sufficient.
Combine related observations in those passes. Link the canonical record instead
of copying its snapshots, role settings, receipt IDs and timing into several tables.
Raw successful checkpoint inputs need not be separately archived: receipts retain
those requests. Preserve failed attempts that explain a limitation.

## Repair relocated evidence

Normal checkpoints validate old and new state and deliberately reject a missing
old pointer. For a known same-content move, use the explicit repair operation:

```bash
python <skill-dir>/scripts/review_run.py repair-evidence <run>/run.json --input <run>/relocation.json
```

The request has `id`, `expected_revision`, `actor`, `note` and `relocations`:

```json
{
  "id": "repair-1", "expected_revision": 2, "actor": "lead",
  "note": "Evidence moved; identity established by the retained archive",
  "relocations": [{"from_path": "old/trace.md", "to_path": "evidence/trace.md",
    "sha256": "<retained original content SHA-256>",
    "identity_source": "<saved original manifest or byte-identical backup>"}]
}
```

Paths resolve from the run directory. Supply the retained original digest and its
authority, not a new digest presented as proof of old content. The replacement must
exist and match it; an existing original must also match. Only active structured
evidence pointers change. Locators, claims, source snapshots, file identities and
prior receipts remain unchanged. A byte-identical prior manifest is saved beside
the run, and a new receipt records the mapping and backup hash. Stale, unrelated,
identity-changing and invalid replacements fail without updating the run. Identical
retries are idempotent; an interrupted replacement may leave the preserved backup,
which is verified on retry.

The helper verifies bytes against the supplied digest, not its historical authority.
Without recoverable identity, retain the evidence gap and investigate afresh in a
new run; do not manufacture a relocation. Schema-1 records retain their existing
manual/record operation and require an explicitly preserved original; this command
targets schema 2 only. When archiving, include the replacement and saved prior
manifest. Repair aliases resolve old receipt pointers in portable copies; original
bytes and hashes remain inspectable. Retain a local identity source when applicable.

## Runtime decision fields

Each `environments` entry has `id`, `purpose`, `status`, `reason`, `runtime` (a
structured evidence pointer to the runtime probe, or null), and `evidence` (precise
dependency provenance/smoke-check citations). States:

- `planned`: preparation remains outstanding.
- `ready`: matched runtime probe plus dependency/smoke evidence; use its exact
  executable/environment for the assigned commands.
- `limited`: unavailable/mismatched runtime, native prerequisites or another
  execution limitation; describe affected checks and conclusions.
- `source_only`: execution adds no relevant evidence; explain why.

The helper rejects `ready` with a mismatched/missing runtime probe. A limited
environment may support a qualified complete review when source evidence resolves
the obligations; it never establishes deployed-runtime equivalence. Runtime
selection and artifact compatibility still require lead judgment.

## Legacy and manual fallback

Schema-1 helpers remain readable. To adopt atomic checkpoints, preserve them:

```bash
python <skill-dir>/scripts/review_run.py promote <old>/run.json --output <new>/run.json
```

Promotion embeds the old inventory, preserves fingerprints/timing and records the
original manifest hash. It never fills missing observations with the promotion
time. Use a fresh run on a new source revision instead of promoting stale coverage.

If Python/helper execution is unavailable, use an allowed structured file editor
to maintain the same schema-2 record, starting from
[run-record-template.json](../assets/run-record-template.json) if needed. Preserve
a byte-identical prior copy before manual changes, set `recording.method` to
`manual` and explain the limitation. Keep the last real helper revision/receipts;
do not fabricate helper receipts or successful validation. Fill actual inventory,
fingerprints, lead evidence, dispositions, investigation entries and observations.
The JSON template includes the embedded coverage shape: each repository entry has
`id`, `snapshot`, and `record`; the inner record is the coverage helper's schema-1
inventory with the same snapshot, complete changed `files`, and `integration`.
Use structured evidence objects with `path`, `locator`, and `claim` for reviewed
dispositions. The placeholders intentionally cannot pass validation unchanged.
Unmeasured timing remains unknown. Resume helper checks when tooling is available.
An unsupported comparison needs explicit equivalent snapshot/inventory evidence
and a disclosed validator limitation; never invent a representable Git comparison.

If a platform rejects an action, stop that action and preserve the failure.
This fallback is not permission to repeat its effects through another tool,
payload or agent. Deliver permissible substantive work with separate **review
coverage**, **record validation** and **archive integrity** statuses. An archive
failure does not erase reviewed evidence; a polished narrative does not complete
stale coverage records. Preserve recoverable artifacts and state what remains.

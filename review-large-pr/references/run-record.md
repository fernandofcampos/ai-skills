# Execution provenance, depth and progress

Use `scripts/review_run.py` for local records or preserve equivalent fields when
the comparison/tooling is unsupported. It uses Python's standard library and the
coverage helper; it does not start agents, fetch refs, run tests or attest models.
The lead alone updates the central manifest. Workers return batch artifacts and
progress observations for the lead to record.

## Lead routing

Apply the shared model policy first. Use current-task runtime configuration or
explicit invocation evidence, including effort and assigned role. Check available
metadata once if unknown; do not search other chats, infer account defaults or
use a model's self-description. This illustrative input exercises the helper;
replace it with observed configuration, never copy it as execution evidence:

```json
{
  "agent": "/root",
  "role": "unassigned",
  "model": "gpt-6-astra",
  "effort": "xhigh",
  "configuration_source": "current task runtime configuration",
  "can_delegate": true
}
```

```bash
python <skill-dir>/scripts/review_run.py route --input <scratch>/routing-input.json
```

Known Astra/xhigh returns `reuse_current`; an `existing_lead` returns reuse of that
identity; assigned reviewers/authors retain their assignment. An assigned lead
with unknown settings retains its role and reports the gap. Only an unassigned
agent without usable configuration/existing lead routes to `delegate_once` when
supported. Otherwise report the configuration limitation and continue permitted
work. The command recommends routing from supplied data; it neither detects the
current model nor proves the requested backend ran.

The default remains Astra/xhigh. An explicit user model choice has precedence
under the shared policy: when one exists, include `user_override` with
`authority: "explicit_user"`, the requested `model`, `effort` and a precise `source`
for that instruction in routing input and the manifest's `lead` object. Never
create an override from a runtime limitation or an agent preference. It does not
replace configuration/invocation evidence for the chosen settings.

## Initialize and record

For new reviews follow [canonical checkpoints](checkpoint-records.md): `begin`
captures intake before scope discovery, then `checkpoint` embeds inventories and
commits coverage, investigations and timing together in schema 2. Its JSON template
also defines the manual fallback. Do not directly edit current helper records or
update imported coverage seeds. Schema-1 `init`, `event`, `milestone` and standalone
coverage commands remain supported for old runs; `promote` preserves them when
moving to the canonical format.

Fingerprints identify installed resources, not proof every reference was read.
Record conditional resources actually used. Preserve old hashes on drift and note
newly used versions; neither promotion nor a later run relabels earlier evidence.
New records can initially have unassessed mode/depth and no inventory; strict checks
reject this until the actual assessment is attached.

Assessment and investigation fields (submit through checkpoint):

- `mode`: `full` once the review is assessed. `unassessed` is the bootstrap state;
  `full` identifies the workflow and does not claim complete coverage.
- `selection_reason`: concrete scope, interactions and uncertainty being reviewed.
- `lead`: `id`, `selection` (`current`, `existing`, `delegated`, `unavailable`),
  `model`, `effort`, `configuration_source`, `evidence_kind` (`runtime_config`,
  `invocation`, `unknown`). Describe requested versus confirmed settings honestly.
- `depth`: `level` (`standard` or `deep`) and behavioral `reason`. Deep requires
  a primary investigation and challenge for each critical boundary; both depths
  require precise coverage and integration evidence.
- `boundaries`: objects with stable `id`, actual `paths` (including unchanged
  consumers) and the critical `contract`. The lead verifies this inventory for
  omissions; a helper cannot infer all important boundaries from filenames.
- `investigations`: one entry per hypothesis/boundary/pass, with the shape below.
  Add distinct IDs for additional hypotheses. Preserve superseded reasoning in
  the linked batch artifact when revising a result; do not erase failed attempts.
- `truncations`: `id`, `source`, `remaining` (the omitted region), `status` (`open`
  or `resolved`) and `evidence`, an array using the same evidence objects as
  investigations (`[]` while no evidence exists). Closing one requires actual
  follow-up evidence; a prose string cannot replace the array.
- `limitations`: concise scope, environment, independence and runtime limits.
- `timing.milestones`: lifecycle observations made by the coordinator/lead, each
  with `name`, `at`, `recorded_at`, `basis` and `source`. Schema 2 requires intake/lead-start/lead-complete entries at completion,
  permitting explicitly unknown times; older records retain timing warnings.

The helpers continue to accept historical `light` records for compatibility.
New reviews use `full`; the skill no longer selects a light workflow. Preserve
historical records and reassess their evidence against the current workflow when
continuing earlier work.

Illustrative resolved investigation (replace it with actual evidence):

```json
{
  "id": "H1", "boundary": "B1", "pass": "primary", "reviewer": "R1",
  "hypothesis": "A lost acknowledgement permits a second external effect",
  "assumption": "The fixture only tests acknowledged replies",
  "method": "Base/head trace and interrupted-reply experiment",
  "result": "refuted",
  "evidence": [{"path": "batches/B1.md", "locator": "Lost reply / submit",
    "claim": "The retry retrieves the same committed request identity before submission"}],
  "conclusion": "The connected retry preserves the original external-effect identity",
  "lead_verified": true, "lead_check": "Inspected submit guard, caller and saved two-attempt trace"
}
```

Results are `pending`, `supported`, `refuted` or `inconclusive`; supported means
the hypothesis held, which may be a defect, never an automatic correctness pass.
A resolved entry needs evidence, conclusion and actual lead verification.
Challenge entries additionally record `independence` (`fresh_reviewer` or
`separate_lead_pass`), `independence_reason` and boolean `prior_findings_withheld`.
A fresh reviewer must differ from the primary reviewer for that boundary; record
prior exposure and never conceal safety constraints. A separate lead pass must
name the limitation preventing fresh review and is not described as independent.

## Timing and liveness

Use a small set of meaningful phases: context, environment, behavioral batches,
integration/challenges and consolidation. Phases may overlap; report wall time
separately from their intervals. Do not infer monetary cost or efficiency from
raw token totals or sum overlapping durations. A single phase can be sufficient
for a focused follow-up. Event states are `start`, `progress`, `waiting`, `blocked`, `complete`, `failed`.
Use a new phase ID for a retry, keeping the failed attempt. Notes identify the
latest saved evidence, known process/agent state, remaining question and next step.

Capture coordinator intake before delegation, passing the timestamp and source to
the lead. Record `lead_start`, `lead_complete`, `delivery_ready` and `delivered`
when actually observed. The coordinator owns any endpoints outside lead execution.
If exact user-request time is unavailable, use the first observed intake and state
that scope; never substitute later manifest creation. These commands illustrate
retrospective source evidence and missing measurements:

```json
{
  "id": "earlier-context-timing", "expected_revision": 2,
  "actor": "lead", "note": "Preserve an unmeasured earlier interval",
  "events": [
    {"phase": "earlier-context", "state": "start", "unknown_time": true,
     "source": "Context was read before timing began", "note": "Earlier context work"},
    {"phase": "earlier-context", "state": "complete", "unknown_time": true,
     "source": "Saved evidence establishes completion only", "note": "Context assessment saved"}
  ]
}
```

Replace illustrative timestamps with actual evidence. Default checkpoints mean
“observed now”; use `--at` plus `--source` for a known earlier boundary, or
`--unknown-time` plus an explanation. Logging time is preserved separately from
effective time. Unknown endpoints produce unknown duration, not zero. Milestones
are unique; preserve earlier observations and explain corrections in a separate
supplement instead of silently replacing them. Phase observations may be logged
after the work, but their effective times must retain order within that phase.

The checker distinguishes intake-to-delivery, intake-to-ready, lead execution,
pre-lead coordination and post-lead delivery intervals when their endpoints exist.
It labels manifest age only as an observation window. Legacy event intervals are
checkpoint intervals, not attested phase measurements. Missing timing warns without
changing code-review completeness. A ready result or lead completion is not
user-visible delivery; leave total time unknown until the host supplies that
evidence. Avoid delaying substantive delivery merely to fill timing fields.
Unexplained scheduler/tool/coordination gaps remain unclassified.

Set `--expect-seconds` for a reasonable next observation based on the task. An
overdue observation produces an advisory warning, not a stalled/failed verdict.
Check one compact agent status, process status or saved checkpoint; continue
independent work when it is progressing. Agree a later checkpoint for a known
long-running test. Do not repeatedly poll unchanged state or interrupt merely
because response text is slow. If there is no progress or the worker failed,
preserve its evidence and reassign only permissible unfinished work. Platform
screening never authorizes rerouting/rephrasing the blocked action. Incomplete
material evidence remains a gap. Keep user updates substantive and timely under
the host's communication rules, without a stream of unchanged status messages.

## Completion and resumption

```bash
python <skill-dir>/scripts/review_run.py check <scratch>/run.json --require-complete
```

Strict run checks require complete embedded (or legacy referenced) coverage, recorded Astra/xhigh
configuration/invocation evidence (or an evidenced explicit user override), assessed
depth, closed phases, no unread truncations and resolved lead-verified investigations. Deep requires a primary
and challenge for every listed boundary. Open defects are allowed; unresolved
required hypotheses are not. Structural success cannot establish sufficient
depth, independent reasoning, remote freshness or absence of omitted boundaries.
Review the evidence audit warnings and semantic completion gate separately.

The checker prints review/record obligations separately from execution-policy
conformance; `--require-complete` still requires both. Report the substantive
verdict from the actual investigation even if policy evidence is unavailable,
with that limitation explicit. Record/timing failures are distinct from missing
source investigation. Neither structural status certifies semantic completeness.
Do not rerun a finished review just to obtain different model evidence or infer
backend settings from an invocation request.

At unchanged revisions, newly discovered risks retain the same in-progress
manifest/checkpoints; preserve the earlier narrative and record reopened obligations.
At changed source revisions, preserve the old run, initialize new coverage/run
records and link explicit reassessment before carrying evidence forward. Do not
edit pinned identities to make stale work pass. Failed optional experiments may
remain recorded if other evidence resolves the question; disclose their limits.

Apply the [criteria freshness contract](../../document-feature-design/references/review-handoff.md)
on every resumption, independently of Git changes. Preserve completed prior runs
and verdicts when beginning a continuation; carry evidence only with an explicit
source-and-criteria applicability reason. An in-progress run may append the bounded
reassessment and reopen only affected dispositions.

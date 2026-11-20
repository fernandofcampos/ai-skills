# Evaluate workflow outcomes

Compare retained agent outputs on identical sources and task constraints. For a
skill migration, use the previous installed pair as the baseline and the revised
pair as the candidate. For a comparison with built-in behavior, leave both
skills out of the baseline workspace.

```sh
python3 evaluations/workflow_eval.py prepare --held-out --output /path/to/new-evaluation
```

Preparation creates separate task packets, a scoring key and unfilled label
files in a new directory. Give the agent only its case and the skill pair for its
arm. Keep this evaluation directory, the scoring key and other outputs outside
the agent's task workspace.

| Held-out task | What to inspect |
| --- | --- |
| caption-timebase | Does the review trace the public call across the unit conversion, identify a reachable regression at a nonzero offset, and check the waveform caller? |
| offline-index-adr | Does the draft distinguish the accepted offline requirement from the proposed SQLite design, preserve the brief's identity, and satisfy the publisher's frontmatter restriction? |

Omit `--held-out` to regenerate the original teaching corpus. Several answers to
those tasks ship in the skills' examples. Use them to calibrate the evaluator.
Use the held-out packets or independent project cases to measure behavior.

| Task | What it measures |
| --- | --- |
| cross-boundary | Introduced tenant-cache defect amid 40 mechanical edits; connected behavior and honest coverage |
| follow-up | Closure of the fixed finding, source/criteria reassessment and reuse of applicable evidence |
| mechanical | False positives and unnecessary investigation for a broad mechanical change |
| concise-adr | Source-grounded rationale, unknown acceptance/implementation/deployment, alternatives and revisit conditions |

## Run the two arms

Use separate fresh tasks/workspaces for baseline and skill. Give each only its
case folder and `prompt.txt`. Install the applicable sibling pair for each skill
arm and invoke the requested skill. Record the package revision for each arm.
For follow-up, provide the same supplied prior review in both arms.

Hold model, effort, tools and task budget constant within each case and record them.
To isolate prompt changes, compare both revisions on the same GPT-6.2 variant.
Repeat the matched pair on each model when evaluating both Astra and Sol. Refresh each
workspace from the same packet, preserve commits, randomize arm order, and repeat
runs when evaluating nondeterministic behavior. Preserve raw output and host/tool
traces, including interruptions. Do not give one arm oracle hints or extra time.
Semantic judgments should be made without knowing which arm produced the output.

## Judge retained evidence

An evaluator distinct from the author fills the generated label files. Name the
evaluator and actual output/trace paths relative to the labels directory. Match
findings by root cause and trigger, not wording or finding count; a label cites the
oracle ID only when the output establishes that defect. Adjudicate credible new
findings before treating them as unsupported or changing the frozen corpus.

Each judgment needs specific output/trace locators and reasoning in `evidence_notes`.
Use `true`, `false` or `null` for each quality check; unknown is never a pass.
Count unsupported findings and unsupported ADR claims separately from matched defects. An attribution of decision authority needs a source assigning that role. A clean task's recall is undefined, not 100%.
Do not reward a skill for inventing extra defects or generating more artifacts.

| Observation | Meaning |
| --- | --- |
| source_traceable | Material conclusions cite inspectable sources at the recorded baseline. |
| connected_path_checked | The review traces the actual caller through the changed boundary and checks a control. |
| coverage_honest | Claims of reviewed/generated/excluded paths match retained evidence. |
| fixed_finding_closed | The follow-up verifies the fix and does not report the old defect as current. |
| unaffected_evidence_reassessed | Reused conclusions have source/criteria applicability reasons. |
| proportional_investigation | Mechanical work receives sufficient evidence without invented architectural work or finding quotas. |
| separates_status | The ADR keeps proposal, implementation and deployment status distinct. |
| alternatives_grounded | Alternatives and rationale are supported or explicitly presented as current analysis. |
| revisit_conditions | Concrete evidence-backed conditions explain when to reconsider the decision. |
| destination_format | The saved ADR respects the destination's formatting restriction and remains structurally valid. |
| clarifications | Requests for information already supplied or safely inferable; necessary clarification is not penalized. |
| repeated_work | Completed unaffected investigations repeated without new evidence, failure or uncertainty. |
| setup_calls | Tool calls devoted to environment/artifact setup; retain trace locators defining the counted calls. |
| elapsed_seconds | Host-observed task start to final output; include delays consistently across arms. |

Process metrics require a retained trace; leave them `null` when unobserved. Artifact
hashes preserve what was judged, but cannot certify the evaluator's interpretation.
Keep timing unknown when the host does not expose it; do not infer it from token totals.

```sh
python evaluations/workflow_eval.py compare --oracle /path/to/new-evaluation/oracle.json --baseline /path/to/new-evaluation/baseline-labels.json --skill /path/to/new-evaluation/skill-labels.json
python -m unittest discover -s evaluations -p 'test_*.py'
```

Comparison rejects mismatched corpora/conditions, missing output, duplicate cases,
invalid judgments and fabricated zero defaults for missing process traces. It reports
per-case missed defects, precision/recall where defined, quality judgments and process
observations. Interpret improvements with their supporting evidence; a unit-test run
or a simulated label file is not a head-to-head agent benchmark.

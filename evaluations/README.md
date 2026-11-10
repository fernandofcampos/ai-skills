# Evaluate workflow outcomes

The helper suites test record mechanics. This workflow compares actual agent
outputs with and without the skills, using the same inputs and conditions. It
includes reproducible synthetic starter tasks; passing them does not establish
performance on production PRs. Add retained real PR/design cases before making
broader claims.

```sh
python evaluations/workflow_eval.py prepare --output /path/to/new-evaluation
```

Preparation creates immutable Git comparisons, separate task packets, an evaluator
oracle, and unfilled label files. It never invokes an agent, posts reviews or changes
an existing checkout. Existing output is never overwritten.

| Task | What it measures |
| --- | --- |
| cross-boundary | Introduced tenant-cache defect amid 40 mechanical edits; connected behavior and honest coverage |
| follow-up | Closure of the fixed finding, source/criteria reassessment and reuse of applicable evidence |
| mechanical | False positives and unnecessary investigation for a broad mechanical change |
| concise-adr | Source-grounded rationale, unknown acceptance/implementation/deployment, alternatives and revisit conditions |

## Run the two arms

Use separate fresh tasks/workspaces for baseline and skill. Give each only its
case folder and `prompt.txt`; keep the oracle, label files, completed examples and
the other arm's output outside its workspace. For baseline, use normal built-in
review/documentation behavior without installing or invoking these skills. For
the skill arm, install the sibling pair and explicitly invoke the applicable skill.
For follow-up, provide the same supplied prior review in both arms.

Hold model, effort, tools and task budget constant and record them. Refresh each
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
Count unsupported findings separately. A clean task's recall is undefined, not 100%.
Do not reward a skill for inventing extra defects or generating more artifacts.

| Observation | Meaning |
| --- | --- |
| source_traceable | Material conclusions cite inspectable sources at the recorded baseline. |
| connected_path_checked | The review establishes the actual caller/cache interaction and control, not only an isolated suspicious line. |
| coverage_honest | Claims of reviewed/generated/excluded paths match retained evidence. |
| fixed_finding_closed | The follow-up verifies the fix and does not report the old defect as current. |
| unaffected_evidence_reassessed | Reused conclusions have source/criteria applicability reasons. |
| proportional_investigation | Mechanical work receives sufficient evidence without invented architectural work or finding quotas. |
| separates_status | The ADR keeps proposal, implementation and deployment status distinct. |
| alternatives_grounded | Alternatives and rationale are supported or explicitly presented as current analysis. |
| revisit_conditions | Concrete evidence-backed conditions explain when to reconsider the decision. |
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

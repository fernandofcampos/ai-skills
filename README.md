# Codex review and design skills

Two companion skills for source-grounded code review and architecture documentation:

| Skill | Purpose |
| --- | --- |
| [review-large-pr](review-large-pr/SKILL.md) | Review large or complex PRs with whole-change reasoning, revision-specific coverage, and durable evidence. |
| [document-feature-design](document-feature-design/SKILL.md) | Create and maintain feature designs, RFCs, and ADRs with an accessible overview and traceable architectural detail. |

Both complete skill directories are included, with their templates, references, helper scripts, tests, and Codex metadata. The design skill owns the shared model policy and handoff contract, so install **both directories as siblings**.

## Install

Clone this repository, then copy both folders into your Codex skill directory:

```sh
git clone https://github.com/fernandofcampos/ai-skills.git
cd ai-skills
skill_root="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_root"
cp -R review-large-pr document-feature-design "$skill_root/"
```

For an existing installation, retain a backup and replace both complete folders together after active reviews finish. See the [paired installation guidance](document-feature-design/references/paired-installation.md).

## Use

Use `review-large-pr` when a large or complex change needs architectural context, cross-component investigation, or durable checkpoints for resumed work. Routine small PRs can use Codex's built-in review. Judge complexity by the interactions and uncertainty, not a fixed line or file count. A focused follow-up to a large review stays in the same workflow and reuses valid evidence.

Example requests in Codex:

```text
Use $review-large-pr to review https://github.com/OWNER/REPO/pull/123.
```

```text
Use $document-feature-design to document the feature in this repository.
```

The [shared model policy](document-feature-design/references/model-policy.md) specifies lead and worker preferences, how to reuse an existing lead, and how to report unavailable settings. Reading a skill does not switch the current model. Review publication, source changes, and deployment remain subject to the authority in the user's request.

## Review commands

The [quickstart](review-large-pr/references/quickstart.md) uses the existing helpers
through one interface. Start in a new evidence folder outside the source checkout:

```sh
python review-large-pr/scripts/review_run.py start --repo /path/to/repo --base main --head feature --output /path/to/reviews/feature
```

Use `assess` for the depth and validation decision, `record` for precise file or
integration evidence, and `checkpoint` for batch investigations and challenges.
After filling the report and reconciling all required evidence:

```sh
python review-large-pr/scripts/review_run.py finish /path/to/reviews/feature/run.json
```

Finish validates the review records, collects linked evidence and checks a portable
archive. It preserves opaque JSON fixtures and does not scan unrelated scratch files.
These commands do not fetch refs, run the review, install dependencies or publish it.

The current lead is reused. Optional project model preferences live in
`.ai-skills.json` at the repository root; start captures them once. Explicit user
choices take precedence. Detailed model metadata and timing are optional:
`check --require-complete` checks substantive records, while `--require-diagnostics`
opts into timing/model checks. Missing evidence still prevents a complete review.

Existing schema-1 and schema-2 records remain readable. Update both installed skill
folders together before using the new commands. Automation that relied on timing
or model checks under `--require-complete` should add `--require-diagnostics`.
The routing helper now returns `preferred_model` / `preferred_effort` and reuses
the current lead instead of recommending delegation solely for model compliance.

## Examples and evaluation

- [Filled large-PR review](review-large-pr/examples/large-pr-review.md)
- [Focused follow-up](review-large-pr/examples/follow-up.md)
- [Concise ADR](document-feature-design/examples/concise-adr.md)
- [Workflow evaluation against built-in behavior](evaluations/README.md)

The examples use explicitly fictional sources. The evaluation workflow supplies
reproducible tasks and compares independently judged, retained agent outputs; its
unit tests do not establish an advantage over built-in review or documentation.

## Validate the package

From the repository root, with Python 3 and Git available:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r document-feature-design/scripts/requirements.txt
.venv/bin/python review-large-pr/scripts/review_run.py check-installation --skill-root review-large-pr
.venv/bin/python -m unittest discover -s review-large-pr/scripts -p 'test_*.py'
.venv/bin/python document-feature-design/scripts/test_validate_design_document.py
.venv/bin/python document-feature-design/scripts/validate_design_document.py document-feature-design/examples/concise-adr.md --project-root . --require-discovery-metadata --strict
.venv/bin/python -m unittest discover -s evaluations -p 'test_*.py'
```

The package check verifies the sibling layout and local resource links. The test suites exercise the bundled helpers and document validator; they do not establish the correctness of a particular PR review or architectural decision.

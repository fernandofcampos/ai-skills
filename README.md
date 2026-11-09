# Codex review and design skills

Two companion skills for source-grounded code review and architecture documentation:

| Skill | Purpose |
| --- | --- |
| [review-large-pr](review-large-pr/SKILL.md) | Review PRs with adaptive light/full depth, revision-specific coverage, and durable evidence. |
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

Example requests in Codex:

```text
Use $review-large-pr to review https://github.com/OWNER/REPO/pull/123.
```

```text
Use $document-feature-design to document the feature in this repository.
```

The [shared model policy](document-feature-design/references/model-policy.md) specifies lead and worker settings, how to reuse an existing lead, and how to report unavailable settings. Reading a skill does not switch the current model. Review publication, source changes, and deployment remain subject to the authority in the user's request.

## Validate the package

From the repository root, with Python 3 and Git available:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r document-feature-design/scripts/requirements.txt
.venv/bin/python review-large-pr/scripts/review_run.py check-installation --skill-root review-large-pr
.venv/bin/python -m unittest discover -s review-large-pr/scripts -p 'test_*.py'
.venv/bin/python document-feature-design/scripts/test_validate_design_document.py
```

The package check verifies the sibling layout and local resource links. The test suites exercise the bundled helpers and document validator; they do not establish the correctness of a particular PR review or architectural decision.

# Shared model preferences and lead ownership

Read this once when either skill starts. Explicit user choices and runtime
restrictions take precedence. Preferences describe desired settings; reading a
skill or configuration file never switches the current conversation's model.

## Resolve preferences once per project

The default preferences are `gpt-6-astra` / `xhigh` for the lead and
`gpt-6.1-sol` / `high` for focused review or documentation authoring. For difficult
architectural reconstruction, the lead may prefer `gpt-6-astra` / `high` for a
bounded authoring assignment. These are preferences, not completion requirements.

A project can set its defaults in `.ai-skills.json` at the repository root:

```json
{
  "schema_version": 1,
  "models": {
    "lead": {"model": "gpt-6.1-sol", "effort": "high"},
    "reviewer": {"model": "gpt-6.1-sol", "effort": "high"},
    "documentation_author": {"model": "gpt-6.1-sol", "effort": "high"}
  }
}
```

Omitted roles retain skill defaults. The configuration contains data only: no
commands, plugins or executable hooks. Model names and effort values must be
nonempty strings; actual availability is determined by the runtime. An invalid
file is an actionable error, not permission to silently ignore project choices.

`review_run.py start` discovers the file at the resolved repository root, or uses
an explicit `--policy <file>`, and saves its contents, source and hash in the run.
Resume from that captured preference; do not silently relabel earlier work when
project settings change. A new run captures the current file. For standalone
documentation, read the same file once at the destination project's root. Resolve
multi-repository ambiguity using the designated delivery project or an explicit
policy. A direct user choice overrides both the project file and defaults; retain
its source in the existing `user_override` field when recording model metadata.

## Reuse the lead; delegate useful work

Reuse the current or already designated lead even if its settings differ or are
not exposed. Make at most one bounded check of current-task metadata when useful.
Do not infer the model from writing style, account defaults or unrelated sessions.
Do not create a coordinator and replacement lead solely to match a model name.

The lead owns scope, source assessment, assignments, integration, semantic checks
and the result. A review invoking documentation retains that lead. Assigned
reviewers/authors stay within their packet and do not start another lead or delegate
further. Retain partial work when handing off a difficult question.

Delegate only when bounded independent work materially improves focus or elapsed
time and the user/runtime permits it. Reuse sufficient documents; perform cheap
corrections directly. Assign substantial writing from verified context to an
available capable author. For unresolved consequential architecture, the lead
resolves or delegates the specific question with existing evidence. A stronger
model cannot manufacture missing requirements or approval.

When requesting an override, specify both model and effort and supply the role,
lead identity, exact sources, requirements, scope, destination and validation plan.
Respect tool restrictions on fresh contexts and capacity. If the preferred setting
is unavailable, continue with the capable current lead and disclose the limit once.
Do not modify global settings, install profiles or retry unsupported calls merely
for preference compliance. A material capability or evidence gap remains a review
limitation regardless of model choice.

## Keep accountability separate from diagnostics

Record the lead identity and substantive worker handoffs. Detailed requested versus
runtime-confirmed settings, timing and liveness observations are optional. When
supplied, distinguish invocation evidence from actual runtime confirmation; unknown
metadata stays unknown. Keep these details in the review/validation record, outside
architectural decisions and discovery metadata.

`check --require-complete` requires substantive record obligations. It does not
require model telemetry or timing. `check --require-diagnostics` explicitly audits
those optional observations and reports their failures separately. Neither flag
attests reasoning quality or backend execution. Malformed supplied evidence remains
an error; optional diagnostics are not permission to invent measurements.

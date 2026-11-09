# Shared model policy for design and large-PR review

Read this policy when either skill starts, before assigning work. It is the single
source of model-selection criteria for both skills. Explicit user choices and
runtime restrictions take precedence. Skill text does not switch a running
conversation's model or reasoning effort.

## One lead, bounded workers

- **Lead:** `gpt-6-astra`, effort `xhigh`. Owns scope, source/context assessment,
  assignments, integration, semantic validation and the consolidated result.
- **Documentation author:** select using the table below; effort `high`.
- **Focused code reviewer:** `gpt-6.1-sol`, effort `high`. Give unresolved
  cross-unit judgments back to the lead rather than starting another whole review.

Before creating a lead, check the current assignment and available current-task
runtime configuration or explicit invocation/spawn settings, including effort.
Reuse an existing designated lead; an assigned worker never starts leader routing.
If the current agent is configured as Astra/xhigh, use it as lead without creating
an intake-only parent. Record the configuration source and reuse decision. Never
infer configuration from writing style, self-description, account defaults or
unrelated sessions; do not crawl conversation history to guess it.

If current configuration is unknown, make one bounded check of available
current-task metadata. Unknown is not evidence of a different model. With no
existing lead and no usable confirmation, delegate **one** explicitly configured
Astra/xhigh lead when tools permit and record why reuse could not be established.
An already assigned lead with missing configuration evidence reports that gap;
it does not recursively create a replacement. The parent of a delegated lead is an
intake/delivery coordinator: it does not duplicate the review or write the lead's
coverage record. Do not create a separate user-visible chat for this routing.

An invocation of document-feature-design by an existing review lead shares that
lead. An assigned author or reviewer follows its assignment, skips leader/model
routing, and does not delegate further. Mark the packet role as `lead`,
`documentation-author` or `reviewer`; include any existing lead identity. This
prevents recursive leaders and author-to-author delegation. A standalone design
request follows the same lead policy; it does not require the user to invoke a
second skill or choose a documentation model manually.

## Select documentation work after assessing context

| Observed work | Execution choice | Reason to record |
| --- | --- | --- |
| An existing design is sufficient and applicable to the requested review; no document edit is requested | Reuse; no documentation worker | Applicable sources/sections and the path checked |
| A small, bounded correction, link/metadata repair, or similarly cheap update | Lead performs it directly | Delegation would cost more than the work; use the lead's actual settings |
| Substantial writing from clear scope, verified behavior and known decisions | `gpt-6.1-sol` / `high` | The remaining work is bounded investigation and synthesis |
| Substantial work must reconstruct architecture, reconcile material conflicting evidence, or reason through unresolved consequential authorization, ownership or recovery decisions | `gpt-6-astra` / `high` | Name the specific unresolved architectural question or conflict |

Classify the required reasoning, not document length, repository count or a
security/finance keyword alone. A well-understood sensitive feature can use Sol;
a short ambiguous decision may warrant Astra. Reuse does not override an explicit
request to update or replace a document. Missing information must remain an
explicit gap; a stronger model cannot manufacture evidence or approval.

If a Sol author discovers a material question meeting the Astra criteria, it
returns the sources, partial artifact and unresolved question to the lead. The
lead decides whether to resolve that bounded question itself or assign an Astra
author with the retained evidence. Preserve useful work; do not blindly rerun the
whole task or escalate for a dependency error or failed structural check. The
lead always validates the result against sources regardless of author model.

## Execute and record the decision honestly

Specify both model and effort explicitly when spawning. Respect tool-specific
constraints: if overrides require a fresh context (`fork_turns="none"`), supply
the skill path, role/lead identity, source roots and exact snapshots, authoritative
requirements, scope/gaps, destination, existing artifacts and validation plan.
Do not assume the worker inherited the conversation. Share usable paths or source
content with enough access to complete the assignment; never pass credentials.

Count the coordinator, lead and workers against available capacity. Reuse the
designated lead, sequence workers when needed, and keep trivial work with it.
An agent-capacity limit is not a reason to bypass the lead or create a recursion.
If no worker slot can become free because the coordinator and lead exhaust the
capacity, the existing lead completes the authoring or review directly and records
`lead-direct` with that limitation. Do not wait for the lead's own coordinator to
finish before progressing.
If requested models, effort overrides or delegation are unavailable, disclose the
specific limitation and the actual/unknown settings. Continue useful authorized
inspection and checks, but do not silently substitute a model or claim the
Astra/xhigh lead requirement was met. Do not modify global settings, install an
agent profile or claim to switch the current conversation just by reading this
file. Report a limitation once rather than repeatedly retrying unsupported calls.

Keep one compact execution record alongside validation evidence. For review use
the review record; for standalone documentation use the local
[design validation record](../assets/design-validation-template.md) or an equivalent
existing report. Record each role/task, selection and concrete reason, requested
model/effort, agent identity, execution evidence and returned result. Distinguish
requested settings from runtime-confirmed settings; write `not exposed` when the
runtime provides no confirmation. Record `reused`/`lead-direct` when no worker ran,
and retain superseded attempts and escalation reasons. Do not turn model choices
into architectural decisions, document-discovery metadata, or proof of approval.

Report substantive completeness and execution-policy conformance separately.
A missing or mismatched model invocation is an execution-policy limitation, not
proof that the source investigation is incomplete or incorrect. Conversely, the
preferred model cannot close missing evidence. Report the actual substantive
verdict and the policy gap without inventing a user override or spawning a new
lead after the designated lead has finished. Strict helper completion may require
both; its failure must identify which obligation remains unmet.

The existing design and coverage helpers validate their respective artifacts;
they do not choose models, start agents or attest which model actually ran.

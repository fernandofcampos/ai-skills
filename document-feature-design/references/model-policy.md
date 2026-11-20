# Model preferences and lead ownership

Both skills keep the current or designated lead. Preferences help choose a model when the host offers a choice. An existing lead continues with its available settings. The runtime controls which models and reasoning efforts can actually run.

## Defaults for new work

| Role | Preferred Codex model | Reasoning effort | Assignment |
| --- | --- | --- | --- |
| Lead | `gpt-6.2-astra` | `medium` | Resolve competing evidence, verify cross-component behavior and own the verdict or design decision record. |
| Reviewer | `gpt-6.2-sol` | `medium` | Investigate one bounded contract or challenge an assumption against pinned sources. |
| Documentation author | `gpt-6.2-sol` | `medium` | Draft or update an artifact from identified sources and return it for verification. |

These are package starting points. If a consequential question still has competing explanations after a focused trace, consider more effort or an available Astra assignment for that question. Missing requirements call for source evidence. [OpenAI model selection guidance](https://developers.openai.com/api/docs/guides/model-selection)

## Choose settings once

A direct user choice takes precedence over the project setting for that role, which takes precedence over the table. Use the destination project's `.ai-skills.json` or an explicitly supplied policy file. Set just the roles the project wants to override. For example, a project can request greater effort for its reviewers.

```json
{
  "schema_version": 1,
  "models": {
    "reviewer": {"model": "gpt-6.2-sol", "effort": "high"}
  }
}
```

The other role keys are `lead` and `documentation_author`. Each entry requires nonempty `model` and `effort` strings. The routing input spells the author role `documentation-author`. The helper accepts other model names for projects with different runtime catalogs. Resolve an invalid policy explicitly.

`review_run.py start` captures the skill defaults and the project settings, source and file hash. On resumption use that snapshot. `route --run <run.json> --input <request.json>` resolves a role using the saved settings. Older runs retain the defaults from their generation for any omitted roles. For standalone design work, read the project file once when present. For several repositories, use the designated delivery project or explicit policy.

## Assign and verify work

Delegate bounded independent work when permitted and useful. Give each worker its role, lead, source snapshots, question, destination and expected evidence. Assigned workers return to the same lead. The lead integrates and verifies their work. If a preference is unavailable, use the available capable agent and disclose a material limitation once.

Keep model diagnostics in the review or validation record. Record an explicit user preference with its source in `user_override`. Distinguish requested settings from observed runtime configuration. `check --require-complete` audits review evidence. Add `--require-diagnostics` when model and timing observations are also required.

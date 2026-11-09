# Review discussions and dependency preparation

## Existing discussions

Read review threads, submitted review bodies and relevant PR comments through the
host's available read APIs. Include replies and resolved/outdated threads that
bear on current behavior. Check pagination for each collection; an empty first
page or a summary alone does not establish that all discussions were read.
Record collection scope, retrieval time, pagination completion, access failures
and unread material. Local-only comparisons can record “not applicable” with a
reason. No publication request is needed to read existing discussions.

For an explicitly blind pass or fresh challenge, save the initial findings and
exposure record before providing prior findings. Then reconcile relevant threads
against the reviewed head: still valid, fixed with evidence, duplicate of a current
finding, rejected with a trace, or unresolved. Do not count an existing report as
an independently discovered finding. A request to keep a benchmark blind throughout
takes precedence: defer reconciliation and disclose that limit.

An author response may clarify intent, but distinguish an accepted decision from
a proposal or an unsupported claim. Read relevant linked decision sources when
needed. A resolved thread is not proof of a fix. Conversely, a stale comment may
describe code that is absent at this head. Keep this assessment separate from
authority to post, resolve, approve or request changes.

## Runtime alignment before installation

Select the relevant runtime lane from the reviewed revision: explicit version pins,
manifest constraints, package-manager declaration, CI matrix and container stage.
Do not assume the host's newer runtime is compatible. When these disagree, record
which lane supports the behavior being checked and why; use separate environments
only for materially relevant lanes. No universal pin/CI/container precedence is
assumed. An unavailable supported runtime is a limitation, not a reason to silently
change the project's requirement.

Prefer an existing verified compatible runtime or an installed version manager.
If preparation is necessary and permitted, use a task-local environment/container
or official artifact with verified integrity; keep global defaults unchanged.
Probe the selected executable before dependency installation:

```bash
python <skill-dir>/scripts/review_environment.py --executable <absolute-runtime-path> --requirement 'Project runtime constraint' --requirement-source '<head>:<config-path>:<locator>' --expected '<exact selected version output>' --output <run>/runtime-probe.json
```

This compares observed version output to the selected exact version; it does not
solve version constraints or download anything. Preserve a mismatched probe and
correct the selection before installation. The lead must justify that the selected
version satisfies the project's requirement. Set the task-local PATH or explicit
invocation so the package manager, install scripts, test runner and children use
this same runtime; record the effective versions in the smoke-check evidence.
A version probe alone does not establish dependency/native compatibility.

Checkpoint an `environments` decision using the [canonical fields](checkpoint-records.md).
A `ready` environment requires the matching probe and dependency/smoke evidence.
If matching preparation is unavailable, record `limited`, the reason and exactly
which conclusions the alternative can support. A justified `source_only` review
needs no runtime installation. Neither state pretends execution occurred under the
project runtime. Inform workers of the selected executable, environment identity,
revision, output locations and limits before assigning suites.

On a runtime change, reassess the installation and native/build/cache products.
Reuse only verified compatible contents; rebuild/reinstall task-owned products
where required. Repeat affected checks when the earlier runtime weakens their
conclusion, not every unrelated source trace or test. Carry unchanged evidence
forward with its original runtime label. Record commands/check categories against
the environment actually used; a later version check cannot relabel earlier tests.

## Dependency preparation decision path

Use one setup owner and a task-owned environment; continue independent source
work during preparation. Choose the cheapest useful check at each step:

1. Inspect runtime/package-manager versions, platform/native requirements,
   reviewed manifests and lockfile. Identify the exact package/version/artifact
   and expected integrity. Inspect effective project/user/environment registry
   and proxy routing without printing tokens, credentials or complete secret-bearing
   configuration files. Record a sanitized registry host and configuration source.
2. Check for a compatible runtime and verified installed contents or content-addressed
   cache. Match the exact locked artifacts and integrity; version labels and matching
   lockfiles alone are insufficient. Use read-only reuse only when the tool permits
   it, otherwise copy/reflink verified artifacts to task-owned writable storage.
   Keep install metadata, build products and writable caches isolated.
3. Attempt the frozen/locked install when necessary. On a missing artifact, 401,
   403, 404, integrity or offline-cache failure, classify the specific failure
   before another full attempt. A 404 does not prove either package absence or
   authorization failure. Check expected package origin, scoped registry routing,
   permitted authentication availability and exact artifact availability.
4. Retry only after recording a changed condition or distinct hypothesis. If the
   identical locked public artifact is available from its authoritative registry,
   a task-local registry override/cache seed is acceptable after verifying locked
   integrity. Preserve package identity, version and lockfile; do not substitute
   a similarly named package, disable integrity, change global routing or send
   private package names/credentials to an unrelated public registry.
5. Run a small import/configuration or focused-test smoke check, then release the
   environment to assigned reviewers. Preserve failed attempts and the successful
   resolution, including artifact provenance and any unverified native contents.
   Stop repeating the same route without new evidence; report remaining access or
   reproducibility limits and continue useful source review.

Record an attempt ledger: timestamp, sanitized route/artifact, method/result,
elapsed interval if observed, changed evidence justifying the next attempt, and
smoke-check result. Setup time may overlap investigation; it is not automatically
critical-path delay. Never bundle credentials or entire dependency caches into the
review archive. This guidance does not authorize production access or execution
of uninspected install hooks.

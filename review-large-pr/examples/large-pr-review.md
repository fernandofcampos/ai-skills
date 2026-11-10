# Filled example: shared profile-cache refactor

This is a teaching report for the repository's `cross-boundary` evaluation fixture.
It illustrates the expected output; it is not a production PR review or an agent
benchmark result. Generate the fixture with `evaluations/workflow_eval.py prepare`
from the repository root. Its oracle records exact base/head commit IDs; an actual
run copies those identities into its canonical run.json.

## Scope and result

The comparison changes `cache.py`, `service.py`, and 40 client metadata files.
The lead traces unchanged `api.py` as a consumer. The fixture's accepted requirement
states that user IDs are unique only within a tenant and a response must belong to
the authenticated tenant. There are no external tickets, hosting metadata or PR
discussions in this fixture; production deployment is outside the evidence.

Investigation depth is deep because the cache identity crosses the authorization
boundary. The client-label edits are mechanical. The intended behavior is unchanged
tenant isolation after a shared-key refactor. The verdict is one blocking defect;
finding a defect does not itself leave the review unfinished.

## Investigation evidence

| Unit and exact mapping | Question | Evidence and conclusion |
| --- | --- | --- |
| R1: `cache.py`, `UserCache.key/get/evict` | Does identity retain tenant ownership? | Base returns `(tenant, user_id)`; head returns `user_id`. Both retrieval and eviction use that identity. |
| R2: `service.py`, `profile`; unchanged `api.py`, `get_profile` | Can distinct authenticated tenants reach the same entry? | The API passes the authenticated tenant and normalized user ID. The service passes both to the cache, whose key discards tenant. The path is reachable without a forged claim. |
| R3: `clients/client-00.json` through `client-39.json`, each `schema_label` | Do client-label changes affect runtime behavior? | Each value changes from v1 to v2; the fixture's runtime files do not read these manifests. Each inventory path maps to this exact mechanical transformation. |

**Primary hypothesis B1:** tenant B can receive tenant A's cached profile for the
same user ID. Trace `get_profile → profile → UserCache.get → key` with a shared
cache and two database rows. A cold lookup for B alone loads B's row; an A lookup
followed by B reuses A's entry. This distinguishes key aliasing from a loader error.

**Challenge:** examine the reverse ordering and the supposed guard that the API
already validates tenant. The caller does provide the correct tenant, but the
cache drops it. A reverse-order trace returns B's row to A, so the result is not
specific to one fixture value. This example describes a separate lead pass, not
independent review by another agent. Retain actual traces/probe results in a real run.

## Finding

**P1 — Preserve tenant in the cache identity.** `UserCache.key` replaces the base
tuple with `user_id`. When two tenants share an ID and one warms the cache, the
other receives the first tenant's profile through the ordinary authenticated API
path. Keep tenant in the key and cover alternating lookups and eviction across
tenants. The requirement and base behavior both establish this as an introduced
isolation defect.

## Validation and limits

The reasoning above is source evidence. The evaluation harness tests the fixture
defect and fix, but those helper-test results are not an agent review result or
production validation. A real report separately identifies executed regression
suites, integration checks and new probes, with commands and retained results.
Model settings and timing are omitted; they do not establish review completeness.

# Filled example: verify the tenant-key fix

This teaching continuation uses the `follow-up` evaluation fixture and the
[prior review](large-pr-review.md). Generated oracle snapshots identify the original
base, previous head and fixed head; an actual run preserves those exact identities
and the prior verdict before carrying evidence into a new inventory.

## Reassessment

The only delta from the reviewed head is `UserCache.key`, restored to
`(tenant, user_id)`. The tenant-isolation requirement is unchanged. There is no
new architecture or external decision evidence in this fixture.

Reopen R1 and the R2 integration scenario because both rely on cache identity.
Inspect `get` and `evict` using the restored key, and follow the API/service path
to verify that the correct tenant still reaches it. Alternate lookups for tenants
A and B sharing user 7; their entries are now separate. Evicting A leaves B's entry
intact. A cold lookup remains the positive control.

Retain R3's per-file mechanical conclusions with their original snapshot: the 40
client labels remain unrelated to runtime identity, their transformation is unchanged,
and the key fix introduces no reader or dependency on them. This is an applicability
reason in addition to unchanged bytes. No other source or criteria changes are present.

## Result

The tenant-key finding is fixed at the new snapshot. The focused source traces
resolve the previously failing path and its affected consumer. Do not republish
the stale finding, create a new design, or rerun the whole review solely to obtain
another clean verdict. Retain the earlier investigation and challenge, explaining
how the corrected key changes their outcome. Actual new experiment results, if
executed, belong beside these source conclusions and must be reported separately.

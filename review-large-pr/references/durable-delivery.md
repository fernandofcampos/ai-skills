# Durable review delivery

For completed reviews, prefer `review_run.py finish <run>/run.json` from the
[quickstart](quickstart.md). It validates required review records, selects linked
evidence and checks the archive. The lower-level commands below support partial
reviews and custom packaging; clearly state substantive gaps in the report.

Choose a task-owned persistent folder outside tracked source, for example
`<task-workspace>/reviews/<repo>-pr-<number>/<head-prefix>/`. Use a new run folder
on repeated reviews. Keep working evidence there from the start when convenient,
or stage a selected set from temporary execution storage before final delivery.
Honor a user-specified destination. A system temporary folder is not delivery.
When using the archive helper, plan sibling evidence and archive directories,
for example `<run>/working/` and `<run>/archive/`. The archive destination must
be new and outside the evidence root passed as `--root`; placing it inside that
root is rejected. A task-scoped parent can contain both siblings.

Preserve the final narrative, exact run/coverage manifests, requirements and
discussion dispositions, useful investigation handoffs, small test result/log
summaries, independent probes/patches and instructions needed to reproduce them.
Keep failed attempts that explain limitations. Select necessary artifacts; do not
copy dependency trees, caches, credentials or whole tool transcripts. Sanitize
logs before inclusion. Retain versions and hashes of original records, including
exact source identities; rewriting a local link must not relabel a source revision.

For schema-2 runs, coverage is embedded in `run.json`; imported seed inventories
are optional history. For schema 1, include each referenced coverage file. The
archive helper provides original byte copies
and a portable evidence view:

```bash
python <skill-dir>/scripts/review_archive.py create --root <scratch> --output <durable-new-folder> --run run.json --report review-record.md --include batches/B1.md --include checks/results.json --include probes/contract-test.py
python <skill-dir>/scripts/review_archive.py check <durable-new-folder>
```

Use explicit files relative to one evidence root, repeating `--include` as needed.
Stop evidence writers before packaging. Legacy referenced coverage and structured evidence
must be selected; stage out-of-root evidence under this root first, preserving
original identity/hash. The helper rejects overwrite, symlinks, path traversal,
common credential/cache filenames and output under system temporary storage.
It preserves original bytes in `originals/`, rewrites local evidence pointers in
`files/`, and records both SHA-256 values and source snapshots in `archive.json`.
Link the final response to `files/review-record.md`.

JSON evidence selected with `--include` stays byte-for-byte unchanged, including
malformed inputs and byte-sensitive fixtures. Only identified review records have
structured paths rewritten: the canonical `--run`, its referenced legacy coverage,
and selected repair/promotion backups are identified automatically. Use repeatable
`--json-record <relative-path>` for other JSON review records, such as checkpoint
inputs, structured handoffs or an unreferenced earlier manifest; this also selects
the file. Coverage files referenced by those records must be included and are
identified automatically. Do not use `--json-record` for test fixtures or other
opaque payloads, even when their fields resemble review records. Declared records
must parse as JSON and all their evidence targets must be selected.

New archives use schema version 2 and retain this record inventory in
`json_records`, so checking after relocation uses the same interpretation. The
checker still accepts existing schema-1 archives under their original JSON and
Markdown normalization rules; it does not rewrite previously delivered archives.

Canonical receipts already preserve checkpoint changes, so raw checkpoint input
files are optional. Select them with `--json-record requests/pass.json` when needed.
Their evidence paths resolve from the canonical
`--run` directory, even if the inputs live in `requests/`; portable copies retain
that convention. Include only inputs for that selected run. Package another run's
inputs with its own canonical record rather than silently mixing reference bases.

After an explicit `repair-evidence`, select the replacement and saved prior manifest.
The portable view applies recorded relocation aliases to current and historical
pointers; `originals/` retains the exact old receipts, paths and hashes. A missing
pointer is not repaired by silently editing history or relaxing normal validation.
Before writing an archive, the helper rejects an old alias pathname whose existing
bytes differ from its retained digest, and verifies the captured bytes of the
resolved replacement against that digest, including chained moves. Failure leaves
the source records and any existing archives unchanged.

Keep a preserved earlier manifest in its original relative-reference context
(for example, `run-before-correction.json` beside `run.json`). Moving it into a
new subdirectory silently changes what its relative evidence paths resolve to.
If restructuring is necessary, retain the byte-identical original and make an
explicitly identified portable copy; do not rewrite history to pass packaging.

Run the coverage/run checks against the working records before archiving. The
archive check works after relocation or scratch deletion; it verifies hashes,
snapshot consistency and portable structured/single-line inline Markdown links,
including optional double-quoted, single-quoted or parenthesized titles. Local
`sandbox:/absolute/path` evidence links under the selected root become portable
relative links; stage out-of-root sandbox evidence first. These are local paths,
not URLs to fetch. The checker preserves titles, queries and fragments; it checks
file targets, not fragment validity. Rewritten URL paths percent-encode filename
characters such as `#`, `?`, `%` and `:`, keeping them separate from query and
fragment delimiters. Reference-style/HTML links, multiline links,
nested labels, escaped title delimiters, and bare destinations containing
parentheses require manual audit; use an angle-bracket destination for a path
containing spaces or parentheses.
It does not preserve or fetch Git source, certify findings, scan arbitrary content
for secrets, or guarantee filesystem retention. Source checkout and installed
skill paths remain provenance references. Explicitly identify unavailable external
source dependencies. Manually inspect reference-style Markdown, HTML links and
plain-text paths; convert evidence links to ordinary inline links when practical.
For manual schema-2 records, retain the same coverage/evidence semantics and
recording limitation; archive validation does not imply helper checkpoints ran.
Unsupported comparisons retain equivalent explicit records with validation limits.
Report review completeness, record validation and archive integrity separately;
packaging failure cannot erase real evidence or repair stale review dispositions.

When collecting optional lifecycle diagnostics, record `delivery_ready` after consolidation and successful required checks, before packaging; this is
readiness to hand off the result, not the final user-visible delivery timestamp.
If later checks reopen work, preserve and qualify the earlier checkpoint and
record corrected readiness in a timing supplement; do not report it as final.
If a host exposes actual delivery time later, save a separate timing supplement
or a new archive version. Do not mutate an already delivered archive's contents
or fabricate a final timestamp to make its end-to-end metric look complete.

# Supported paired installation

Install or stage the complete directories as siblings under one skill root:

```text
<skill-root>/
  document-feature-design/
    SKILL.md
    references/model-policy.md
    references/review-handoff.md
    references/paired-installation.md
    assets/...
    scripts/...
  review-large-pr/
    SKILL.md
    references/...
    assets/...
    scripts/...
```

The design skill owns the single shared model policy and handoff contract. The
review skill resolves them relative to its own directory, regardless of the
current working directory. Copying only SKILL.md or installing review-large-pr
alone is not the supported arrangement. Do not silently select an unrelated
installed companion to fill a missing staged dependency.

Check a staged pair before adoption:

```bash
python <skill-root>/review-large-pr/scripts/review_run.py check-installation --skill-root <skill-root>/review-large-pr
```

This checks the companion, policy and linked local resources, not dependency
installation, model execution or semantic compatibility. Run both skills' suites
and validate an authored document with the design validator's declared dependencies.

For maintenance during active work, stage a complete pair in a separate directory,
capture original hashes, and deliver the patch and validation there. Keep the pair
used by the active assignment unchanged. Subsequent adoption replaces both complete
directories together after those users finish; this guidance does not authorize
installation. Retain the old pair for rollback and preserve fingerprints in prior
review records. Fresh runs capture the newly adopted versions.

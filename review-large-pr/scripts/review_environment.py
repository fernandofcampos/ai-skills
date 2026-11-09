#!/usr/bin/env python3
"""Probe an explicitly selected runtime before installs; never install or fetch.

The lead selects the expected exact version from the project's supported runtime
and available installation. Equality checks do not interpret arbitrary version
ranges, qualify production/native behavior or certify dependency contents.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from review_coverage import CoverageError, evidence_list


def inspect_probe(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise CoverageError('Expected runtime probe schema 1.')
    for field in ('executable', 'requirement', 'requirement_source', 'expected', 'observed', 'checked_at'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise CoverageError(f'Runtime probe requires {field}.')
    if type(data.get('returncode')) is not int:
        raise CoverageError('Runtime probe requires a returncode.')
    aligned = data['returncode'] == 0 and data['observed'] == data['expected']
    if data.get('alignment') != ('matched' if aligned else 'mismatched'):
        raise CoverageError('Runtime probe alignment disagrees with observed version/exit.')
    return aligned


def inspect_environments(rows, root):
    if not isinstance(rows, list):
        raise CoverageError('environments must be an array.')
    pending, warnings, seen = [], [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'].strip() or row['id'] in seen:
            raise CoverageError('Environment requires a unique nonempty id.')
        seen.add(row['id'])
        status = row.get('status')
        if status not in {'planned', 'ready', 'limited', 'source_only'}:
            raise CoverageError('Environment status must be planned, ready, limited or source_only.')
        for field in ('purpose', 'reason'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise CoverageError(f'Environment requires {field}.')
        evidence_list(row.get('evidence'), 'environment.evidence', root)
        runtime = row.get('runtime')
        aligned = False
        if runtime is not None:
            if not isinstance(runtime, dict):
                raise CoverageError('Runtime must be a structured evidence pointer or null.')
            evidence_list([runtime], 'environment.runtime', root)
            aligned = inspect_probe(json.loads((root / runtime['path']).read_text()))
        if status == 'ready':
            if not aligned:
                raise CoverageError('Ready environment requires a matched runtime probe; qualify unavailable/mismatched execution as limited.')
            if not row['evidence']:
                raise CoverageError('Ready environment needs dependency provenance and smoke-check evidence.')
        elif status == 'planned':
            pending.append(f'environment not prepared: {row["id"]}')
        elif status == 'limited':
            warnings.append(f'Limited environment {row["id"]}: {row["reason"]}; no runtime-equivalence claim.')
    return pending, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', required=True, help='Inspected absolute path to the selected runtime.')
    parser.add_argument('--version-arg', default='--version')
    parser.add_argument('--requirement', required=True, help='Project runtime requirement, not host default.')
    parser.add_argument('--requirement-source', required=True, help='Reviewed revision and precise config/CI/container locator.')
    parser.add_argument('--expected', required=True, help='Exact expected version output selected within that requirement.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        path = Path(args.executable)
        if not path.is_absolute() or not path.is_file():
            raise CoverageError('Runtime executable must be an existing absolute file path.')
        if Path(args.output).exists():
            raise CoverageError('Preserve earlier probes; choose a new output path.')
        result = subprocess.run([str(path), args.version_arg], capture_output=True, text=True, timeout=20, check=False)
        output = (result.stdout.strip() or result.stderr.strip())[:4096] or '(empty output)'
        data = dict(schema_version=1, executable=str(path), requirement=args.requirement,
                    requirement_source=args.requirement_source, expected=args.expected,
                    observed=output, returncode=result.returncode,
                    checked_at=datetime.now(timezone.utc).isoformat(),
                    alignment='matched' if result.returncode == 0 and output == args.expected else 'mismatched')
        inspect_probe(data)
        with Path(args.output).open('x') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
        print(f'Runtime {data["alignment"]}; saved {args.output}. Dependency and smoke checks remain separate.')
        return 0 if data['alignment'] == 'matched' else 2
    except (CoverageError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

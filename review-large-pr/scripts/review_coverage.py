#!/usr/bin/env python3
"""Create, checkpoint and check revision-specific review coverage.

This verifies inventory and evidence-field structure, not the quality of a review.
It does not fetch refs, inspect a hosting service, or modify the Git checkout.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


class CoverageError(Exception):
    pass


def git(repo, *args):
    result = subprocess.run(
        ['git', '-C', str(repo), *args], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        detail = result.stderr.decode('utf-8', 'replace').strip()
        raise CoverageError(f'Git failed: {detail}')
    if result.stderr:
        print(result.stderr.decode('utf-8', 'replace').strip(), file=sys.stderr)
    return result.stdout


def snapshot(repo, base, head):
    root = git(repo, 'rev-parse', '--show-toplevel').decode('utf-8', 'surrogateescape').removesuffix('\n')
    root = str(Path(root).resolve())
    def commit(ref):
        return git(root, 'rev-parse', '--verify', '--end-of-options',
                   ref + '^{commit}').decode().strip()
    base_id, head_id = commit(base), commit(head)
    common = git(root, 'merge-base', '--all', base_id, head_id).decode().split()
    if len(common) != 1:
        raise CoverageError('A unique merge base is required; use an explicit external record for this comparison.')
    info = {'repo_root': root, 'target_base': base_id,
            'comparison_base': common[0], 'head': head_id}
    raw = git(root, 'diff', '--name-status', '-z', '--no-ext-diff',
              '--no-textconv', '--ignore-submodules=none', '--find-renames=50%',
              '-l1000', common[0], head_id, '--')
    parts = raw.split(b'\0')
    if parts[-1] != b'':
        raise CoverageError('Incomplete Git path inventory.')
    parts.pop()
    inventory = []
    index = 0
    while index < len(parts):
        change = parts[index].decode('ascii')
        index += 1
        old_path = None
        if change.startswith(('R', 'C')):
            old_path = parts[index].decode('utf-8', 'surrogateescape')
            index += 1
        path = parts[index].decode('utf-8', 'surrogateescape')
        index += 1
        inventory.append({'path': path, 'old_path': old_path, 'change': change})
    return info, inventory


def write_initial(args):
    info, inventory = snapshot(args.repo, args.base, args.head)
    record = {
        'schema_version': 1,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'snapshot': info,
        'files': [dict(item, units=[], status='unreviewed', evidence=[], notes='')
                  for item in inventory],
        'integration': {'status': 'unreviewed', 'evidence': [], 'notes': ''},
    }
    # Exclusive creation preserves earlier reviews; never overwrite on a refresh.
    with Path(args.output).open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2, ensure_ascii=True)
        stream.write('\n')
    print(f'Created {args.output}: {len(inventory)} change entries, all unreviewed; rename entries include both paths.')
    print('Committed comparison only; working-tree changes and remote freshness are not checked.')


def string_list(value, field):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise CoverageError(f'{field} must be a list of nonempty strings.')
    return value


def evidence_list(value, field, record_dir):
    if not isinstance(value, list):
        raise CoverageError(f'{field} must be a list of evidence entries.')
    for entry in value:
        # Preserve existing v1 free-text records; new local evidence can be precise.
        if isinstance(entry, str):
            if not entry.strip():
                raise CoverageError(f'{field} must contain nonempty strings or evidence objects.')
            continue
        if not isinstance(entry, dict) or set(entry) != {'path', 'locator', 'claim'}:
            raise CoverageError(f'{field}: evidence objects require path, locator and claim only.')
        if any(not isinstance(v, str) or not v.strip() for v in entry.values()):
            raise CoverageError(f'{field}: path, locator and claim must be nonempty strings.')
        path = Path(entry['path'])
        if not path.is_absolute():
            path = record_dir / path
        if not path.is_file():
            raise CoverageError(f'{field}: evidence file does not exist: {entry["path"]!r}')
    return value


def review_fields(item, label, record_dir, integration=False):
    if not isinstance(item, dict):
        raise CoverageError(f'{label} must be an object.')
    allowed = {'unreviewed', 'partial', 'reviewed'}
    allowed.add('not_applicable' if integration else 'excluded')
    status = item.get('status')
    if not isinstance(status, str) or status not in allowed:
        raise CoverageError(f'{label}: invalid review status.')
    evidence = evidence_list(item.get('evidence'), f'{label}.evidence', record_dir)
    notes = item.get('notes')
    if not isinstance(notes, str):
        raise CoverageError(f'{label}.notes must be a string.')
    if status == 'reviewed' and not evidence:
        raise CoverageError(f'{label}: reviewed requires evidence.')
    if status in {'excluded', 'not_applicable'} and not notes.strip():
        raise CoverageError(f'{label}: {status} requires a rationale in notes.')
    if not integration:
        units = string_list(item.get('units'), f'{label}.units')
        if status in {'partial', 'reviewed'} and not units:
            raise CoverageError(f'{label}: {status} requires unit IDs.')
    return status


def load_record(args):
    with Path(args.record).open(encoding='utf-8') as stream:
        return json.load(stream)


def validate_record(record, args):
    if not isinstance(record, dict) or type(record.get('schema_version')) is not int or record['schema_version'] != 1:
        raise CoverageError('Expected a review coverage object with schema_version 1.')
    info, inventory = snapshot(args.repo, args.base, args.head)
    if record.get('snapshot') != info:
        raise CoverageError('Snapshot mismatch: repository, target base, comparison base, or head changed. Create a fresh record and reassess affected evidence.')
    rows = record.get('files')
    if not isinstance(rows, list):
        raise CoverageError('files must be an array.')
    expected = {item['path']: item for item in inventory}
    seen = set()
    counts = Counter()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str):
            raise CoverageError('Each file must be an object with a path string.')
        path = row['path']
        if path in seen:
            raise CoverageError(f'Duplicate coverage path: {path!r}')
        seen.add(path)
        if path not in expected:
            raise CoverageError(f'Unexpected coverage path: {path!r}')
        actual = {key: row.get(key) for key in ('path', 'old_path', 'change')}
        if actual != expected[path]:
            raise CoverageError(f'Changed-file metadata mismatch: {path!r}')
        counts[review_fields(row, repr(path), Path(args.record).resolve().parent)] += 1
    missing = set(expected) - seen
    if missing:
        raise CoverageError(f'Missing coverage paths: {sorted(missing)!r}')
    integration = review_fields(record.get('integration'), 'integration',
                                Path(args.record).resolve().parent, integration=True)
    complete = (counts['reviewed'] == len(inventory)
                and integration in {'reviewed', 'not_applicable'})
    return counts, integration, complete, len(inventory)


def check_record(args):
    record = load_record(args)
    counts, integration, complete, size = validate_record(record, args)
    summary = ', '.join(f'{state}={counts[state]}' for state in
                        ('reviewed', 'partial', 'unreviewed', 'excluded'))
    print(f'Inventory verified: {size} change entries; {summary}; integration={integration}.')
    if args.audit_evidence:
        for warning in audit_evidence(record):
            print(f'WARNING: {warning}')
    if args.require_complete and not complete:
        raise CoverageError('Coverage incomplete; full coverage requires all files reviewed and integration assessed.')
    state = 'complete' if complete else 'incomplete'
    print(f'PASS: structural checks; coverage {state}. Evidence quality, correctness, and remote freshness require separate verification.')


def audit_evidence(record):
    """Heuristic warnings, never a semantic verdict or a reason to reject a group."""
    claims = {}
    legacy = []
    for row in record['files']:
        if row['status'] != 'reviewed':
            continue
        objects = [e for e in row['evidence'] if isinstance(e, dict)]
        if not objects:
            legacy.append(row['path'])
            continue
        # Common supplementary citations are fine: inspect the primary claim only.
        claim = ' '.join(objects[0]['claim'].split()).casefold()
        claims.setdefault(claim, []).append(row['path'])
    warnings = []
    for paths in claims.values():
        if len(paths) >= 3:
            warnings.append(f'Identical primary claim across {len(paths)} paths '
                            f'(examples: {paths[:3]!r}). Verify an explicit file-to-symbol/behavior '
                            'mapping in the cited group; repetition alone does not prove a gap.')
    if legacy:
        warnings.append(f'{len(legacy)} reviewed paths have only free-text evidence. '
                        'Manually verify precise locators and conclusions; legacy records remain supported.')
    return warnings


def atomic_save(record, path):
    """Replace a validated record without exposing a partially written JSON file."""
    path = Path(path).resolve()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream, indent=2, ensure_ascii=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def record_batch(args):
    """One bounded pass, with distinct dispositions; never broadcast one verdict."""
    record = load_record(args)
    validate_record(record, args)
    changes = json.loads(Path(args.input).read_text(encoding='utf-8'))
    if not isinstance(changes, dict) or not changes or set(changes) - {'files', 'integration'}:
        raise CoverageError('Batch requires files and/or integration only.')
    apply_batch(record, changes)
    validate_record(record, args)
    atomic_save(record, args.record)
    print(f'Recorded bounded batch: {len(changes.get("files", []))} files; integration={"integration" in changes}. '
          'Snapshot and other dispositions preserved; evidence meaning remains a lead judgment.')


def apply_batch(record, changes):
    """Apply only review fields in memory; caller validates before committing."""
    if not isinstance(changes, dict) or not changes or set(changes) - {'files', 'integration'}:
        raise CoverageError('Batch requires files and/or integration only.')
    rows = changes.get('files', [])
    if not isinstance(rows, list) or (not rows and 'integration' not in changes):
        raise CoverageError('Batch must contain at least one disposition.')
    targets = {row['path']: row for row in record['files']}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'path', 'units', 'status', 'evidence', 'notes'}:
            raise CoverageError('Batch file entries require path, units, status, evidence and notes only.')
        path = row['path']
        if not isinstance(path, str) or path not in targets or path in seen:
            raise CoverageError('Batch path is absent or duplicated.')
        seen.add(path)
        targets[path].update({k: v for k, v in row.items() if k != 'path'})
    if 'integration' in changes:
        row = changes['integration']
        if not isinstance(row, dict) or set(row) != {'status', 'evidence', 'notes'}:
            raise CoverageError('Batch integration requires status, evidence and notes only.')
        record['integration'].update(row)


def record_checkpoint(args):
    """Replace one disposition, validating the entire result before atomic replacement."""
    record = load_record(args)
    if args.integration:
        if args.unit:
            raise CoverageError('Integration checkpoints do not take unit IDs; name them in evidence.')
        target = record.get('integration') if isinstance(record, dict) else None
    else:
        rows = record.get('files', []) if isinstance(record, dict) else []
        if not isinstance(rows, list):
            raise CoverageError('files must be an array.')
        target = next((row for row in rows if isinstance(row, dict)
                       and row.get('path') == args.path), None)
    if not isinstance(target, dict):
        raise CoverageError('Checkpoint target is absent from the inventory.')
    if any(v is not None for v in (args.evidence_file, args.locator, args.claim)):
        if not all(v is not None and v.strip() for v in
                   (args.evidence_file, args.locator, args.claim)):
            raise CoverageError('Supply --evidence-file, --locator and --claim together.')
    evidence = list(args.evidence)
    if args.evidence_file is not None:
        evidence.append({'path': args.evidence_file, 'locator': args.locator, 'claim': args.claim})
    target.update(status=args.status, evidence=evidence, notes=args.notes)
    if not args.integration:
        target['units'] = args.unit
    # Verify supplied refs, immutable inventory and every evidence entry. No write on failure.
    validate_record(record, args)
    atomic_save(record, args.record)
    label = 'integration' if args.integration else repr(args.path)
    print(f'Recorded {label}: {args.status}. Snapshot and other dispositions preserved.')
    print('Checkpoint records the lead assessment; it does not establish evidence quality or requirements coverage.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Create an unreviewed inventory; refuse overwrite.')
    init.add_argument('--output', required=True, help='New JSON path in an existing scratch directory.')
    check = commands.add_parser('check', help='Validate snapshot, full inventory, and evidence fields.')
    check.add_argument('record')
    check.add_argument('--require-complete', action='store_true')
    check.add_argument('--audit-evidence', action='store_true',
                       help='Warn about repeated primary claims and legacy-only evidence; never certify meaning.')
    batch = commands.add_parser('record-batch', help='Atomically checkpoint one bounded pass with distinct file evidence.')
    batch.add_argument('record')
    batch.add_argument('--input', required=True, help='JSON with files and/or integration dispositions.')
    update = commands.add_parser('record', help='Atomically replace one file/integration review disposition.')
    update.add_argument('record')
    selector = update.add_mutually_exclusive_group(required=True)
    selector.add_argument('--path', help='Exact changed path from the inventory, including deletions.')
    selector.add_argument('--integration', action='store_true')
    update.add_argument('--status', required=True,
                        choices=['unreviewed', 'partial', 'reviewed', 'excluded', 'not_applicable'])
    update.add_argument('--unit', action='append', default=[], help='Repeat for multiple file unit IDs.')
    update.add_argument('--evidence', action='append', default=[], help='Additional free-text evidence; repeatable.')
    update.add_argument('--evidence-file', help='Local evidence path, relative to the coverage record or absolute.')
    update.add_argument('--locator', help='Symbol, scenario, section, test name or line location in that evidence.')
    update.add_argument('--claim', help='Concise conclusion supported by the cited evidence.')
    update.add_argument('--notes', default='')
    for command in (init, check, update, batch):
        command.add_argument('--repo', required=True)
        command.add_argument('--base', required=True, help='Target branch/ref or exact commit; records its merge base with head.')
        command.add_argument('--head', required=True, help='Head branch/ref or exact commit.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            write_initial(args)
        elif args.command == 'record':
            record_checkpoint(args)
        elif args.command == 'record-batch':
            record_batch(args)
        else:
            check_record(args)
    except (CoverageError, OSError, ValueError, IndexError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

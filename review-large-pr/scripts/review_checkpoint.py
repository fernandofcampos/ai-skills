"""Atomic schema-2 checkpoints; invoked through review_run.py.

One lead owns the canonical file. Embedded coverage removes multi-file commit
windows. Request IDs make retries idempotent; revisions reject stale handoffs.
No source edits, dependency installation, model selection or network access.
"""
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile

from review_coverage import CoverageError, apply_batch, atomic_save
from review_timing import observation, timestamp


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def absolute_evidence(data, root):
    """Rebase structured evidence when embedding a formerly separate inventory."""
    if isinstance(data, dict):
        if set(data) == {'path', 'locator', 'claim'}:
            data['path'] = str((root / data['path']).resolve())
        for value in data.values():
            absolute_evidence(value, root)
    elif isinstance(data, list):
        for value in data:
            absolute_evidence(value, root)


@contextmanager
def writer_lock(path):
    """OS-held lock releases on process death; the inert lock file may remain."""
    lock = Path(str(path) + '.lock')
    with lock.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            if stream.tell() == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise CoverageError('Another checkpoint writer is active.') from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CoverageError('Another checkpoint writer is active.') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def save_new(data, path):
    """Create without overwriting an existing run, including concurrent creation."""
    path = Path(path).resolve()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def begin(args):
    from review_run import fingerprints, now, nonempty
    intake = observation(args.intake_at, args.intake_unknown, args.intake_source)
    data = dict(schema_version=2, created_at=now(), revision=0, checkpoints=[],
                mode='unassessed', selection_reason='Awaiting bounded assessment',
                coverage=[], installed_skill_snapshot=fingerprints(args.skill_root),
                lead=None, depth=dict(level='unassessed', reason=''), boundaries=[],
                investigations=[], truncations=[], limitations=[], environments=[],
                recording=dict(method='helper', reason='Canonical atomic checkpoints'),
                timing=dict(milestones=[dict(name='intake', **intake)]), events=[])
    owner = nonempty(args.owner, 'owner')
    if args.role == 'lead':
        data['timing']['milestones'].append(dict(name='lead_start', **observation(
            args.lead_at, args.lead_unknown, args.lead_source)))
    elif args.lead_at or args.lead_unknown or args.lead_source:
        raise CoverageError('Lead-start options require --role lead; the assigned lead records its own start.')
    data['events'].append(dict(owner=owner, phase='intake' if args.role == 'coordinator' else 'review',
                               state='start', note='First observed review checkpoint; earlier work is not timed',
                               expect_seconds=None, **observation()))
    save_new(data, args.output)
    print('Created canonical schema-2 run. Pass this path to the lead; record scope, configuration and depth next.')


def promote(args):
    """Explicitly preserve v1, embed its coverage, and keep original timing/hashes."""
    from review_run import read, inspect_run
    source = Path(args.record).resolve()
    data = read(source)
    if data.get('schema_version') != 1:
        raise CoverageError('Promote requires a schema-1 source; never overwrite it.')
    if source == Path(args.output).resolve():
        raise CoverageError('Promote requires a new output path.')
    inspect_run(data, source)
    result = deepcopy(data)
    absolute_evidence(result, source.parent)
    embedded = []
    for index, ref in enumerate(data['coverage'], 1):
        path = (source.parent / ref['path']).resolve()
        record = read(path)
        absolute_evidence(record, path.parent)
        embedded.append(dict(id=f'repo-{index}', snapshot=ref['snapshot'], record=record))
    result.update(schema_version=2, revision=0, checkpoints=[], coverage=embedded,
                  environments=[], recording=dict(method='helper', reason='Promoted without changing prior evidence'),
                  previous_record=dict(path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    # Missing older lifecycle measurements remain missing, never synthesized.
    inspect_run(result, args.output)
    save_new(result, args.output)
    print('Promoted to one canonical file; old run/coverage files are preserved and no longer updated.')


def observe_input(row):
    if not isinstance(row, dict):
        raise CoverageError('Timing checkpoint must be an object.')
    unknown = row.get('unknown_time', False)
    if type(unknown) is not bool:
        raise CoverageError('unknown_time must be a boolean.')
    return observation(row.get('at'), unknown, row.get('source'))


def upsert(data, key, rows):
    from review_run import nonempty
    if not isinstance(rows, list):
        raise CoverageError(f'{key} must be an array.')
    existing = {row['id']: row for row in data[key]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise CoverageError(f'{key} entries must be objects.')
        ident = nonempty(row.get('id'), key + '.id')
        if ident in seen:
            raise CoverageError(f'Duplicate {key} update: {ident}')
        seen.add(ident)
        existing[ident] = row
    data[key] = list(existing.values())


def apply_checkpoint(data, request, path):
    from review_run import nonempty, read
    allowed = {'id', 'expected_revision', 'actor', 'note', 'assessment', 'coverage',
               'boundaries', 'investigations', 'truncations', 'environments',
               'events', 'milestones', 'recording', 'limitations'}
    if not isinstance(request, dict) or set(request) - allowed:
        raise CoverageError('Unknown checkpoint fields; source identities/history cannot be patched.')
    for field in ('id', 'actor', 'note'):
        nonempty(request.get(field), field)
    if type(request.get('expected_revision')) is not int or request['expected_revision'] != data['revision']:
        raise CoverageError('Stale checkpoint revision. Read current state and reconcile; do not overwrite newer work.')
    assessment = request.get('assessment', {})
    if not isinstance(assessment, dict) or set(assessment) - {'mode', 'selection_reason', 'lead', 'depth'}:
        raise CoverageError('Assessment accepts mode, selection_reason, lead and depth only.')
    data.update(assessment)
    root = Path(path).resolve().parent
    rows = request.get('coverage', [])
    if not isinstance(rows, list):
        raise CoverageError('coverage updates must be an array.')
    existing = {c['id']: c for c in data['coverage']}
    seen = set()
    for change in rows:
        if not isinstance(change, dict):
            raise CoverageError('coverage update must be an object.')
        ident = nonempty(change.get('id'), 'coverage.id')
        if ident in seen:
            raise CoverageError('Duplicate coverage update.')
        seen.add(ident)
        if 'import' in change:
            if set(change) - {'id', 'import', 'files', 'integration'} or ident in existing:
                raise CoverageError('Import requires a new coverage ID; snapshots cannot be replaced.')
            source = (root / nonempty(change['import'], 'coverage.import')).resolve()
            record = read(source)
            absolute_evidence(record, source.parent)
            batch = {k: change[k] for k in ('files', 'integration') if k in change}
            if batch:
                apply_batch(record, batch)
            existing[ident] = dict(id=ident, snapshot=deepcopy(record['snapshot']), record=record)
        else:
            if ident not in existing:
                raise CoverageError('Unknown coverage ID; first import its exact inventory.')
            apply_batch(existing[ident]['record'], {k: v for k, v in change.items() if k != 'id'})
    data['coverage'] = list(existing.values())
    for key in ('boundaries', 'investigations', 'truncations', 'environments'):
        if key in request:
            upsert(data, key, request[key])
    for key in ('recording',):
        if key in request:
            data[key] = request[key]
    if 'limitations' in request:
        from review_coverage import string_list
        data['limitations'].extend(string_list(request['limitations'], 'limitations'))
    events, milestones = request.get('events', []), request.get('milestones', [])
    if not isinstance(events, list) or not isinstance(milestones, list):
        raise CoverageError('events and milestones must be arrays.')
    for row in events:
        if not isinstance(row, dict) or set(row) - {'owner', 'phase', 'state', 'note', 'expect_seconds', 'at', 'unknown_time', 'source'}:
            raise CoverageError('Invalid event checkpoint fields.')
        data['events'].append(dict(owner=row.get('owner', request['actor']), phase=row.get('phase'),
            state=row.get('state'), note=row.get('note'), expect_seconds=row.get('expect_seconds'),
            **observe_input(row)))
    for row in milestones:
        if not isinstance(row, dict) or set(row) - {'name', 'at', 'unknown_time', 'source'}:
            raise CoverageError('Invalid lifecycle checkpoint fields.')
        if row.get('name') == 'delivered' and (not row.get('at') or not row.get('source')):
            raise CoverageError('Delivered requires a host-observed timestamp and source.')
        data.setdefault('timing', {'milestones': []})['milestones'].append(
            dict(name=row.get('name'), **observe_input(row)))
    data['revision'] += 1
    data['checkpoints'].append(dict(id=request['id'], request_sha256=digest(request),
        revision=data['revision'], recorded_at=observation()['recorded_at'],
        actor=request['actor'], note=request['note'], changes=deepcopy(request)))


def checkpoint(args):
    from review_run import inspect_run, read
    path = Path(args.record).resolve()
    request = read(args.input)
    if not isinstance(request, dict):
        raise CoverageError('Checkpoint input must be an object.')
    with writer_lock(path):
        original = read(path)
        if original.get('schema_version') != 2:
            raise CoverageError('Checkpoint requires schema 2; promote legacy records to a new path first.')
        # Validate existing state too; a later patch cannot silently repair altered identities.
        with redirect_stdout(io.StringIO()):
            inspect_run(original, path)
        for receipt in original['checkpoints']:
            if receipt['id'] == request.get('id'):
                if receipt['request_sha256'] != digest(request):
                    raise CoverageError('Checkpoint ID reused with different contents.')
                with redirect_stdout(io.StringIO()):
                    pending, warnings = inspect_run(original, path, args.require_complete)
                print('Checkpoint already committed; no duplicate timing or coverage writes.')
                print_status(pending, warnings)
                return
        updated = deepcopy(original)
        apply_checkpoint(updated, request, path)
        with redirect_stdout(io.StringIO()):
            pending, warnings = inspect_run(updated, path, args.require_complete)
        atomic_save(updated, path)
    print(f'Committed checkpoint {request["id"]} at revision {updated["revision"]}; coverage, investigations and timing saved together.')
    print_status(pending, warnings)


def print_status(pending, warnings):
    print('Current record: ' + ('pending: ' + '; '.join(pending) if pending else 'recorded obligations resolved') + '.')
    for warning in warnings:
        print('WARNING: ' + warning)


def repair_evidence(args):
    """Explicit same-content relocation; never relax normal checkpoint validation."""
    from review_run import inspect_run, nonempty, read
    path = Path(args.record).resolve()
    request = read(args.input)
    if not isinstance(request, dict) or set(request) != {'id', 'expected_revision', 'actor', 'note', 'relocations'}:
        raise CoverageError('Repair requires id, expected_revision, actor, note and relocations only.')
    for key in ('id', 'actor', 'note'):
        nonempty(request[key], key)
    rows = request['relocations']
    if not isinstance(rows, list) or not rows:
        raise CoverageError('Repair requires at least one explicit relocation.')
    with writer_lock(path):
        before = path.read_bytes()
        original = json.loads(before)
        if original.get('schema_version') != 2:
            raise CoverageError('Evidence repair requires a canonical schema-2 record.')
        for receipt in original['checkpoints']:
            if receipt['id'] == request['id']:
                if receipt['request_sha256'] != digest(request):
                    raise CoverageError('Checkpoint ID reused with different contents.')
                inspect_run(original, path)
                print('Evidence repair already committed; no history or pointer changes.')
                return
        if type(request['expected_revision']) is not int or request['expected_revision'] != original['revision']:
            raise CoverageError('Stale repair revision; reconcile current evidence first.')
        mapping, retained = {}, []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'from_path', 'to_path', 'sha256', 'identity_source'}:
                raise CoverageError('Relocation requires from_path, to_path, sha256 and identity_source only.')
            for key in row:
                nonempty(row[key], 'relocation.' + key)
            old = (path.parent / row['from_path']).resolve()
            new = (path.parent / row['to_path']).resolve()
            if old == new or str(old) in mapping:
                raise CoverageError('Relocations must name distinct, non-duplicate old/new paths.')
            expected = row['sha256']
            if (len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)
                    or not new.is_file() or hashlib.sha256(new.read_bytes()).hexdigest() != expected):
                raise CoverageError('Replacement evidence is missing or does not match the retained SHA-256.')
            if old.exists() and (not old.is_file() or hashlib.sha256(old.read_bytes()).hexdigest() != expected):
                raise CoverageError('Existing original evidence does not match the retained SHA-256.')
            mapping[str(old)] = str(new)
            retained.append(dict(row, from_path=str(old), to_path=str(new)))
        if set(mapping) & set(mapping.values()):
            raise CoverageError('Use final destinations; chained/cyclic relocations in one repair are invalid.')
        updated, used = deepcopy(original), set()
        def relocate(value):
            if isinstance(value, dict):
                if set(value) == {'path', 'locator', 'claim'}:
                    old = str((path.parent / value['path']).resolve())
                    if old in mapping:
                        value['path'] = mapping[old]
                        used.add(old)
                for key, child in value.items():
                    if key not in {'checkpoints', 'evidence_repairs', 'installed_skill_snapshot'}:
                        relocate(child)
            elif isinstance(value, list):
                for child in value:
                    relocate(child)
        relocate(updated)
        if used != set(mapping):
            raise CoverageError('Each relocation must repair an active structured evidence pointer.')
        # Verify all source identities, inventory and unrelated evidence normally.
        # Only the explicitly mapped file-existence failures can be repaired.
        with redirect_stdout(io.StringIO()):
            inspect_run(updated, path)
        envelope = {k: v for k, v in request.items() if k != 'relocations'}
        apply_checkpoint(updated, envelope, path)
        updated['checkpoints'][-1].update(request_sha256=digest(request), changes=deepcopy(request))
        backup = path.with_name(path.name + '.before-repair-' + digest(request)[:16] + '.json')
        updated.setdefault('evidence_repairs', []).append(dict(
            id=request['id'], relocations=retained, previous_record=str(backup),
            previous_sha256=hashlib.sha256(before).hexdigest()))
        from review_archive import relocation_aliases, relocated_path
        aliases = relocation_aliases(updated)
        for old in aliases:
            relocated_path(old, path, path.parent, aliases)
        with redirect_stdout(io.StringIO()):
            inspect_run(updated, path)
        if backup.exists():
            if backup.read_bytes() != before:
                raise CoverageError('Prior repair backup differs; preserve it and investigate.')
        else:
            with backup.open('xb') as stream:
                stream.write(before)
                stream.flush()
                os.fsync(stream.fileno())
        atomic_save(updated, path)
    print(f'Committed evidence repair {request["id"]}; preserved prior bytes at {backup}. '
          'Claims, locators, source identities and prior receipts are unchanged; identity authority requires human verification.')


def inspect_checkpoint_fields(data, root):
    from review_run import nonempty
    from review_environment import inspect_environments
    pending, warnings = inspect_environments(data.get('environments'), root)
    revision, receipts = data.get('revision'), data.get('checkpoints')
    if type(revision) is not int or revision < 0 or not isinstance(receipts, list):
        raise CoverageError('Schema 2 requires revision and checkpoints.')
    if len(receipts) != revision:
        raise CoverageError('Checkpoint revision/history mismatch.')
    ids = set()
    previous = timestamp(data['created_at'])
    for index, receipt in enumerate(receipts, 1):
        if not isinstance(receipt, dict) or receipt.get('revision') != index:
            raise CoverageError('Checkpoint history must retain committed revision order.')
        ident = nonempty(receipt.get('id'), 'checkpoint.id')
        if ident in ids:
            raise CoverageError('Duplicate checkpoint receipt.')
        ids.add(ident)
        for field in ('actor', 'note'):
            nonempty(receipt.get(field), 'checkpoint.' + field)
        value = receipt.get('request_sha256')
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise CoverageError('Invalid checkpoint request hash.')
        logged = timestamp(receipt.get('recorded_at'))
        if logged < previous:
            raise CoverageError('Checkpoint logging times must be chronological.')
        previous = logged
    recording = data.get('recording')
    if not isinstance(recording, dict) or recording.get('method') not in {'helper', 'manual'}:
        raise CoverageError('recording.method must be helper or manual.')
    nonempty(recording.get('reason'), 'recording.reason')
    if recording['method'] == 'manual':
        warnings.append('Manual fallback record: verify the stated limitation and exact evidence; no helper execution is implied.')
    points = {r['name'] for r in data.get('timing', {}).get('milestones', [])}
    for name in ('intake', 'lead_start', 'lead_complete'):
        if name not in points:
            pending.append(f'lifecycle endpoint missing: {name}; record evidence or explicitly unknown')
    if not data.get('environments'):
        pending.append('validation environment decision missing (execution or justified source-only)')
    return pending, warnings


def add_commands(sub):
    begin_parser = sub.add_parser('begin', help='Capture intake before discovery/delegation; create one canonical record.')
    begin_parser.add_argument('--output', required=True)
    begin_parser.add_argument('--owner', required=True)
    begin_parser.add_argument('--role', choices=['coordinator', 'lead'], required=True)
    begin_parser.add_argument('--skill-root', default=str(Path(__file__).resolve().parent.parent))
    time = begin_parser.add_mutually_exclusive_group()
    time.add_argument('--intake-at')
    time.add_argument('--intake-unknown', action='store_true')
    begin_parser.add_argument('--intake-source')
    lead_time = begin_parser.add_mutually_exclusive_group()
    lead_time.add_argument('--lead-at')
    lead_time.add_argument('--lead-unknown', action='store_true')
    begin_parser.add_argument('--lead-source')
    update = sub.add_parser('checkpoint', help='Atomically save a lead-verified pass and its lifecycle/phase observations.')
    update.add_argument('record')
    update.add_argument('--input', required=True)
    update.add_argument('--require-complete', action='store_true')
    convert = sub.add_parser('promote', help='Preserve a legacy run and embed coverage in a new schema-2 record.')
    convert.add_argument('record')
    convert.add_argument('--output', required=True)
    repair = sub.add_parser('repair-evidence', help='Relocate same-content evidence explicitly, preserving prior bytes/history.')
    repair.add_argument('record')
    repair.add_argument('--input', required=True)


def dispatch(args):
    {'begin': begin, 'checkpoint': checkpoint, 'promote': promote, 'repair-evidence': repair_evidence}[args.command](args)

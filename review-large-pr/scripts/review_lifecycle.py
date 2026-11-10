"""Task-oriented commands over the existing coverage, checkpoint and archive helpers."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path, PurePosixPath
import shutil
from urllib.parse import unquote, urlsplit
import uuid

from review_coverage import CoverageError, atomic_save, snapshot
from review_checkpoint import apply_checkpoint, save_new, writer_lock
from review_policy import load_policy


def start(args):
    from review_run import fingerprints, inspect_run, nonempty, now
    from review_timing import observation
    output = Path(args.output).resolve()
    if output.exists():
        raise CoverageError(f'Run folder already exists: {output}. Resume its run.json or choose a new --output.')
    snap, inventory = snapshot(args.repo, args.base, args.head)
    if output.is_relative_to(Path(snap['repo_root'])):
        raise CoverageError('Choose --output outside the source checkout to keep review artifacts separate.')
    policy = load_policy(snap['repo_root'], args.policy)
    created = now()
    coverage = dict(schema_version=1, created_at=created, snapshot=snap,
        files=[dict(row, units=[], status='unreviewed', evidence=[], notes='') for row in inventory],
        integration=dict(status='unreviewed', evidence=[], notes=''))
    data = dict(schema_version=2, created_at=created, revision=0, checkpoints=[],
        mode='full', selection_reason='Requested large or complex PR review; assessment pending',
        coverage=[dict(id='repo', snapshot=deepcopy(snap), record=coverage)],
        installed_skill_snapshot=fingerprints(args.skill_root), model_policy=policy,
        lead=dict(id=nonempty(args.owner, 'owner'), selection='current'),
        depth=dict(level='unassessed', reason=''), boundaries=[], investigations=[],
        truncations=[], limitations=[], environments=[], events=[], timing=dict(milestones=[]),
        recording=dict(method='helper', reason='Atomic start with pinned embedded inventory'))
    if args.diagnostics:
        data['timing']['milestones'] = [dict(name=name, **observation()) for name in ('intake', 'lead_start')]
        data['events'] = [dict(owner=args.owner, phase='review', state='start',
            note='Helper start observed; earlier work is not timed', expect_seconds=None, **observation())]
    template = Path(args.skill_root) / 'assets/review-record-template.md'
    report = template.read_text(encoding='utf-8')
    with redirect_stdout(io.StringIO()):
        inspect_run(data, output / 'run.json')
    output.mkdir(parents=True)
    try:
        save_new(data, output / 'run.json')
        (output / 'review-record.md').write_text(report, encoding='utf-8')
    except Exception:
        shutil.rmtree(output)
        raise
    print(f'Created {output / "run.json"}: {len(inventory)} changed paths, all unreviewed.')
    print('Next: assess depth and validation needs, fill review-record.md, then record verified evidence. '
          'Working-tree changes and remote PR freshness are not checked.')


def commit_update(path, changes, note, expected_revision=None):
    from review_run import inspect_run, read
    with writer_lock(path):
        original = read(path)
        if original.get('schema_version') != 2:
            raise CoverageError('Use promote to create a schema-2 run before assess or record.')
        with redirect_stdout(io.StringIO()):
            inspect_run(original, path)
        lead = original.get('lead') or {}
        if not lead.get('id'):
            raise CoverageError('Record the designated lead identity through checkpoint first.')
        request = dict(id='pass-' + uuid.uuid4().hex,
            expected_revision=original['revision'] if expected_revision is None else expected_revision,
            actor=lead['id'], note=note, **changes)
        updated = deepcopy(original)
        apply_checkpoint(updated, request, path)
        with redirect_stdout(io.StringIO()):
            inspect_run(updated, path)
        atomic_save(updated, path)
    print(f'Committed {request["id"]} at revision {updated["revision"]}.')


def assess(args):
    from review_run import nonempty, read
    environment = (dict(id='validation', status='source_only', purpose='Review validation',
                        reason=nonempty(args.source_only, 'source-only reason'), runtime=None, evidence=[])
                   if args.source_only is not None else read(args.environment))
    commit_update(Path(args.record).resolve(), dict(
        assessment=dict(mode='full', selection_reason=nonempty(args.reason, 'assessment reason'),
                        depth=dict(level=args.depth, reason=args.reason)),
        environments=[environment]), 'Assessed investigation depth and validation needs', args.expected_revision)


def record(args):
    from review_run import read
    path = Path(args.record).resolve()
    data = read(path)
    if data.get('schema_version') != 2:
        raise CoverageError('Use promote to create a schema-2 run before record.')
    ids = [row['id'] for row in data.get('coverage', [])]
    repo_id = args.repository_id or (ids[0] if len(ids) == 1 else None)
    if repo_id is None:
        raise CoverageError('Choose --repository-id for this multi-repository run.')
    evidence = []
    supplied = (args.evidence_file, args.locator, args.claim)
    if any(supplied):
        if not all(supplied):
            raise CoverageError('Supply --evidence-file, --locator and --claim together.')
        evidence.append(dict(path=args.evidence_file, locator=args.locator, claim=args.claim))
    row = dict(status=args.status, evidence=evidence, notes=args.notes)
    if args.integration:
        if args.unit:
            raise CoverageError('--unit belongs to a file disposition, not --integration.')
        update = dict(id=repo_id, integration=row)
    else:
        update = dict(id=repo_id, files=[dict(row, path=args.path, units=args.unit)])
    commit_update(path, dict(coverage=[update]), f'Verified disposition: {args.path or "integration"}',
                  args.expected_revision)


def collect_evidence(root, run, report, includes=(), json_records=()):
    """Follow declared evidence and supported links only; never glob the scratch tree."""
    from review_archive import (evidence_references, local_reference, markdown_links,
        relocated_path, relocation_aliases, relative_name, safe_file)
    run_data = json.loads(safe_file(root, run).read_bytes())
    aliases = relocation_aliases(run_data)
    selected, records, visited = set(), {run, *json_records}, set()
    queue = [run, report, *includes, *json_records]
    while queue:
        name = queue.pop()
        relative_name(name)
        signature = (name, name in records)
        if signature in visited:
            continue
        visited.add(signature)
        raw = safe_file(root, name).read_bytes()
        selected.add(name)
        owner = PurePosixPath(name)
        if name in records:
            data = json.loads(raw)
            if isinstance(data, dict) and {'id', 'expected_revision', 'actor', 'note'} <= data.keys():
                owner = PurePosixPath(run)
            for ref in evidence_references(data):
                queue.append(local_reference(ref['path'], owner, root, aliases))
            if isinstance(data, dict):
                known = [r['path'] for r in data.get('coverage', []) if 'path' in r and 'snapshot' in r]
                known.extend(r['previous_record'] for r in data.get('evidence_repairs', []))
                if isinstance(data.get('previous_record'), dict):
                    known.append(data['previous_record']['path'])
                for value in known:
                    target = local_reference(value, owner, root)
                    records.add(target)
                    queue.append(target)
        elif owner.suffix.lower() == '.md':
            def visit(match):
                url = urlsplit(match[2].removeprefix('<').removesuffix('>'))
                sandbox = url.scheme == 'sandbox'
                if (url.scheme and not sandbox) or url.netloc or not url.path:
                    return match[0]
                decoded = unquote(url.path)
                if (not sandbox and Path(decoded).is_absolute()
                        and not relocated_path(decoded, owner, root, aliases).is_relative_to(root)):
                    return match[0]
                queue.append(local_reference(decoded, owner, root, aliases))
                return match[0]
            markdown_links(raw.decode('utf-8'), visit)
    return selected, records


def finish(args):
    from review_archive import create, safe_file
    from review_run import inspect_run, read
    path = Path(args.record).resolve()
    root = path.parent
    output = Path(args.output).resolve() if args.output else root.with_name(root.name + '-archive')
    with writer_lock(path):
        # No automatic reviewed dispositions, depth decisions or completion timestamps.
        inspect_run(read(path), path, require_complete=True, require_diagnostics=args.require_diagnostics)
        report = safe_file(root, args.report).read_text(encoding='utf-8')
        if not report.strip() or '<!-- review-template: incomplete -->' in report:
            raise CoverageError('Fill review-record.md and remove its incomplete-template marker before finish.')
        selected, records = collect_evidence(root, path.name, args.report, args.include, args.json_record)
        output.parent.mkdir(parents=True, exist_ok=True)
        create(root, output, path.name, args.report, sorted(selected), sorted(records - {path.name}))
    print(f'Delivery report: {output / "files" / args.report}')
    print('Review records and archive verified. The lead still owns semantic conclusions and remote freshness.')


def add_commands(sub):
    command = sub.add_parser('start', help='Create a run folder, pinned inventory and report in one step.')
    for name in ('repo', 'base', 'head', 'output'):
        command.add_argument('--' + name, required=True)
    command.add_argument('--owner', default='lead')
    command.add_argument('--policy', help='Override the project-root .ai-skills.json preference file.')
    command.add_argument('--diagnostics', action='store_true', help='Opt in to phase/lifecycle timing.')
    command.add_argument('--skill-root', default=str(Path(__file__).resolve().parent.parent))
    command = sub.add_parser('assess', help='Record assessed depth and validation needs without a JSON envelope.')
    command.add_argument('record')
    command.add_argument('--depth', choices=['standard', 'deep'], required=True)
    command.add_argument('--reason', required=True)
    environment = command.add_mutually_exclusive_group(required=True)
    environment.add_argument('--source-only', help='Why source reasoning suffices for this change.')
    environment.add_argument('--environment', help='JSON environment entry for prepared or limited execution.')
    command.add_argument('--expected-revision', type=int)
    command = sub.add_parser('record', help='Save a precise file or integration disposition atomically.')
    command.add_argument('record')
    command.add_argument('--repository-id')
    target = command.add_mutually_exclusive_group(required=True)
    target.add_argument('--path')
    target.add_argument('--integration', action='store_true')
    command.add_argument('--status', choices=['unreviewed', 'partial', 'reviewed', 'excluded', 'not_applicable'], required=True)
    command.add_argument('--unit', action='append', default=[])
    for name in ('evidence-file', 'locator', 'claim'):
        command.add_argument('--' + name)
    command.add_argument('--notes', default='')
    command.add_argument('--expected-revision', type=int)
    command = sub.add_parser('finish', help='Check review completion, collect linked evidence and verify its archive.')
    command.add_argument('record')
    command.add_argument('--output', help='New durable archive folder; defaults to a sibling named <run-folder>-archive.')
    command.add_argument('--report', default='review-record.md')
    command.add_argument('--include', action='append', default=[])
    command.add_argument('--json-record', action='append', default=[])
    command.add_argument('--require-diagnostics', action='store_true')


def dispatch(args):
    try:
        {'start': start, 'assess': assess, 'record': record, 'finish': finish}[args.command](args)
    except CoverageError as exc:
        raise CoverageError(f'{exc}\nRecovery: inspect the named gap, use assess/record/checkpoint to save verified '
                            'work, then retry. Never mark missing evidence reviewed to pass finish. '
                            'Use a new output folder when preserving an existing run or archive.') from exc

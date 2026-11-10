#!/usr/bin/env python3
"""Record review provenance, progress and behavioral investigations locally.

Uses the standard library and Git. Does not choose review depth, start agents,
attest a backend model, certify reasoning, contact services or execute tests.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from review_coverage import CoverageError, atomic_save, audit_evidence, evidence_list, validate_record
from review_timing import MILESTONES, observation, timestamp, timing_summary, validate_observation
from review_policy import load_policy, preferred_configuration, preferences


def now():
    return datetime.now(timezone.utc).isoformat()


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise CoverageError(f'{label} must be a nonempty string.')
    return value


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def route(request, policy=None):
    """A routing recommendation from supplied configuration, never discovery."""
    if not isinstance(request, dict):
        raise CoverageError('Routing input must be an object.')
    agent = nonempty(request.get('agent'), 'agent')
    role = request.get('role', 'unassigned')
    if role not in {'unassigned', 'lead', 'reviewer', 'documentation-author'}:
        raise CoverageError('Unknown assignment role.')
    preferred_model, preferred_effort = preferred_configuration(request, policy)
    configured = (request.get('model') == preferred_model
                  and request.get('effort') == preferred_effort
                  and isinstance(request.get('configuration_source'), str)
                  and bool(request['configuration_source'].strip()))
    existing = request.get('existing_lead')
    if existing is not None:
        nonempty(existing, 'existing_lead')
    if role in {'reviewer', 'documentation-author'}:
        action, lead = 'retain_assignment', existing
    elif existing and existing != agent:
        action, lead = 'reuse_existing', existing
    else:
        action, lead = 'reuse_current', agent
    return {'action': action, 'lead': lead, 'preferred_model': preferred_model,
            'preferred_effort': preferred_effort, 'preference_confirmed': configured,
            'note': 'Use only current-task configuration or explicit invocation evidence. '
                    'Reuse the current lead even when settings are unknown or differ. '
                    'Delegate for useful independent work, not model-name compliance. '
                    'This result neither observes nor changes runtime settings.'}


def fingerprints(skill_root):
    root = Path(skill_root).resolve()
    paths = [p for p in root.rglob('*') if p.is_file()
             and p.suffix in {'.md', '.py', '.yaml', '.json'} and '__pycache__' not in p.parts]
    # Shared policy is an actual dependency; do not scan unrelated skills/sessions.
    for name in ('model-policy.md', 'review-handoff.md', 'paired-installation.md'):
        shared = root.parent / 'document-feature-design/references' / name
        if shared.is_file():
            paths.append(shared)
    return [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(paths)]


def check_installation(skill_root):
    """Check the supported sibling pair and its local links, independent of cwd."""
    from urllib.parse import unquote, urlsplit
    root = Path(skill_root).resolve()
    pair = root.parent
    design = pair / 'document-feature-design'
    if root.name != 'review-large-pr':
        raise CoverageError('--skill-root must identify the review-large-pr directory.')
    required = [root / 'SKILL.md', design / 'SKILL.md',
                design / 'references/model-policy.md', design / 'references/review-handoff.md',
                design / 'scripts/validate_design_document.py',
                design / 'scripts/requirements.txt']
    required.extend(root / 'scripts' / name for name in (
        'review_run.py', 'review_coverage.py', 'review_checkpoint.py',
        'review_archive.py', 'review_environment.py', 'review_timing.py',
        'review_lifecycle.py', 'review_policy.py'))
    for path in required:
        if not path.is_file():
            raise CoverageError(f'Incomplete paired installation: {path}')
    from review_archive import markdown_links
    checked = set(required)
    for folder in (root, design):
        for source in folder.rglob('*.md'):
            def visit(match):
                url = urlsplit(match[2].removeprefix('<').removesuffix('>'))
                if not url.scheme and not url.netloc and url.path:
                    target = (source.parent / unquote(url.path)).resolve()
                    if not target.is_relative_to(pair) or not target.is_file():
                        raise CoverageError(f'Unresolved paired resource: {source} -> {url.path}')
                    checked.add(target)
                return match[0]
            markdown_links(source.read_text(encoding='utf-8'), visit)
    print(f'PASS: paired installation; {len(checked)} local resources resolve. '
          'Dependencies, model execution and semantic compatibility are separate checks.')


def init(args):
    coverages = []
    for name in args.coverage:
        path = Path(name).resolve()
        record = read(path)
        snap = record.get('snapshot') if isinstance(record, dict) else None
        if not isinstance(snap, dict):
            raise CoverageError('Coverage requires a snapshot.')
        validate_record(record, SimpleNamespace(record=str(path), repo=snap.get('repo_root'),
                        base=snap.get('target_base'), head=snap.get('head')))
        coverages.append({'path': str(path), 'snapshot': snap})
    if len({c['path'] for c in coverages}) != len(coverages):
        raise CoverageError('Duplicate coverage record.')
    data = {'schema_version': 1, 'created_at': now(), 'mode': args.mode,
            'selection_reason': nonempty(args.reason, 'selection reason'),
            'coverage': coverages, 'installed_skill_snapshot': fingerprints(args.skill_root),
            'lead': None, 'depth': {'level': 'unassessed', 'reason': ''},
            'boundaries': [], 'investigations': [], 'truncations': [], 'events': [],
            'limitations': [], 'timing': {'milestones': []}}
    with Path(args.output).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    print('Created run manifest. Record lead identity and depth assessment before completion. '
          'Fingerprints identify installed resources, not proof that every resource was loaded.')


def identified_rows(data, name):
    rows = data.get(name)
    if not isinstance(rows, list):
        raise CoverageError(f'{name} must be an array.')
    ids = set()
    for row in rows:
        if not isinstance(row, dict):
            raise CoverageError(f'{name} entries must be objects.')
        ident = nonempty(row.get('id'), name + '.id')
        if ident in ids:
            raise CoverageError(f'Duplicate {name} ID: {ident}')
        ids.add(ident)
    return rows


def validate_events(data):
    events = data.get('events')
    if not isinstance(events, list):
        raise CoverageError('events must be an array.')
    phases = {}
    previous = timestamp(data['created_at'])
    for e in events:
        if not isinstance(e, dict):
            raise CoverageError('Event must be an object.')
        t, recorded, basis = validate_observation(e)
        if recorded < previous:
            raise CoverageError('Event logging times must be chronological and after run creation.')
        previous = recorded
        key = (nonempty(e.get('owner'), 'owner'), nonempty(e.get('phase'), 'phase'))
        state = e.get('state')
        if state not in {'start', 'progress', 'waiting', 'blocked', 'complete', 'failed'}:
            raise CoverageError('Invalid event state.')
        nonempty(e.get('note'), 'event note')
        expected = e.get('expect_seconds')
        if expected is not None and (type(expected) is not int or expected <= 0):
            raise CoverageError('expect_seconds must be a positive integer or null.')
        if state == 'start':
            if key in phases:
                raise CoverageError('Phase already started; use a new phase ID for a retry.')
            phases[key] = {'start': t, 'last_known': t, 'last': e, 'basis': basis}
        elif key not in phases or phases[key]['last']['state'] in {'complete', 'failed'}:
            raise CoverageError('Event requires an active phase; preserve ended attempts.')
        else:
            known = phases[key]['last_known']
            if t is not None and known is not None and t < known:
                raise CoverageError('Effective phase timestamps must be chronological.')
            if t is not None:
                phases[key]['last_known'] = t
            if basis == 'legacy':
                phases[key]['basis'] = 'legacy'
            phases[key]['last'] = e
    return phases


def event(args):
    data = read(args.record)
    require_schema(data)
    if data['schema_version'] == 2:
        raise CoverageError('Use checkpoint for schema 2 so revisions and lifecycle history stay consistent.')
    validate_events(data)
    data['events'].append({**observation(args.at, args.unknown_time, args.source),
                           'owner': args.owner, 'phase': args.phase,
                           'state': args.state, 'note': args.note,
                           'expect_seconds': args.expect_seconds})
    validate_events(data)
    atomic_save(data, args.record)
    print('Progress event saved; no coverage or investigation result changed.')


def milestone(args):
    data = read(args.record)
    require_schema(data)
    if data['schema_version'] == 2:
        raise CoverageError('Use checkpoint for schema 2 so revisions and lifecycle history stay consistent.')
    if args.name == 'delivered' and (not args.at or not args.source):
        raise CoverageError('Delivered requires a host-observed --at and --source; readiness is not delivery.')
    timing_summary(data)
    data.setdefault('timing', {'milestones': []})['milestones'].append(
        dict(name=args.name, **observation(args.at, args.unknown_time, args.source)))
    timing_summary(data)
    atomic_save(data, args.record)
    print('Lifecycle observation saved. It does not attest host delivery or change review coverage.')


def require_schema(data):
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] not in {1, 2}:
        raise CoverageError('Expected run manifest schema_version 1 or 2.')


def inspect_run(data, path, require_complete=False, at=None, require_diagnostics=False):
    require_schema(data)
    created = timestamp(data.get('created_at'))
    bootstrap = data['schema_version'] == 2 and data.get('mode') == 'unassessed'
    if data.get('mode') not in {'light', 'full'} and not bootstrap:
        raise CoverageError('Mode must be light or full.')
    nonempty(data.get('selection_reason'), 'selection_reason')
    root = Path(path).resolve().parent
    pending, warnings, policy_pending, diagnostic_pending = [], [], [], []
    coverages = data.get('coverage')
    if not isinstance(coverages, list) or (not coverages and data['schema_version'] == 1):
        raise CoverageError('At least one coverage record is required.')
    if bootstrap:
        pending.append('mode unassessed')
    if not coverages:
        pending.append('coverage inventory not attached')
    seen = set()
    for c in coverages:
        if not isinstance(c, dict):
            raise CoverageError('Coverage references must be objects.')
        if data['schema_version'] == 2:
            ident = nonempty(c.get('id'), 'coverage id')
            p, record = Path(path), c.get('record')
            if set(c) != {'id', 'snapshot', 'record'}:
                raise CoverageError('Embedded coverage requires id, snapshot and record only.')
        else:
            p = Path(nonempty(c.get('path'), 'coverage path'))
            p = p if p.is_absolute() else root / p
            ident, record = str(p.resolve()), read(p)
        if ident in seen:
            raise CoverageError('Duplicate coverage reference.')
        seen.add(ident)
        snap = c.get('snapshot')
        if not isinstance(snap, dict) or not isinstance(record, dict) or record.get('snapshot') != snap:
            raise CoverageError('Run/coverage snapshot mismatch; preserve this run and reassess a new snapshot.')
        _, _, complete, _ = validate_record(record, SimpleNamespace(record=str(p),
            repo=snap.get('repo_root'), base=snap.get('target_base'), head=snap.get('head')))
        if not complete:
            pending.append(f'coverage incomplete: {ident}')
        for warning in audit_evidence(record):
            warnings.append(f'{ident}: {warning}')
    if data['schema_version'] == 2:
        from review_checkpoint import inspect_checkpoint_fields
        extra_pending, extra_warnings = inspect_checkpoint_fields(data, root)
        pending.extend(extra_pending)
        warnings.extend(extra_warnings)
    preferences(data.get('model_policy'))
    versions = data.get('installed_skill_snapshot')
    if not isinstance(versions, list) or not versions:
        raise CoverageError('Installed skill fingerprints are required.')
    for v in versions:
        if not isinstance(v, dict) or not isinstance(v.get('sha256'), str) or len(v['sha256']) != 64 or any(c not in '0123456789abcdef' for c in v['sha256']):
            raise CoverageError('Malformed skill fingerprint.')
        p = Path(nonempty(v.get('path'), 'fingerprint path'))
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != v['sha256']:
            warnings.append(f'Installed resource changed/missing since capture: {p}. Preserve the old hash and record any newly used version.')
    lead = data.get('lead')
    if lead is None:
        pending.append('lead identity unrecorded')
        policy_pending.append('lead configuration unrecorded')
    elif not isinstance(lead, dict):
        raise CoverageError('lead must be an object or null.')
    else:
        nonempty(lead.get('id'), 'lead.id')
        for field in ['selection', 'model', 'effort', 'configuration_source', 'evidence_kind']:
            if field in lead:
                nonempty(lead[field], 'lead.' + field)
        if lead.get('selection', 'current') not in {'current', 'existing', 'delegated', 'unavailable'} or lead.get('evidence_kind', 'unknown') not in {'runtime_config', 'invocation', 'unknown'}:
            raise CoverageError('Invalid lead selection/configuration evidence kind.')
        preferred = preferred_configuration(lead, data.get('model_policy'))
        if lead.get('user_override'):
            warnings.append('Explicit user model override recorded; validate its authority against the user request.')
        if ((lead.get('model'), lead.get('effort')) != preferred
                or lead.get('evidence_kind', 'unknown') == 'unknown'
                or not lead.get('configuration_source') or lead.get('selection') == 'unavailable'):
            policy_pending.append('Preferred lead settings are unconfirmed or differ; no backend execution claim')
    depth = data.get('depth')
    if not isinstance(depth, dict) or depth.get('level') not in {'unassessed', 'standard', 'deep'}:
        raise CoverageError('Depth level must be unassessed, standard or deep.')
    if depth['level'] == 'unassessed':
        pending.append('depth unassessed')
    else:
        nonempty(depth.get('reason'), 'depth.reason')
    if depth['level'] == 'deep' and data['mode'] != 'full':
        raise CoverageError('Deep investigation requires full mode.')
    boundaries = identified_rows(data, 'boundaries')
    for b in boundaries:
        nonempty(b.get('contract'), 'boundary.contract')
        if not isinstance(b.get('paths'), list) or not b['paths'] or any(not isinstance(p, str) or not p.strip() for p in b['paths']):
            raise CoverageError('Boundary needs actual paths, including relevant unchanged consumers.')
    if depth['level'] == 'deep' and not boundaries:
        pending.append('deep review has no critical boundaries')
    boundary_ids = {b['id'] for b in boundaries}
    investigations = identified_rows(data, 'investigations')
    resolved = set()
    for inv in investigations:
        if inv.get('boundary') not in boundary_ids or inv.get('pass') not in {'primary', 'challenge'}:
            raise CoverageError('Investigation needs a known boundary and primary/challenge pass.')
        for field in ['reviewer', 'hypothesis', 'assumption', 'method']:
            nonempty(inv.get(field), 'investigation.' + field)
        if inv.get('result') not in {'pending', 'supported', 'refuted', 'inconclusive'}:
            raise CoverageError('Invalid hypothesis result.')
        evidence_list(inv.get('evidence'), 'investigation.evidence', root)
        if type(inv.get('lead_verified')) is not bool:
            raise CoverageError('lead_verified must be a boolean.')
        if inv['result'] in {'pending', 'inconclusive'} or not inv['lead_verified']:
            pending.append(f'investigation unresolved/unverified: {inv["id"]}')
            continue
        if not inv['evidence']:
            raise CoverageError('Resolved investigation requires evidence.')
        nonempty(inv.get('conclusion'), 'investigation.conclusion')
        nonempty(inv.get('lead_check'), 'investigation.lead_check')
        if inv['pass'] == 'challenge':
            if inv.get('independence') not in {'fresh_reviewer', 'separate_lead_pass'}:
                raise CoverageError('Challenge needs fresh_reviewer or separate_lead_pass independence.')
            nonempty(inv.get('independence_reason'), 'challenge.independence_reason')
            if type(inv.get('prior_findings_withheld')) is not bool:
                raise CoverageError('Challenge must record whether prior findings were withheld.')
            if inv['independence'] == 'fresh_reviewer' and any(
                p['reviewer'] == inv['reviewer'] and p['boundary'] == inv['boundary']
                and p['pass'] == 'primary' for p in investigations):
                raise CoverageError('A fresh reviewer cannot be the primary reviewer for the same boundary.')
            if inv['independence'] == 'separate_lead_pass' and (not lead or inv['reviewer'] != lead['id']):
                raise CoverageError('A separate_lead_pass must be performed by the designated lead.')
        resolved.add((inv['boundary'], inv['pass']))
    for b in boundaries:
        for kind in (['primary', 'challenge'] if depth['level'] == 'deep' else ['primary']):
            if (b['id'], kind) not in resolved:
                pending.append(f'missing resolved {kind} investigation: {b["id"]}')
    for gap in identified_rows(data, 'truncations'):
        nonempty(gap.get('source'), 'truncation.source')
        nonempty(gap.get('remaining'), 'truncation.remaining')
        evidence_list(gap.get('evidence'), 'truncation.evidence', root)
        if gap.get('status') == 'open':
            pending.append(f'unread truncated source: {gap["id"]}')
        elif gap.get('status') != 'resolved' or not gap['evidence']:
            raise CoverageError('Resolved truncation requires follow-up evidence.')
    phases = validate_events(data)
    if not phases:
        diagnostic_pending.append('no phase timing recorded')
    current = at or datetime.now(timezone.utc)
    for (owner, phase), state in phases.items():
        e = state['last']
        ended = e['state'] in {'complete', 'failed'}
        end, recorded, basis = validate_observation(e)
        end = end if ended else current
        elapsed = (f'{(end-state["start"]).total_seconds():.1f}s'
                   if end is not None and state['start'] is not None else 'unknown')
        label = 'legacy checkpoint interval' if state['basis'] == 'legacy' else 'elapsed'
        print(f'Phase {owner}/{phase}: {e["state"]}, {label}={elapsed}; {e["note"]}')
        if state['basis'] == 'legacy':
            warnings.append(f'Legacy timing for {owner}/{phase}: actual phase boundaries are not attested.')
        if not ended:
            diagnostic_pending.append(f'active phase: {owner}/{phase}')
            if e.get('expect_seconds') and (current-recorded).total_seconds() > e['expect_seconds']:
                warnings.append(f'Progress observation due for {owner}/{phase}; inspect one status/checkpoint. Elapsed time is not proof of a stall.')
    finish = max((validate_observation(e)[1] for e in data['events']), default=created)
    if any(p['last']['state'] not in {'complete', 'failed'} for p in phases.values()):
        finish = current
    show_timing = bool(phases or (data.get('timing') or {}).get('milestones') or require_diagnostics)
    if show_timing:
        print(f'Manifest observation window={(finish-created).total_seconds():.1f}s; not end-to-end duration. Phase intervals may overlap; do not sum them.')
    durations, timing_warnings = timing_summary(data)
    if show_timing:
        warnings.extend(timing_warnings)
    points = {row['name'] for row in (data.get('timing') or {}).get('milestones', [])}
    for name in ('intake', 'lead_start', 'lead_complete'):
        if name not in points:
            diagnostic_pending.append(f'lifecycle endpoint missing: {name}; record evidence or explicitly unknown')
    for name, seconds in (durations.items() if show_timing else []):
        print(f'Timing {name}: ' + ('unknown' if seconds is None else f'{seconds:.1f}s'))
    for warning in warnings:
        print('WARNING: ' + warning)
    print('Recorded review/record obligations: ' + ('pending: ' + '; '.join(pending) if pending else 'resolved') + '.')
    print('Model observations (optional): ' + ('limited: ' + '; '.join(policy_pending) if policy_pending
          else 'supported by recorded configuration/invocation; backend execution is not attested') + '.')
    diagnostic_pending.extend(policy_pending)
    if require_diagnostics or show_timing:
        print('Optional diagnostics: ' + ('; '.join(diagnostic_pending) if diagnostic_pending else 'recorded') + '.')
    if require_complete and pending:
        raise CoverageError('Run incomplete: ' + '; '.join(pending))
    if require_diagnostics and diagnostic_pending:
        raise CoverageError('Diagnostics incomplete: ' + '; '.join(diagnostic_pending))
    print('PASS: structural run checks; ' + ('incomplete: ' + '; '.join(pending) if pending else 'recorded obligations resolved') +
          '. Lead must verify depth, evidence meaning, freshness and actual execution; no defect-count quota.')
    return pending, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    routing = sub.add_parser('route', help='Recommend lead reuse from supplied current-task configuration.')
    routing.add_argument('--input', required=True)
    routing.add_argument('--repo', help='Project root containing optional .ai-skills.json.')
    routing.add_argument('--policy', help='Explicit project model policy file.')
    installation = sub.add_parser('check-installation', help='Verify the supported sibling pair and local resources.')
    installation.add_argument('--skill-root', default=str(Path(__file__).resolve().parent.parent))
    create = sub.add_parser('init', help='Capture coverage identities and installed skill fingerprints.')
    create.add_argument('--coverage', action='append', required=True)
    create.add_argument('--output', required=True)
    create.add_argument('--mode', choices=['light', 'full'], required=True)
    create.add_argument('--reason', required=True)
    create.add_argument('--skill-root', default=str(Path(__file__).resolve().parent.parent))
    from review_checkpoint import add_commands, dispatch
    add_commands(sub)
    from review_lifecycle import add_commands as lifecycle_commands, dispatch as lifecycle_dispatch
    lifecycle_commands(sub)
    update = sub.add_parser('event', help='Append a timestamped progress checkpoint; preserve earlier attempts.')
    update.add_argument('record')
    update.add_argument('--owner', required=True)
    update.add_argument('--phase', required=True)
    update.add_argument('--state', choices=['start', 'progress', 'waiting', 'blocked', 'complete', 'failed'], required=True)
    update.add_argument('--note', required=True)
    update.add_argument('--expect-seconds', type=int)
    life = sub.add_parser('milestone', help='Record intake, lead and delivery endpoints from actual evidence.')
    life.add_argument('record')
    life.add_argument('--name', choices=MILESTONES, required=True)
    for command in (update, life):
        choice = command.add_mutually_exclusive_group()
        choice.add_argument('--at', help='Retrospective ISO timestamp; requires --source.')
        choice.add_argument('--unknown-time', action='store_true', help='Earlier boundary not measured; requires --source.')
        command.add_argument('--source', help='Timestamp evidence or reason it is unknown.')
    check = sub.add_parser('check', help='Validate records and report phase timing/observation warnings.')
    check.add_argument('record')
    check.add_argument('--require-complete', action='store_true')
    check.add_argument('--require-diagnostics', action='store_true', help='Also require optional timing and model evidence.')
    args = parser.parse_args(argv)
    try:
        if args.command in {'start', 'assess', 'record', 'finish'}:
            lifecycle_dispatch(args)
        elif args.command in {'begin', 'checkpoint', 'promote', 'repair-evidence'}:
            dispatch(args)
        elif args.command == 'check-installation':
            check_installation(args.skill_root)
        elif args.command == 'route':
            print(json.dumps(route(read(args.input), load_policy(args.repo, args.policy)), indent=2))
        elif args.command == 'init':
            init(args)
        elif args.command == 'event':
            event(args)
        elif args.command == 'milestone':
            milestone(args)
        else:
            inspect_run(read(args.record), args.record, args.require_complete,
                        require_diagnostics=args.require_diagnostics)
    except (CoverageError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

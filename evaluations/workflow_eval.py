#!/usr/bin/env python3
"""Prepare isolated workflow tasks and compare independently judged agent outputs.

No agent is invoked and no semantic score is inferred from a helper's exit code.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


CASES = {
    'cross-boundary': {'defects': ['tenant-cache-key'],
        'checks': ['source_traceable', 'connected_path_checked', 'coverage_honest']},
    'follow-up': {'defects': [],
        'checks': ['source_traceable', 'fixed_finding_closed', 'unaffected_evidence_reassessed']},
    'mechanical': {'defects': [],
        'checks': ['source_traceable', 'coverage_honest', 'proportional_investigation']},
    'concise-adr': {'defects': [],
        'checks': ['source_traceable', 'separates_status', 'alternatives_grounded', 'revisit_conditions']},
}
BASE_CACHE = '''class UserCache:
    def __init__(self):
        self.values = {}

    def key(self, tenant, user_id):
        return (tenant, user_id)

    def get(self, tenant, user_id, load):
        key = self.key(tenant, user_id)
        if key not in self.values:
            self.values[key] = load()
        return self.values[key]

    def evict(self, tenant, user_id):
        self.values.pop(self.key(tenant, user_id), None)
'''
BASE_SERVICE = '''def profile(database, cache, tenant, user_id):
    return cache.get(tenant, user_id, lambda: database[(tenant, user_id)])
'''
BASE_API = '''from service import profile

def get_profile(database, cache, claims, user_id):
    return profile(database, cache, claims['tenant'], str(user_id))
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME='Workflow fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
        GIT_COMMITTER_NAME='Workflow fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
        GIT_AUTHOR_DATE='2026-01-01T00:00:00Z', GIT_COMMITTER_DATE='2026-01-01T00:00:00Z')
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
        '-C', str(repo), *args], env=env, stderr=subprocess.PIPE).decode().strip()


def commit(repo, message):
    git(repo, 'add', '-A')
    git(repo, 'commit', '-qm', message)
    return git(repo, 'rev-parse', 'HEAD')


def fixture(repo):
    repo.mkdir(parents=True)
    git(repo, 'init', '-q')
    for name, content in {'cache.py': BASE_CACHE, 'service.py': BASE_SERVICE, 'api.py': BASE_API,
        'requirements.md': '# Accepted fixture requirements\nUser IDs are unique within a tenant only. '
                           'A profile response must always belong to the authenticated tenant.\n'}.items():
        (repo / name).write_text(content)
    (repo / 'clients').mkdir()
    for index in range(40):
        (repo / 'clients' / f'client-{index:02}.json').write_text(json.dumps({'client': index, 'schema_label': 'v1'}) + '\n')
    return commit(repo, 'Fixture base')


def relabel(repo):
    for path in (repo / 'clients').glob('*.json'):
        path.write_text(path.read_text().replace('"v1"', '"v2"'))


def prepare(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Corpus output must be new; preserve existing runs and results.')
    output.mkdir(parents=True)
    try:
        snapshots = {}
        project = output / 'cases/cross-boundary/project'
        base = fixture(project)
        relabel(project)
        (project / 'cache.py').write_text(BASE_CACHE.replace('return (tenant, user_id)', 'return user_id'))
        (project / 'service.py').write_text(BASE_SERVICE + '\n# Cache keys are shared across API consumers.\n')
        head = commit(project, 'Cache refactor and client metadata refresh')
        snapshots['cross-boundary'] = {'base': base, 'head': head}
        follow = output / 'cases/follow-up/project'
        shutil.copytree(project, follow)
        (follow / 'cache.py').write_text(BASE_CACHE)
        fixed = commit(follow, 'Retain tenant in cache identity')
        snapshots['follow-up'] = {'base': base, 'previous_head': head, 'head': fixed}
        (follow.parent / 'prior-review.md').write_text(
            f'# Prior review at {head}\nP1 tenant-cache-key: cache.key drops tenant. '
            'After tenant A warms user 7, tenant B receives A\'s profile through api.get_profile. '
            'Client label changes were inspected as mechanical; they have no runtime readers in this fixture. '
            'Reassess applicability instead of assuming unchanged bytes prove reuse.\n')
        mechanical = output / 'cases/mechanical/project'
        mech_base = fixture(mechanical)
        relabel(mechanical)
        snapshots['mechanical'] = {'base': mech_base, 'head': commit(mechanical, 'Mechanical client label update')}
        proposal = Path(__file__).resolve().parents[1] / 'document-feature-design/examples/proposal.md'
        doc = output / 'cases/concise-adr'
        doc.mkdir(parents=True)
        shutil.copyfile(proposal, doc / 'proposal.md')
        snapshots['concise-adr'] = {'proposal_sha256': digest(proposal.read_bytes())}
        for name in CASES:
            folder = output / 'cases' / name
            if name == 'concise-adr':
                prompt = 'Write a concise ADR from proposal.md. Preserve source identity, decision/implementation/deployment status, alternatives and revisit conditions. Save adr.md locally.'
            else:
                snap = snapshots[name]
                prompt = f'Review the PR in project from base {snap["base"]} to head {snap["head"]}. Read requirements.md. Save a local review with findings, evidence and honest coverage.'
                if name == 'follow-up':
                    prompt += ' Resume the prior review in prior-review.md, inspect the fix and reassess carried-forward evidence without repeating unaffected work.'
            (folder / 'prompt.txt').write_text(prompt + '\n')
        corpus_id = digest(json.dumps({'cases': CASES, 'snapshots': snapshots}, sort_keys=True).encode())
        manifest = {'schema_version': 1, 'corpus_id': corpus_id, 'snapshots': snapshots, 'cases': CASES}
        (output / 'oracle.json').write_text(json.dumps(manifest, indent=2) + '\n')
        for arm in ('baseline', 'skill'):
            labels = {'schema_version': 1, 'corpus_id': corpus_id, 'arm': arm,
                'conditions': dict(model=None, effort=None, tools=None, budget=None),
                'judge': '', 'cases': []}
            for name, spec in CASES.items():
                labels['cases'].append({'id': name, 'output': f'outputs/{arm}/{name}.md', 'trace': None,
                    'matched_defects': [], 'unsupported_findings': None,
                    'checks': dict.fromkeys(spec['checks']), 'clarifications': None,
                    'repeated_work': None, 'setup_calls': None, 'elapsed_seconds': None, 'evidence_notes': ''})
            (output / f'{arm}-labels.json').write_text(json.dumps(labels, indent=2) + '\n')
        return manifest
    except Exception:
        shutil.rmtree(output)
        raise


def artifact(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Each judged run needs its actual output artifact.')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f'Artifact must be a nonempty file under the labels folder: {name}')
    raw = path.read_bytes()
    if not raw.strip():
        raise ValueError(f'Artifact must be a nonempty file under the labels folder: {name}')
    return digest(raw)


def score(path, oracle, arm):
    path = Path(path)
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1 or data.get('corpus_id') != oracle['corpus_id'] or data.get('arm') != arm:
        raise ValueError('Labels must identify the same corpus and the expected arm.')
    conditions = data.get('conditions')
    if (not isinstance(conditions, dict) or set(conditions) != {'model', 'effort', 'tools', 'budget'}
            or any(not isinstance(v, str) or not v.strip() for v in conditions.values())):
        raise ValueError('Record model, effort, tools and budget; do not compare unrecorded conditions.')
    if not isinstance(data.get('judge'), str) or not data['judge'].strip():
        raise ValueError('Identify the independent evaluator.')
    rows = data.get('cases')
    if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            or len(rows) != len(oracle['cases']) or {r.get('id') for r in rows} != set(oracle['cases'])):
        raise ValueError('Exactly one result per corpus case is required.')
    results = {}
    for row in rows:
        name = row['id']
        spec = oracle['cases'][name]
        found = row.get('matched_defects')
        if (not isinstance(found, list) or any(not isinstance(v, str) for v in found)
                or len(set(found)) != len(found) or not set(found) <= set(spec['defects'])):
            raise ValueError('Matched defects must be distinct known oracle IDs; adjudicate unexpected findings separately.')
        checks = row.get('checks')
        if (not isinstance(checks, dict) or set(checks) != set(spec['checks'])
                or any(v is not None and type(v) is not bool for v in checks.values())):
            raise ValueError('Judge each named quality check as true, false or null (unknown).')
        if not isinstance(row.get('evidence_notes'), str) or not row['evidence_notes'].strip():
            raise ValueError('Judgments require output/trace locators and reasoning in evidence_notes.')
        for key in ('unsupported_findings', 'clarifications', 'repeated_work', 'setup_calls', 'elapsed_seconds'):
            value = row[key]
            if value is not None and (type(value) not in ({int, float} if key == 'elapsed_seconds' else {int})
                                      or not math.isfinite(value) or value < 0):
                raise ValueError(f'{key} must be a nonnegative observation or null.')
        output_hash = artifact(path.parent, row['output'])
        trace_hash = artifact(path.parent, row['trace']) if row.get('trace') else None
        if trace_hash is None and any(row[k] is not None for k in ('clarifications', 'repeated_work', 'setup_calls', 'elapsed_seconds')):
            raise ValueError('Process metrics require a retained trace; otherwise record null.')
        unsupported = row['unsupported_findings']
        denominator = len(found) + unsupported if unsupported is not None else 0
        results[name] = dict(missed_defects=sorted(set(spec['defects']) - set(found)),
            precision=len(found) / denominator if denominator else None,
            recall=len(found) / len(spec['defects']) if spec['defects'] else None,
            unsupported_findings=unsupported, checks=checks, output_sha256=output_hash,
            trace_sha256=trace_hash, **{k: row[k] for k in ('clarifications', 'repeated_work', 'setup_calls', 'elapsed_seconds')})
    return {'conditions': conditions, 'judge': data['judge'], 'cases': results}


def compare(oracle_path, baseline_path, skill_path):
    oracle = json.loads(Path(oracle_path).read_text())
    if (oracle.get('schema_version') != 1 or oracle.get('corpus_id') !=
            digest(json.dumps({'cases': oracle['cases'], 'snapshots': oracle['snapshots']}, sort_keys=True).encode())):
        raise ValueError('Oracle identity does not match its retained cases and snapshots.')
    baseline, skill = score(baseline_path, oracle, 'baseline'), score(skill_path, oracle, 'skill')
    if baseline['conditions'] != skill['conditions']:
        raise ValueError('Conditions differ; use matched runs before attributing an outcome to the skill.')
    return {'corpus_id': oracle['corpus_id'], 'baseline': baseline, 'skill': skill,
            'limits': 'Scores depend on independent human judgments and retained artifacts. '
                      'Unknown observations remain null; synthetic tasks do not establish general superiority.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('prepare')
    build.add_argument('--output', required=True)
    report = sub.add_parser('compare')
    for key in ('oracle', 'baseline', 'skill'):
        report.add_argument('--' + key, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.output) if args.command == 'prepare' else compare(args.oracle, args.baseline, args.skill)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

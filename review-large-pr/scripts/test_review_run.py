#!/usr/bin/env python3
"""Behavioral run-helper tests with real isolated Git snapshots; no network."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import review_run
from review_coverage import CoverageError


class RoutingCases(unittest.TestCase):
    def routing(self, **extra):
        return review_run.route(dict(agent='root', role='unassigned', can_delegate=True, **extra))['action']

    def test_known_astra_xhigh_is_reused(self):
        self.assertEqual(self.routing(model='gpt-6-astra', effort='xhigh',
                                     configuration_source='current task config'), 'reuse_current')

    def test_unknown_or_different_settings_reuse_current_lead(self):
        for values in [dict(model='gpt-6-astra'), dict(model='gpt-6-astra', effort='xhigh'),
                       dict(model='gpt-6-astra', effort='xhigh', configuration_source=42),
                       dict(model='gpt-6-astra', effort='high', configuration_source='current config')]:
            self.assertEqual(self.routing(**values), 'reuse_current')

    def test_existing_lead_and_assigned_workers_never_create_second_lead(self):
        self.assertEqual(self.routing(existing_lead='lead'), 'reuse_existing')
        for role in ['reviewer', 'documentation-author']:
            self.assertEqual(review_run.route(dict(agent='worker', role=role, existing_lead='lead',
                                                   can_delegate=True))['action'], 'retain_assignment')
        self.assertEqual(review_run.route(dict(agent='lead', role='lead', can_delegate=True))['action'],
                         'reuse_current')

    def test_unavailable_delegation_reuses_current_lead(self):
        self.assertEqual(review_run.route(dict(agent='root', can_delegate=False))['action'],
                         'reuse_current')

    def test_explicit_user_override_is_recorded_without_changing_default(self):
        self.assertEqual(self.routing(model='gpt-6-astra', effort='high', configuration_source='runtime config',
                         user_override=dict(authority='explicit_user', model='gpt-6-astra', effort='high',
                                            source='User explicitly requested high for this review')), 'reuse_current')
        with self.assertRaises(CoverageError):
            self.routing(user_override=dict(model='gpt-6.1-sol', effort='high'))


class InstallationCases(unittest.TestCase):
    def test_complete_pair_resolves_after_copy_from_unrelated_cwd(self):
        pair = Path(review_run.__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder:
            staged = Path(folder) / 'staged'; staged.mkdir()
            for name in ('document-feature-design', 'review-large-pr'):
                shutil.copytree(pair / name, staged / name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            script = staged / 'review-large-pr/scripts/review_run.py'
            result = subprocess.run([sys.executable, str(script), 'check-installation'],
                                    cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('paired installation', result.stdout)
            policy = staged / 'document-feature-design/references/model-policy.md'
            self.assertIn(str(policy.resolve()), [row['path'] for row in review_run.fingerprints(script.parent.parent)])
            policy.unlink()
            result = subprocess.run([sys.executable, str(script), 'check-installation'],
                                    cwd=folder, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Incomplete paired installation', result.stderr)


class RunCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Review Test')
        self.git('config', 'user.email', 'review@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        (self.repo / 'logic.py').write_text('limit = 1\n')
        self.base = self.commit('base')
        (self.repo / 'logic.py').write_text('limit = 2\n')
        self.head = self.commit('change')
        self.coverage = self.root / 'coverage.json'
        self.coverage_cli('init', '--output', str(self.coverage))
        data = json.loads(self.coverage.read_text())
        self.evidence = self.root / 'evidence.md'
        self.evidence.write_text('## B1\nRead actual admission and consumer; the limit is checked before the effect.\n')
        citation = self.citation()
        data['files'][0].update(status='reviewed', units=['R1'], evidence=[citation])
        data['integration'].update(status='reviewed', evidence=[citation])
        self.coverage.write_text(json.dumps(data))
        self.skill = self.root / 'skill'
        self.skill.mkdir()
        (self.skill / 'SKILL.md').write_text('test skill snapshot\n')
        self.record = self.root / 'run.json'
        self.cli('init', '--coverage', str(self.coverage), '--output', str(self.record),
                 '--mode', 'full', '--reason', 'Durable effect boundary', '--skill-root', str(self.skill))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args]).decode().strip()

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def coverage_cli(self, command, *args):
        subprocess.run([sys.executable, str(Path(__file__).with_name('review_coverage.py')), command,
                        *args, '--repo', str(self.repo), '--base', self.base, '--head', self.head],
                       check=True, capture_output=True)

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(Path(review_run.__file__)), *args],
                                capture_output=True, text=True)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def load(self):
        return json.loads(self.record.read_text())

    def save(self, data):
        self.record.write_text(json.dumps(data))

    def citation(self):
        return dict(path='evidence.md', locator='B1 / admission',
                    claim='The actual consumer rejects out-of-bound values before issuing the effect.')

    def investigation(self, ident='H1', kind='primary', reviewer='R1'):
        return dict(id=ident, boundary='B1', **{'pass': kind}, reviewer=reviewer,
                    hypothesis='An accepted value can exceed the downstream limit',
                    assumption='The positive fixture uses only a small value',
                    method='Trace admission and consumer bounds at base/head', result='refuted',
                    evidence=[self.citation()], conclusion='Admission imposes the stricter bound',
                    lead_verified=True, lead_check='Checked both bounds and every caller',
                    independence='fresh_reviewer', independence_reason='Separate reviewer on this boundary',
                    prior_findings_withheld=True)

    def finish(self, deep=False):
        data = self.load()
        data['lead'] = dict(id='root', selection='current', model='gpt-6-astra', effort='xhigh',
                            configuration_source='test current-task configuration', evidence_kind='runtime_config')
        data['depth'] = dict(level='deep' if deep else 'standard', reason='Inspected actual changed contract')
        if deep:
            data['boundaries'] = [dict(id='B1', contract='Bounds precede the effect', paths=['logic.py'])]
            data['investigations'] = [self.investigation(), self.investigation('H2', 'challenge', 'R2')]
        self.save(data)
        self.cli('event', str(self.record), '--phase', 'review', '--owner', 'root', '--state', 'start', '--note', 'Review began')
        self.cli('event', str(self.record), '--phase', 'review', '--owner', 'root', '--state', 'complete', '--note', 'Evidence B1 saved')
        return self.load()

    def check(self, complete=True, ok=True):
        return self.cli('check', str(self.record), *(['--require-complete'] if complete else []), ok=ok)

    def test_unassessed_run_is_resumable_but_cannot_complete(self):
        self.check(complete=False)
        result = self.check(ok=False)
        self.assertIn('depth unassessed', result.stderr)

    def test_light_record_needs_no_deep_ledger_or_workers(self):
        data = self.finish()
        data['mode'] = 'light'
        self.save(data)
        self.check()

    def test_deep_resolved_source_investigations_allow_zero_findings(self):
        self.finish(deep=True)
        self.check()

    def test_deep_empty_boundary_or_missing_challenge_is_incomplete(self):
        data = self.finish(deep=True)
        data['investigations'].pop()
        self.save(data)
        self.assertIn('missing resolved challenge', self.check(ok=False).stderr)
        data['boundaries'] = []
        data['investigations'] = []
        self.save(data)
        self.assertIn('no critical boundaries', self.check(ok=False).stderr)

    def test_inconclusive_or_unverified_hypothesis_blocks_completion_despite_file_coverage(self):
        data = self.finish(deep=True)
        for change in [dict(result='inconclusive'), dict(lead_verified=False)]:
            changed = json.loads(json.dumps(data))
            changed['investigations'][0].update(change)
            self.save(changed)
            self.assertIn('unresolved/unverified', self.check(ok=False).stderr)

    def test_supported_defect_does_not_make_review_incomplete(self):
        data = self.finish(deep=True)
        data['investigations'][0].update(result='supported', conclusion='Admitted value violates the downstream limit')
        self.save(data)
        self.check()

    def test_truncated_region_requires_followup_evidence(self):
        data = self.finish()
        data['truncations'] = [dict(id='T1', source='logic.py tail omitted', remaining='lines 20-80', status='open', evidence=[])]
        self.save(data)
        self.assertIn('unread truncated source', self.check(ok=False).stderr)
        data['truncations'][0]['status'] = 'resolved'
        self.save(data)
        self.assertIn('follow-up evidence', self.check(ok=False).stderr)
        data['truncations'][0]['evidence'] = [self.citation()]
        self.save(data)
        self.check()

    def test_fresh_challenge_cannot_be_same_primary_reviewer(self):
        data = self.finish(deep=True)
        data['investigations'][1]['reviewer'] = 'R1'
        self.save(data)
        self.assertIn('cannot be the primary', self.check(ok=False).stderr)
        data['investigations'][1].update(independence='separate_lead_pass')
        self.save(data)
        self.assertIn('designated lead', self.check(ok=False).stderr)
        data['investigations'][1].update(independence='separate_lead_pass', reviewer='root',
                                         independence_reason='Delegation unavailable; separate lead reasoning pass')
        self.save(data)
        self.check()

    def test_missing_or_wrong_lead_configuration_prevents_compliance_claim(self):
        data = self.finish()
        for change in [dict(effort='high'), dict(model='gpt-6.1-sol'), dict(evidence_kind='unknown'), dict(selection='unavailable')]:
            changed = json.loads(json.dumps(data)); changed['lead'].update(change)
            self.save(changed)
            result = self.check()
            strict = self.cli('check', str(self.record), '--require-complete', '--require-diagnostics', ok=False)
            self.assertIn('Preferred lead settings', strict.stderr)
            self.assertIn('Recorded review/record obligations: resolved.', result.stdout)
            self.assertIn('Model observations (optional): limited:', result.stdout)

    def test_explicit_user_choice_can_override_policy_but_not_configuration_evidence(self):
        data = self.finish()
        data['lead'].update(effort='high', user_override=dict(authority='explicit_user', model='gpt-6-astra',
                            effort='high', source='Direct user request for this review'))
        self.save(data)
        self.assertIn('Explicit user model override', self.check().stdout)
        data['lead']['evidence_kind'] = 'unknown'; self.save(data)
        self.check()
        self.cli('check', str(self.record), '--require-diagnostics', ok=False)

    def test_missing_artifact_or_malformed_investigation_fails(self):
        data = self.finish(deep=True)
        for change in [dict(evidence=[]), dict(evidence=[dict(self.citation(), path='absent.md')]),
                       dict(lead_verified='yes'), dict(boundary='unknown'), dict(hypothesis='')]:
            changed = json.loads(json.dumps(data)); changed['investigations'][0].update(change)
            self.save(changed)
            self.check(ok=False)

    def test_skill_drift_warns_without_rewriting_original_fingerprint(self):
        self.finish()
        before = self.record.read_bytes()
        (self.skill / 'SKILL.md').write_text('changed\n')
        self.assertIn('changed/missing since capture', self.check().stdout)
        self.assertEqual(self.record.read_bytes(), before)

    def test_same_head_escalation_preserves_events_and_coverage(self):
        data = self.finish()
        data['mode'] = 'light'; self.save(data)
        before = self.coverage.read_bytes()
        prior_events = data['events'][:]
        data['mode'] = 'full'; data['depth'] = dict(level='deep', reason='New cross-boundary risk')
        data['boundaries'] = [dict(id='B1', contract='Bound precedes effect', paths=['logic.py'])]
        data['investigations'] = [self.investigation()]; self.save(data)
        self.check(ok=False)
        data['investigations'].append(self.investigation('H2', 'challenge', 'R2')); self.save(data)
        self.check()
        self.assertEqual(self.load()['events'], prior_events)
        self.assertEqual(self.coverage.read_bytes(), before)

    def test_new_snapshot_cannot_be_substituted_under_old_run(self):
        self.finish()
        (self.repo / 'logic.py').write_text('limit = 3\n')
        self.head = self.commit('next')
        self.coverage.unlink()
        self.coverage_cli('init', '--output', str(self.coverage))
        self.assertIn('snapshot mismatch', self.check(ok=False).stderr)

    def test_phase_events_preserve_attempts_and_do_not_change_assessments(self):
        before = self.load()
        args = ['event', str(self.record), '--phase', 'setup', '--owner', 'lead']
        self.cli(*args, '--state', 'start', '--note', 'Install underway', '--expect-seconds', '120')
        self.cli(*args, '--state', 'failed', '--note', 'Missing package access; no retry')
        saved = self.record.read_bytes()
        self.cli(*args, '--state', 'progress', '--note', 'Cannot rewrite ended attempt', ok=False)
        self.assertEqual(self.record.read_bytes(), saved)
        after = self.load(); after['events'] = []
        self.assertEqual(after, before)

    def test_slow_progress_is_warning_without_automatic_stall_or_write(self):
        data = self.finish()
        self.cli('event', str(self.record), '--phase', 'experiment', '--owner', 'R1', '--state', 'start',
                 '--note', 'Known process running; next saved trace expected', '--expect-seconds', '60')
        data = self.load(); before = self.record.read_bytes()
        future = datetime.now(timezone.utc) + timedelta(seconds=120)
        with redirect_stdout(io.StringIO()):
            pending, warnings = review_run.inspect_run(data, self.record, at=future)
        self.assertTrue(any('observation due' in w for w in warnings))
        self.assertFalse(any('active phase' in p for p in pending))
        with self.assertRaisesRegex(CoverageError, 'active phase'):
            with redirect_stdout(io.StringIO()):
                review_run.inspect_run(data, self.record, at=future, require_diagnostics=True)
        self.assertEqual(self.record.read_bytes(), before)

    def test_init_refuses_overwrite(self):
        before = self.record.read_bytes()
        self.cli('init', '--coverage', str(self.coverage), '--output', str(self.record), '--mode', 'light',
                 '--reason', 'bounded', ok=False)
        self.assertEqual(self.record.read_bytes(), before)

    def test_milestone_cli_preserves_coverage_and_refuses_duplicate(self):
        self.finish()
        before = self.coverage.read_bytes()
        args = ['milestone', str(self.record), '--name', 'intake', '--at',
                '2026-01-01T12:00:00Z', '--source', 'Coordinator checkpoint']
        self.cli(*args)
        saved = self.record.read_bytes()
        self.cli(*args, ok=False)
        self.assertEqual(self.record.read_bytes(), saved)
        self.assertEqual(self.coverage.read_bytes(), before)
        self.assertIn('end_to_end: unknown', self.check().stdout)

    def test_retrospective_unknown_phase_is_not_near_zero(self):
        self.finish()
        args = ['event', str(self.record), '--phase', 'earlier-context', '--owner', 'root',
                '--unknown-time', '--source', 'Phase was not measured', '--note', 'Saved context']
        self.cli(*args, '--state', 'start')
        self.cli(*args, '--state', 'complete')
        self.assertIn('earlier-context: complete, elapsed=unknown', self.check().stdout)

    def test_legacy_record_warns_and_does_not_claim_total_wall_time(self):
        data = self.finish()
        data.pop('timing')
        for row in data['events']:
            for key in ['basis', 'recorded_at', 'source']:
                row.pop(key)
        self.save(data)
        output = self.check().stdout
        self.assertIn('legacy checkpoint interval', output)
        self.assertIn('end-to-end duration is unknown', output)
        self.assertNotIn('Run wall time=', output)

    def test_atomic_event_failure_keeps_manifest(self):
        before = self.record.read_bytes()
        with patch('review_coverage.os.replace', side_effect=PermissionError('denied')):
            self.assertEqual(review_run.main(['event', str(self.record), '--phase', 'review', '--owner', 'root',
                                             '--state', 'start', '--note', 'start']), 1)
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.run.json.*')), [])

    def test_malformed_records_fail_without_traceback(self):
        for value in ['[]', '{', '{"schema_version": true}', '{"schema_version": 1, "created_at": 42}']:
            self.record.write_text(value)
            self.check(ok=False)


if __name__ == '__main__':
    unittest.main(verbosity=2)

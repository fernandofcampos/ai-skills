"""Exercise the user commands against real Git snapshots and relocated evidence."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import review_archive
import review_lifecycle
import review_policy
import review_run
from review_coverage import CoverageError
import test_review_run as legacy


class LifecycleCases(unittest.TestCase):
    git = legacy.RunCases.git
    commit = legacy.RunCases.commit
    coverage_cli = legacy.RunCases.coverage_cli
    cli = legacy.RunCases.cli
    load = legacy.RunCases.load
    save = legacy.RunCases.save
    citation = legacy.RunCases.citation

    def setUp(self):
        legacy.RunCases.setUp(self)
        durable = tempfile.TemporaryDirectory(prefix='.lifecycle-test-', dir=Path.cwd())
        self.addCleanup(durable.cleanup)
        self.delivery_root = Path(durable.name)
        self.run_dir = self.root / 'review'
        self.cli('start', '--repo', str(self.repo), '--base', self.base, '--head', self.head,
                 '--output', str(self.run_dir))
        self.record = self.run_dir / 'run.json'
        self.output = self.delivery_root / 'archive'

    def complete(self):
        self.cli('assess', str(self.record), '--depth', 'standard', '--reason', 'Constant and consumer traced',
                 '--source-only', 'Source trace establishes constant bounds without runtime-dependent behavior')
        (self.run_dir / 'evidence.md').write_text('## Limit\nlogic.py: limit changes from 1 to 2; its consumer was inspected.\n')
        (self.run_dir / 'review-record.md').write_text('# Review\nScope: constant change. No defect found.\n[Evidence](evidence.md#limit)\n')
        citation = ['--evidence-file', 'evidence.md', '--locator', 'Limit / logic.py',
                    '--claim', 'Constant and relevant consumer traced at both revisions']
        self.cli('record', str(self.record), '--path', 'logic.py', '--status', 'reviewed', '--unit', 'R1', *citation)
        self.cli('record', str(self.record), '--integration', '--status', 'reviewed', *citation)

    def test_start_pins_snapshot_and_leaves_truth_unassessed(self):
        data = self.load()
        self.assertEqual(data['coverage'][0]['snapshot']['head'], self.head)
        self.assertEqual(data['coverage'][0]['record']['files'][0]['status'], 'unreviewed')
        self.assertEqual(data['depth']['level'], 'unassessed')
        self.assertEqual(data['events'], [])
        self.assertNotIn('model', data['lead'])
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.cli('finish', str(self.record), '--output', str(self.output), ok=False)
        self.assertFalse(self.output.exists())

    def test_unknown_model_and_absent_timing_do_not_block_complete_review(self):
        self.complete()
        before = self.record.read_bytes()
        self.cli('check', str(self.record), '--require-complete')
        result = self.cli('check', str(self.record), '--require-complete', '--require-diagnostics', ok=False)
        self.assertIn('Diagnostics incomplete', result.stderr)
        self.assertEqual(self.record.read_bytes(), before)

    def test_explicit_diagnostics_can_be_completed_without_claiming_host_delivery(self):
        self.run_dir = self.root / 'diagnostics'
        self.cli('start', '--repo', str(self.repo), '--base', self.base, '--head', self.head,
                 '--output', str(self.run_dir), '--diagnostics')
        self.record = self.run_dir / 'run.json'
        self.complete()
        end = dict(id='end', expected_revision=self.load()['revision'], actor='lead', note='Review completed',
            assessment=dict(lead=dict(id='lead', selection='current', model='gpt-6-astra', effort='xhigh',
                                     configuration_source='Test invocation', evidence_kind='invocation')),
            events=[dict(phase='review', state='complete', note='Verified pass saved')],
            milestones=[dict(name='lead_complete')])
        request = self.root / 'end.json'
        request.write_text(json.dumps(end))
        self.cli('checkpoint', str(self.record), '--input', str(request))
        output = self.cli('check', str(self.record), '--require-complete', '--require-diagnostics').stdout
        self.assertIn('end_to_end: unknown', output)
        self.assertNotIn('delivered', [row['name'] for row in self.load()['timing']['milestones']])

    def test_finish_collects_links_preserves_json_bytes_and_relocates(self):
        self.complete()
        (self.run_dir / 'evidence.md').write_text('## Limit\n[fixture](trace%231.json)\n[probe](probe.py)\n')
        fixture = b'{ invalid fixture\xff'
        (self.run_dir / 'trace#1.json').write_bytes(fixture)
        (self.run_dir / 'probe.py').write_text('assert 1 + 1 == 2\n')
        (self.run_dir / '.env').write_text('UNRELATED=not-an-artifact\n')
        (self.run_dir / 'unrelated.txt').write_text('Do not collect me\n')
        self.cli('finish', str(self.record), '--output', str(self.output))
        manifest = json.loads((self.output / 'archive.json').read_text())
        self.assertEqual({row['path'] for row in manifest['files']},
                         {'run.json', 'review-record.md', 'evidence.md', 'trace#1.json', 'probe.py'})
        self.assertEqual((self.output / 'files/trace#1.json').read_bytes(), fixture)
        shutil.rmtree(self.run_dir)
        moved = self.delivery_root / 'moved'
        self.output.rename(moved)
        with redirect_stdout(io.StringIO()):
            review_archive.check(moved)

    def test_start_invalid_refs_policy_and_existing_output_do_not_overwrite(self):
        before = self.record.read_bytes()
        self.cli('start', '--repo', str(self.repo), '--base', self.base, '--head', self.head,
                 '--output', str(self.run_dir), ok=False)
        self.assertEqual(self.record.read_bytes(), before)
        target = self.root / 'new'
        self.cli('start', '--repo', str(self.repo), '--base', self.base, '--head', 'absent-commit',
                 '--output', str(target), ok=False)
        self.assertFalse(target.exists())
        (self.repo / '.ai-skills.json').write_text('{broken')
        self.cli('start', '--repo', str(self.repo), '--base', self.base, '--head', self.head,
                 '--output', str(target), ok=False)
        self.assertFalse(target.exists())

    def test_project_preferences_are_captured_once_and_explicit_policy_wins(self):
        policy = {'schema_version': 1, 'models': {'lead': {'model': 'project-model', 'effort': 'high'}}}
        (self.repo / '.ai-skills.json').write_text(json.dumps(policy))
        target = self.root / 'configured'
        self.cli('start', '--repo', str(self.repo), '--base', self.base, '--head', self.head, '--output', str(target))
        saved = json.loads((target / 'run.json').read_text())['model_policy']
        self.assertEqual(review_policy.preferred_configuration({}, saved), ('project-model', 'high'))
        (self.repo / '.ai-skills.json').unlink()
        self.assertEqual(review_policy.preferred_configuration({}, saved), ('project-model', 'high'))
        explicit = self.root / 'explicit.json'
        explicit.write_text(json.dumps({'schema_version': 1, 'models': {}}))
        self.assertEqual(review_policy.load_policy(self.repo, explicit)['source'], str(explicit))
        self.assertEqual(review_policy.preferred_configuration(dict(user_override=dict(
            authority='explicit_user', model='user-model', effort='low', source='Direct request')), saved),
            ('user-model', 'low'))

    def test_invalid_or_stale_evidence_updates_leave_record_unchanged(self):
        self.complete()
        before = self.record.read_bytes()
        self.cli('record', str(self.record), '--path', 'logic.py', '--status', 'reviewed', '--unit', 'R1',
                 '--evidence-file', 'missing.md', '--locator', 'L', '--claim', 'C', ok=False)
        self.cli('record', str(self.record), '--path', 'logic.py', '--status', 'partial',
                 '--expected-revision', '0', ok=False)
        self.assertEqual(self.record.read_bytes(), before)

    def test_finish_refuses_missing_forbidden_and_outside_evidence(self):
        self.complete()
        for dest in ('missing.md', '.env', '../evidence.md'):
            (self.run_dir / '.env').write_text('PRIVATE=fixture\n')
            (self.run_dir / 'evidence.md').write_text(f'[required]({dest})\n')
            self.cli('finish', str(self.record), '--output', str(self.output), ok=False)
            self.assertFalse(self.output.exists())

    def test_finish_refuses_replacing_archive_and_preserves_run(self):
        self.complete()
        self.cli('finish', str(self.record), '--output', str(self.output))
        before, archive = self.record.read_bytes(), (self.output / 'archive.json').read_bytes()
        self.cli('finish', str(self.record), '--output', str(self.output), ok=False)
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual((self.output / 'archive.json').read_bytes(), archive)

    def test_failed_start_cleans_only_its_new_folder(self):
        target = self.root / 'failed'
        with patch('review_lifecycle.save_new', side_effect=OSError('simulated disk failure')):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(review_run.main(['start', '--repo', str(self.repo), '--base', self.base,
                    '--head', self.head, '--output', str(target)]), 1)
        self.assertFalse(target.exists())
        self.assertTrue(self.record.exists())

    def test_absent_lead_or_unresolved_deep_work_still_blocks_completion(self):
        self.complete()
        data = self.load()
        data['lead'] = None
        self.save(data)
        self.assertIn('lead identity', self.cli('check', str(self.record), '--require-complete', ok=False).stderr)
        data['lead'] = {'id': 'lead'}
        data['depth'] = {'level': 'deep', 'reason': 'Interacting behavior needs challenge'}
        self.save(data)
        self.assertIn('critical boundaries', self.cli('check', str(self.record), '--require-complete', ok=False).stderr)


if __name__ == '__main__':
    unittest.main()

"""Real local snapshots exercise atomic passes, lifecycle and same-schema fallback."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import review_checkpoint
import review_environment
import review_run
from review_coverage import CoverageError
import test_review_run as legacy


class CheckpointCases(unittest.TestCase):
    # Reuse fixture utilities without inheriting and rerunning legacy test cases.
    git = legacy.RunCases.git
    commit = legacy.RunCases.commit
    coverage_cli = legacy.RunCases.coverage_cli
    cli = legacy.RunCases.cli
    load = legacy.RunCases.load
    save = legacy.RunCases.save
    citation = legacy.RunCases.citation
    check = legacy.RunCases.check
    investigation = legacy.RunCases.investigation

    def setUp(self):
        legacy.RunCases.setUp(self)
        self.legacy = self.record
        self.record = self.root / 'canonical.json'
        self.cli('begin', '--output', str(self.record), '--owner', 'lead', '--role', 'lead',
                 '--skill-root', str(self.skill))
        seed = json.loads(self.coverage.read_text())
        seed['files'][0].update(status='unreviewed', units=[], evidence=[])
        seed['integration'].update(status='unreviewed', evidence=[])
        self.coverage.write_text(json.dumps(seed))
        self.request(dict(id='scope', expected_revision=0, actor='lead', note='Scope established',
            coverage=[dict(id='service', **{'import': 'coverage.json'})],
            assessment=dict(mode='light', selection_reason='Bounded limit change',
                depth=dict(level='standard', reason='Actual consumer traced'),
                lead=dict(id='lead', selection='current', model='gpt-6-astra', effort='xhigh',
                          configuration_source='test invocation', evidence_kind='invocation')),
            environments=[dict(id='source', status='source_only', purpose='Inspect limit consumer',
                               reason='Source trace resolves exact constant behavior', runtime=None, evidence=[])]))

    def request(self, data, ok=True, complete=False):
        target = self.root / 'checkpoint.json'
        target.write_text(json.dumps(data))
        return self.cli('checkpoint', str(self.record), '--input', str(target),
                        *(['--require-complete'] if complete else []), ok=ok)

    def completion(self):
        return dict(id='pass-1', expected_revision=self.load()['revision'], actor='lead',
            note='Verified file and integration evidence',
            coverage=[dict(id='service',
                files=[dict(path='logic.py', units=['R1'], status='reviewed',
                            evidence=[self.citation()], notes='')],
                integration=dict(status='reviewed', evidence=[self.citation()], notes=''))],
            events=[dict(phase='review', state='complete', note='Verified trace saved')],
            milestones=[dict(name='lead_complete')])

    def test_whole_pass_commits_once_and_seed_remains_historical(self):
        seed = self.coverage.read_bytes()
        self.request(self.completion(), complete=True)
        self.check()
        self.assertEqual(self.load()['revision'], 2)
        self.assertEqual(self.load()['coverage'][0]['record']['files'][0]['status'], 'reviewed')
        self.assertEqual(self.coverage.read_bytes(), seed)
        self.assertEqual(len(self.load()['events']), 2)

    def test_import_and_verified_dispositions_can_share_one_atomic_checkpoint(self):
        other = self.root / 'combined.json'
        self.cli('begin', '--output', str(other), '--owner', 'lead', '--role', 'lead',
                 '--skill-root', str(self.skill))
        self.record = other
        seed = self.coverage.read_bytes()
        request = self.completion()
        request['coverage'][0]['import'] = 'coverage.json'
        self.request(request)
        self.assertEqual(self.load()['coverage'][0]['record']['files'][0]['status'], 'reviewed')
        self.assertEqual(self.coverage.read_bytes(), seed)

    def test_import_with_invalid_disposition_commits_nothing(self):
        other = self.root / 'invalid-combined.json'
        self.cli('begin', '--output', str(other), '--owner', 'lead', '--role', 'lead',
                 '--skill-root', str(self.skill))
        self.record = other; before = other.read_bytes()
        request = self.completion()
        request['coverage'][0]['import'] = 'coverage.json'
        request['coverage'][0]['files'][0]['evidence'][0]['path'] = 'missing.md'
        self.request(request, ok=False)
        self.assertEqual(other.read_bytes(), before)

    def test_identical_retry_is_noop_even_after_another_checkpoint(self):
        final = self.completion()
        self.request(final)
        self.request(dict(id='ready', expected_revision=2, actor='coordinator', note='Report ready',
                          milestones=[dict(name='delivery_ready')]))
        before = self.record.read_bytes()
        self.assertIn('already committed', self.request(final, complete=True).stdout)
        self.assertEqual(before, self.record.read_bytes())
        changed = deepcopy(final); changed['note'] = 'Different content'
        self.assertIn('reused', self.request(changed, ok=False).stderr)
        self.assertEqual(before, self.record.read_bytes())

    def test_stale_or_identity_changing_updates_leave_everything_unchanged(self):
        before = self.record.read_bytes()
        for update in [
            dict(self.completion(), expected_revision=0),
            dict(self.completion(), installed_skill_snapshot=[]),
            dict(self.completion(), coverage=[dict(id='service', **{'import': 'coverage.json'})]),
            dict(self.completion(), coverage=[dict(id='service', snapshot={})]),
        ]:
            self.request(update, ok=False)
            self.assertEqual(before, self.record.read_bytes())

    def test_invalid_evidence_does_not_partially_close_phase_or_mark_file(self):
        request = self.completion()
        request['coverage'][0]['files'][0]['evidence'][0]['path'] = 'missing.md'
        before = self.record.read_bytes()
        self.request(request, ok=False)
        self.assertEqual(before, self.record.read_bytes())

    def test_failed_atomic_replace_keeps_all_state_and_can_resume(self):
        request = self.completion()
        target = self.root / 'checkpoint.json'; target.write_text(json.dumps(request))
        before = self.record.read_bytes()
        with patch('review_coverage.os.replace', side_effect=OSError('simulated I/O failure')), redirect_stdout(io.StringIO()):
            self.assertEqual(review_run.main(['checkpoint', str(self.record), '--input', str(target)]), 1)
        self.assertEqual(before, self.record.read_bytes())
        self.assertEqual(list(self.root.glob('.canonical.json.*')), [])
        self.request(request, complete=True)

    def test_active_writer_is_rejected_and_os_lock_can_be_reused(self):
        before = self.record.read_bytes()
        with review_checkpoint.writer_lock(self.record):
            self.assertIn('writer is active', self.request(self.completion(), ok=False).stderr)
        self.assertEqual(before, self.record.read_bytes())
        self.request(self.completion(), complete=True)

    def test_deep_pass_saves_hypotheses_with_coverage_and_missing_challenge_stays_partial(self):
        request = self.completion()
        request['assessment'] = dict(mode='full', depth=dict(level='deep', reason='Interacting effect boundary'))
        request['boundaries'] = [dict(id='B1', contract='Admission limit enforced', paths=['logic.py'])]
        request['investigations'] = [self.investigation()]
        before = self.record.read_bytes()
        self.assertIn('missing resolved challenge', self.request(request, ok=False, complete=True).stderr)
        self.assertEqual(before, self.record.read_bytes())
        request['investigations'].append(self.investigation('H2', 'challenge', 'R2'))
        self.request(request, complete=True)

    def test_partial_completion_time_does_not_close_unreviewed_coverage(self):
        request = self.completion(); request.pop('coverage')
        self.request(request)
        result = self.check(ok=False)
        self.assertIn('coverage incomplete', result.stderr)
        self.assertNotIn('lifecycle endpoint missing: lead_complete', result.stderr)

    def test_unknown_lead_end_is_not_near_zero_or_host_delivery(self):
        request = self.completion()
        request['milestones'] = [dict(name='lead_complete', unknown_time=True, source='Earlier handoff was unmeasured')]
        self.request(request, complete=True)
        output = self.check().stdout
        self.assertIn('lead_execution: unknown', output)
        self.assertIn('end_to_end: unknown', output)
        before = self.record.read_bytes()
        self.request(dict(id='delivery', expected_revision=2, actor='coordinator',
                          note='Cannot predict UI delivery', milestones=[dict(name='delivered')]), ok=False)
        self.assertEqual(before, self.record.read_bytes())

    def test_bootstrap_coordinator_precedes_lead_and_rejects_legacy_mutators(self):
        other = self.root / 'coordinator.json'
        self.cli('begin', '--output', str(other), '--owner', 'coordinator', '--role', 'coordinator')
        data = json.loads(other.read_text())
        self.assertEqual([r['name'] for r in data['timing']['milestones']], ['intake'])
        self.assertEqual(data['events'][0]['phase'], 'intake')
        before = self.record.read_bytes()
        self.cli('event', str(self.record), '--owner', 'lead', '--phase', 'review', '--state', 'complete',
                 '--note', 'Wrong mutator', ok=False)
        self.assertEqual(before, self.record.read_bytes())

    def test_late_bootstrap_preserves_unknown_intake_and_lead_start(self):
        other = self.root / 'late-start.json'
        self.cli('begin', '--output', str(other), '--owner', 'lead', '--role', 'lead',
                 '--intake-unknown', '--intake-source', 'Earlier request time unavailable',
                 '--lead-unknown', '--lead-source', 'Lead had already read context')
        data = json.loads(other.read_text())
        self.assertEqual([p['at'] for p in data['timing']['milestones']], [None, None])
        self.assertEqual([p['basis'] for p in data['timing']['milestones']], ['unknown', 'unknown'])
        self.assertEqual(data['events'][0]['basis'], 'observed')
        self.assertIn('lead_execution: unknown', self.cli('check', str(other)).stdout)

    def test_manual_fallback_uses_same_validator_and_cannot_hide_gaps(self):
        self.request(self.completion(), complete=True)
        data = self.load()
        template = json.loads((Path(review_run.__file__).parent.parent / 'assets/run-record-template.json').read_text())
        template.update(data)
        template.update(revision=0, checkpoints=[],
                        recording=dict(method='manual', reason='Helper unavailable during recorded pass; prior bytes preserved'))
        fallback = self.root / 'manual.json'; fallback.write_text(json.dumps(template))
        result = self.cli('check', str(fallback), '--require-complete')
        self.assertIn('Manual fallback', result.stdout)
        template['coverage'][0]['record']['integration'].update(status='unreviewed', evidence=[])
        fallback.write_text(json.dumps(template))
        self.cli('check', str(fallback), '--require-complete', ok=False)

    def test_promote_keeps_versions_timing_original_bytes_and_rebases_evidence(self):
        before = self.legacy.read_bytes()
        folder = self.root / 'moved'; folder.mkdir()
        target = folder / 'run.json'
        self.cli('promote', str(self.legacy), '--output', str(target))
        data = json.loads(target.read_text())
        original = json.loads(before)
        self.assertEqual(data['timing'], original['timing'])
        self.assertEqual(data['installed_skill_snapshot'], original['installed_skill_snapshot'])
        self.assertEqual(before, self.legacy.read_bytes())
        self.assertEqual(data['coverage'][0]['snapshot'], original['coverage'][0]['snapshot'])
        self.cli('promote', str(self.legacy), '--output', str(target), ok=False)

    def test_ready_rejects_mismatch_and_limited_preserves_qualification(self):
        probe = dict(schema_version=1, executable=sys.executable, requirement='Python supported by project',
                     requirement_source=self.head + ':runtime config', expected='Python 99.0',
                     observed='Python 3.9.6', returncode=0, alignment='mismatched',
                     checked_at='2026-01-01T12:00:00+00:00')
        (self.root / 'runtime.json').write_text(json.dumps(probe))
        row = dict(id='execution', status='ready', purpose='Run focused tests', reason='Selected project runtime',
                   runtime=dict(path='runtime.json', locator='observed', claim='Version probe'),
                   evidence=[self.citation()])
        request = self.completion(); request['environments'] = [row]
        self.request(request, ok=False)
        row.update(status='limited', reason='Supported runtime unavailable; alternative checks are qualified')
        self.request(request, complete=True)
        self.assertIn('no runtime-equivalence claim', self.check().stdout)

    def repair_request(self):
        return dict(id='relocate-1', expected_revision=self.load()['revision'],
                    actor='lead', note='Retained evidence moved to a durable path',
                    relocations=[dict(from_path='evidence.md', to_path='moved.md',
                        sha256=hashlib.sha256((self.root / 'moved.md').read_bytes()).hexdigest(),
                        identity_source='Retained byte-identical evidence backup')])

    def repair(self, request, ok=True):
        target = self.root / 'repair-request.json'; target.write_text(json.dumps(request))
        return self.cli('repair-evidence', str(self.record), '--input', str(target), ok=ok)

    def test_explicit_missing_pointer_repair_preserves_history_and_source_identities(self):
        self.request(self.completion(), complete=True)
        before = self.record.read_bytes(); original = self.load()
        self.evidence.rename(self.root / 'moved.md')
        self.check(ok=False)
        self.request(dict(id='ordinary', expected_revision=2, actor='lead', note='Still missing'), ok=False)
        self.assertEqual(self.record.read_bytes(), before)
        request = self.repair_request(); self.repair(request)
        updated = self.load()
        self.assertEqual(updated['checkpoints'][:-1], original['checkpoints'])
        self.assertEqual(updated['installed_skill_snapshot'], original['installed_skill_snapshot'])
        self.assertEqual(updated['coverage'][0]['snapshot'], original['coverage'][0]['snapshot'])
        entry = updated['coverage'][0]['record']['files'][0]['evidence'][0]
        self.assertEqual(entry['locator'], self.citation()['locator'])
        self.assertEqual(entry['claim'], self.citation()['claim'])
        self.assertEqual(entry['path'], str((self.root / 'moved.md').resolve()))
        history = updated['evidence_repairs'][0]
        self.assertEqual(Path(history['previous_record']).read_bytes(), before)
        self.assertEqual(history['previous_sha256'], hashlib.sha256(before).hexdigest())
        self.check()
        after = self.record.read_bytes()
        self.repair(request)
        self.assertEqual(self.record.read_bytes(), after)
        self.repair(dict(request, note='Different content'), ok=False)
        self.assertEqual(self.record.read_bytes(), after)

    def test_repair_rejects_stale_mismatched_unused_and_identity_edits_without_write(self):
        self.request(self.completion(), complete=True)
        self.evidence.rename(self.root / 'moved.md')
        request = self.repair_request()
        bad_hash = deepcopy(request); bad_hash['relocations'][0]['sha256'] = '0' * 64
        unused = deepcopy(request); unused['relocations'][0]['from_path'] = 'never-referenced.md'
        for value in [dict(request, expected_revision=0), bad_hash, unused, dict(request, snapshot={})]:
            before = self.record.read_bytes()
            self.repair(value, ok=False)
            self.assertEqual(self.record.read_bytes(), before)
        data = self.load()
        data['coverage'][0]['record']['files'][0]['change'] = 'A'
        self.save(data); before = self.record.read_bytes()
        self.repair(request, ok=False)
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(list(self.root.glob('canonical.json.before-repair-*')), [])

    def test_repair_failed_replace_retains_original_and_backup_then_retries(self):
        self.request(self.completion(), complete=True)
        self.evidence.rename(self.root / 'moved.md')
        request = self.repair_request()
        target = self.root / 'repair.json'; target.write_text(json.dumps(request))
        before = self.record.read_bytes()
        with patch('review_coverage.os.replace', side_effect=OSError('disk error')), redirect_stdout(io.StringIO()):
            self.assertEqual(review_run.main(['repair-evidence', str(self.record), '--input', str(target)]), 1)
        self.assertEqual(self.record.read_bytes(), before)
        backup, = self.root.glob('canonical.json.before-repair-*')
        self.assertEqual(backup.read_bytes(), before)
        self.repair(request)
        self.check()

    def test_repeated_move_is_supported_but_cyclic_history_is_rejected(self):
        self.request(self.completion(), complete=True)
        self.evidence.rename(self.root / 'moved.md')
        first = self.repair_request(); self.repair(first)
        (self.root / 'moved.md').rename(self.root / 'final.md')
        second = deepcopy(first)
        second.update(id='relocate-2', expected_revision=self.load()['revision'])
        second['relocations'][0].update(from_path='moved.md', to_path='final.md')
        self.repair(second); self.check()
        (self.root / 'final.md').rename(self.evidence)
        cycle = deepcopy(first)
        cycle.update(id='relocate-3', expected_revision=self.load()['revision'])
        cycle['relocations'][0].update(from_path='final.md', to_path='evidence.md')
        before = self.record.read_bytes()
        self.assertIn('Cyclic', self.repair(cycle, ok=False).stderr)
        self.assertEqual(self.record.read_bytes(), before)

    def test_existing_original_content_mismatch_cannot_be_replaced_as_relocation(self):
        self.request(self.completion(), complete=True)
        (self.root / 'moved.md').write_bytes(self.evidence.read_bytes())
        request = self.repair_request()
        self.evidence.write_text('Different current contents')
        before = self.record.read_bytes()
        self.assertIn('original evidence does not match', self.repair(request, ok=False).stderr)
        self.assertEqual(self.record.read_bytes(), before)

    def test_repaired_run_and_preserved_history_archive_after_scratch_deletion(self):
        import review_archive
        self.request(self.completion(), complete=True)
        original = self.record.read_bytes()
        self.evidence.rename(self.root / 'moved.md')
        self.repair(self.repair_request())
        backup = Path(self.load()['evidence_repairs'][0]['previous_record']).name
        (self.root / 'report.md').write_text('[Evidence](moved.md "Verified trace")\n')
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            destination = Path(folder) / 'archive'
            with redirect_stdout(io.StringIO()):
                review_archive.create(self.root, destination, self.record.name,
                                      'report.md', ['moved.md', backup])
            self.assertEqual((destination / 'originals' / backup).read_bytes(), original)
            shutil.rmtree(self.root)
            moved = Path(folder) / 'relocated'; destination.rename(moved)
            with redirect_stdout(io.StringIO()):
                review_archive.check(moved)

    def test_archive_rejects_path_reuse_after_a_valid_fresh_checkpoint(self):
        import review_archive
        self.request(self.completion(), complete=True)
        self.evidence.rename(self.root / 'moved.md')
        self.repair(self.repair_request())
        backup = Path(self.load()['evidence_repairs'][0]['previous_record'])
        backup_bytes = backup.read_bytes()
        report = self.root / 'report.md'
        report.write_text('[Earlier evidence](moved.md)\n')
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            previous = Path(folder) / 'previous-archive'
            with redirect_stdout(io.StringIO()):
                review_archive.create(self.root, previous, self.record.name,
                                      'report.md', ['moved.md', backup.name])
            archive_bytes = {p.relative_to(previous): p.read_bytes()
                             for p in previous.rglob('*') if p.is_file()}
            self.evidence.write_text('## New pass\nDifferent evidence from the new pass.\n')
            fresh = dict(path='evidence.md', locator='New pass', claim='New pass verified different behavior')
            self.request(dict(id='fresh-pass', expected_revision=self.load()['revision'],
                actor='lead', note='New evidence recorded at the reused pathname',
                coverage=[dict(id='service', files=[dict(path='logic.py', units=['R1'],
                    status='reviewed', evidence=[fresh], notes='')])]), complete=True)
            self.check()
            report.write_text('[New evidence](evidence.md#new-pass "New pass")\n')
            before = self.record.read_bytes()
            report_bytes = report.read_bytes()
            output = Path(folder) / 'new-archive'
            with self.assertRaisesRegex(CoverageError, 'Ambiguous relocation'):
                review_archive.create(self.root, output, self.record.name, 'report.md',
                                      ['evidence.md', 'moved.md', backup.name])
            self.assertFalse(output.exists())
            self.assertEqual(self.record.read_bytes(), before)
            self.assertEqual(backup.read_bytes(), backup_bytes)
            self.assertEqual(report.read_bytes(), report_bytes)
            self.assertEqual(self.load()['coverage'][0]['record']['files'][0]['evidence'], [fresh])
            self.assertEqual({p.relative_to(previous): p.read_bytes()
                              for p in previous.rglob('*') if p.is_file()}, archive_bytes)


class RuntimeCases(unittest.TestCase):
    def test_actual_runtime_probe_and_mismatch_are_preserved(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'runtime.json'
            version = subprocess.check_output([sys.executable, '--version'], text=True).strip()
            args = ['--executable', sys.executable, '--requirement', 'Python used by this fixture',
                    '--requirement-source', 'fixture runtime pin', '--expected', version, '--output', str(path)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(review_environment.main(args), 0)
                self.assertTrue(review_environment.inspect_probe(json.loads(path.read_text())))
                old = path.read_bytes()
                self.assertEqual(review_environment.main(args), 1)
                self.assertEqual(path.read_bytes(), old)
                args[-1] = str(Path(folder) / 'mismatch.json')
                args[args.index('--expected') + 1] = 'Python 99.0'
                self.assertEqual(review_environment.main(args), 2)
                self.assertFalse(review_environment.inspect_probe(json.loads(Path(args[-1]).read_text())))


if __name__ == '__main__':
    unittest.main(verbosity=2)

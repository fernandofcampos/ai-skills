#!/usr/bin/env python3
"""Behavioral CLI tests using isolated real Git repositories; no network access."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('review_coverage.py')


class CoverageCases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Coverage Test')
        self.git('config', 'user.email', 'coverage@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.write('old name.txt', 'A stable file to rename.\n' * 4)
        self.write('remove.txt', 'obsolete\n')
        self.write('logic.py', 'LIMIT = 1\n')
        self.base = self.commit('base')
        self.git('mv', 'old name.txt', 'new name.txt')
        (self.repo / 'remove.txt').unlink()
        self.write('logic.py', 'LIMIT = 2\n')
        self.write('config.json', '{"enabled": true}\n')
        self.write('odd\tname\nλ.txt', 'path escaping\n')
        (self.repo / 'asset.bin').write_bytes(b'\x00\x80\xff\x01')
        self.head = self.commit('feature')
        self.record = self.root / 'coverage.json'
        self.good(self.run_cli('init', '--output', str(self.record)))

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.repo), *args],
                                capture_output=True, check=True)
        return result.stdout.decode().strip()

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def run_cli(self, command, *args, base=None, head=None):
        result = subprocess.run([
            sys.executable, str(SCRIPT), command, *args,
            '--repo', str(self.repo), '--base', base or self.base,
            '--head', head or self.head,
        ], capture_output=True, text=True, check=False)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def check(self, *args, **kwargs):
        return self.run_cli('check', str(self.record), *args, **kwargs)

    def load(self):
        return json.loads(self.record.read_text())

    def save(self, data):
        self.record.write_text(json.dumps(data), encoding='utf-8')

    def finish(self):
        data = self.load()
        for row in data['files']:
            row.update(status='reviewed', units=['R1'],
                       evidence=['Review record R1: inspected base/head and callers.'])
        data['integration'].update(status='reviewed',
                                   evidence=['Review record S1: code trace at head.'])
        self.save(data)
        return data

    def checkpoint(self, *args, **kwargs):
        return self.run_cli('record', str(self.record), *args, **kwargs)

    def local_evidence(self):
        path = self.root / 'handoffs' / 'r1.md'
        path.parent.mkdir(exist_ok=True)
        path.write_text('## S1\nChecked logic.py LIMIT change and its consumer.\n')
        return {'path': 'handoffs/r1.md', 'locator': 'S1 / LIMIT',
                'claim': 'Consumer accepts the new limit at the reviewed head.'}

    def good(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def bad(self, result, message):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stdout + result.stderr)

    def test_complete_inventory_handles_rename_delete_binary_and_unusual_paths(self):
        data = self.load()
        rows = {r['path']: r for r in data['files']}
        self.assertEqual(set(rows), {'new name.txt', 'remove.txt', 'logic.py',
                                    'config.json', 'odd\tname\nλ.txt', 'asset.bin'})
        self.assertEqual(rows['new name.txt']['old_path'], 'old name.txt')
        self.assertEqual(rows['new name.txt']['change'], 'R100')
        self.assertEqual(rows['remove.txt']['change'], 'D')
        self.good(self.check())

    def test_unfinished_is_resumable_but_cannot_claim_full_coverage(self):
        result = self.check()
        self.good(result)
        self.assertIn('coverage incomplete', result.stdout)
        self.bad(self.check('--require-complete'), 'Coverage incomplete')

    def test_completed_file_and_integration_records_pass(self):
        self.finish()
        self.good(self.check('--require-complete'))

    def test_missing_file_is_rejected(self):
        data = self.finish()
        data['files'].pop()
        self.save(data)
        self.bad(self.check(), 'Missing coverage paths')

    def test_extra_file_is_rejected(self):
        data = self.load()
        data['files'].append(dict(data['files'][0], path='invented.py'))
        self.save(data)
        self.bad(self.check(), 'Unexpected coverage path')

    def test_duplicate_file_cannot_cover_an_omission(self):
        data = self.load()
        data['files'][-1] = data['files'][0]
        self.save(data)
        self.bad(self.check(), 'Duplicate coverage path')

    def test_rename_source_is_verified(self):
        data = self.load()
        next(r for r in data['files'] if r['old_path'])['old_path'] = 'wrong.txt'
        self.save(data)
        self.bad(self.check(), 'metadata mismatch')

    def test_reviewed_requires_evidence_and_unit(self):
        data = self.finish()
        data['files'][0]['evidence'] = []
        self.save(data)
        self.bad(self.check(), 'reviewed requires evidence')
        data['files'][0]['evidence'] = ['record R1']
        data['files'][0]['units'] = []
        self.save(data)
        self.bad(self.check(), 'requires unit IDs')

    def test_blank_evidence_and_invalid_status_are_rejected(self):
        data = self.finish()
        data['files'][0]['evidence'] = [' ']
        self.save(data)
        self.bad(self.check(), 'nonempty strings')
        data['files'][0]['evidence'] = ['record R1']
        data['files'][0]['status'] = 'approved'
        self.save(data)
        self.bad(self.check(), 'invalid review status')

    def test_exclusion_requires_reason_and_prevents_full_coverage(self):
        data = self.finish()
        data['files'][0].update(status='excluded', notes='')
        self.save(data)
        self.bad(self.check(), 'requires a rationale')
        data['files'][0]['notes'] = 'Outside explicitly requested subset.'
        self.save(data)
        self.good(self.check())
        self.bad(self.check('--require-complete'), 'Coverage incomplete')

    def test_integration_is_required_even_if_files_are_reviewed(self):
        data = self.finish()
        data['integration']['status'] = 'partial'
        self.save(data)
        self.bad(self.check('--require-complete'), 'Coverage incomplete')
        data['integration'].update(status='not_applicable', notes='')
        self.save(data)
        self.bad(self.check(), 'requires a rationale')
        data['integration']['notes'] = 'Example justification; quality is a manual check.'
        self.save(data)
        self.good(self.check('--require-complete'))

    def test_new_head_invalidates_review(self):
        self.finish()
        self.write('logic.py', 'LIMIT = 3\n')
        new_head = self.commit('update')
        self.bad(self.check(head=new_head), 'Snapshot mismatch')

    def test_moving_target_base_invalidates_even_if_merge_base_is_same(self):
        self.finish()
        self.git('checkout', '-q', '--detach', self.base)
        self.write('unrelated.txt', 'target branch update\n')
        new_base = self.commit('base update')
        self.assertEqual(self.git('merge-base', new_base, self.head), self.base)
        self.bad(self.check(base=new_base), 'Snapshot mismatch')

    def test_uses_merge_base_not_target_tip_for_diverged_branches(self):
        self.git('checkout', '-q', '--detach', self.base)
        self.write('base-only.txt', 'unrelated target change\n')
        new_base = self.commit('target update')
        self.record = self.root / 'diverged.json'
        self.good(self.run_cli('init', '--output', str(self.record), base=new_base))
        self.assertEqual(self.load()['snapshot']['comparison_base'], self.base)
        self.assertNotIn('base-only.txt', [r['path'] for r in self.load()['files']])
        self.good(self.check(base=new_base))

    def test_dirty_and_untracked_files_are_preserved_and_not_attributed_to_head(self):
        self.write('logic.py', 'uncommitted change\n')
        self.write('private-local.txt', 'untracked\n')
        before = self.git('status', '--porcelain')
        self.good(self.check())
        self.assertEqual(self.git('status', '--porcelain'), before)
        self.assertEqual((self.repo / 'logic.py').read_text(), 'uncommitted change\n')
        self.assertNotIn('private-local.txt', [r['path'] for r in self.load()['files']])

    def test_existing_record_cannot_be_overwritten(self):
        before = self.record.read_bytes()
        self.bad(self.run_cli('init', '--output', str(self.record)), 'File exists')
        self.assertEqual(self.record.read_bytes(), before)

    def test_malformed_records_fail_without_tracebacks(self):
        for value in ('{', '[]', '{"schema_version": true}'):
            with self.subTest(value=value):
                self.record.write_text(value)
                result = self.check()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)

    def test_missing_repository_or_ref_fails_without_a_record(self):
        output = self.root / 'bad.json'
        self.bad(self.run_cli('init', '--output', str(output), head='absent-ref'), 'Git failed')
        self.assertFalse(output.exists())

    def test_submodule_pointer_change_is_inventoried(self):
        self.git('update-index', '--add', '--cacheinfo', f'160000,{self.base},vendor')
        self.git('commit', '-qm', 'add submodule pointer')
        sub_base = self.git('rev-parse', 'HEAD')
        self.git('update-index', '--cacheinfo', f'160000,{self.head},vendor')
        self.git('commit', '-qm', 'update submodule pointer')
        sub_head = self.git('rev-parse', 'HEAD')
        self.git('config', 'diff.ignoreSubmodules', 'all')
        self.git('config', 'submodule.vendor.ignore', 'all')
        self.assertEqual(self.git('diff', '--name-only', sub_base, sub_head), '')
        self.record = self.root / 'submodule.json'
        self.good(self.run_cli('init', '--output', str(self.record), base=sub_base, head=sub_head))
        self.assertEqual([r['path'] for r in self.load()['files']], ['vendor'])
        self.good(self.check(base=sub_base, head=sub_head))

    def test_empty_diff_still_requires_explicit_integration_disposition(self):
        self.record = self.root / 'empty.json'
        self.good(self.run_cli('init', '--output', str(self.record), head=self.base))
        self.bad(self.check('--require-complete', head=self.base), 'Coverage incomplete')
        data = self.load()
        data['integration'].update(status='not_applicable', notes='No committed changes.')
        self.save(data)
        self.good(self.check('--require-complete', head=self.base))

    def test_multiple_merge_bases_are_explicitly_unsupported(self):
        tree = self.git('rev-parse', self.base + '^{tree}')
        left = self.git('commit-tree', tree, '-p', self.base, '-m', 'left')
        right = self.git('commit-tree', tree, '-p', self.base, '-m', 'right')
        first = self.git('commit-tree', tree, '-p', left, '-p', right, '-m', 'first merge')
        second = self.git('commit-tree', tree, '-p', right, '-p', left, '-m', 'second merge')
        output = self.root / 'ambiguous.json'
        self.bad(self.run_cli('init', '--output', str(output), base=first, head=second),
                 'unique merge base is required')
        self.assertFalse(output.exists())

    def test_repository_path_preserves_trailing_spaces(self):
        new_path = self.root / 'repository with spaces '
        self.repo.rename(new_path)
        self.repo = new_path
        self.record = self.root / 'spaces.json'
        self.good(self.run_cli('init', '--output', str(self.record)))
        self.assertEqual(self.load()['snapshot']['repo_root'], str(new_path.resolve()))
        self.good(self.check())

    def test_precise_evidence_resolves_relative_to_record_not_cwd(self):
        data = self.finish()
        data['files'][0]['evidence'] = [self.local_evidence()]
        self.save(data)
        self.good(self.check('--require-complete'))

    def test_absolute_evidence_and_legacy_strings_can_be_mixed(self):
        data = self.finish()
        citation = self.local_evidence()
        citation['path'] = str(self.root / citation['path'])
        data['integration']['evidence'] = [citation, 'Remote ticket read recorded in narrative.']
        self.save(data)
        self.good(self.check('--require-complete'))

    def test_missing_evidence_file_or_directory_is_rejected(self):
        data = self.finish()
        citation = self.local_evidence()
        for path in ('missing.md', 'handoffs'):
            with self.subTest(path=path):
                data['files'][0]['evidence'] = [dict(citation, path=path)]
                self.save(data)
                self.bad(self.check(), 'evidence file does not exist')

    def test_malformed_evidence_objects_are_rejected(self):
        data = self.finish()
        citation = self.local_evidence()
        for value in (None, 1, {}, {'path': citation['path']}, dict(citation, claim=' '),
                      dict(citation, locator=42), dict(citation, extra='unknown')):
            with self.subTest(value=value):
                data['files'][0]['evidence'] = [value]
                self.save(data)
                self.bad(self.check(), 'evidence')

    def test_checkpoint_changes_only_requested_review_fields(self):
        before = self.load()
        before['extra_context'] = {'ticket': 'Read by the lead'}
        self.save(before)
        citation = self.local_evidence()
        self.good(self.checkpoint('--path', 'logic.py', '--status', 'reviewed', '--unit', 'R1',
                                  '--evidence-file', citation['path'], '--locator', citation['locator'],
                                  '--claim', citation['claim'], '--notes', 'Verified S1'))
        expected = json.loads(json.dumps(before))
        row = next(r for r in expected['files'] if r['path'] == 'logic.py')
        row.update(status='reviewed', units=['R1'], evidence=[citation], notes='Verified S1')
        self.assertEqual(self.load(), expected)
        self.bad(self.check('--require-complete'), 'Coverage incomplete')

    def test_checkpoint_reopens_file_and_can_replace_missing_old_evidence(self):
        self.finish()
        self.good(self.checkpoint('--path', 'logic.py', '--status', 'partial', '--unit', 'R1',
                                  '--notes', 'Need cold-start trace'))
        data = self.load()
        row = next(r for r in data['files'] if r['path'] == 'logic.py')
        self.assertEqual(row['evidence'], [])
        row['evidence'] = [dict(self.local_evidence(), path='removed-artifact.md')]
        self.save(data)
        self.good(self.checkpoint('--path', 'logic.py', '--status', 'reviewed', '--unit', 'R1',
                                  '--evidence', 'record R1: replacement trace'))
        self.good(self.check('--require-complete'))

    def test_integration_checkpoint_and_not_applicable_rationale(self):
        self.finish()
        before = self.record.read_bytes()
        self.bad(self.checkpoint('--integration', '--status', 'not_applicable'), 'requires a rationale')
        self.assertEqual(self.record.read_bytes(), before)
        self.good(self.checkpoint('--integration', '--status', 'not_applicable', '--notes',
                                  'No runtime integration in this bounded example.'))
        self.good(self.check('--require-complete'))
        self.good(self.checkpoint('--integration', '--status', 'reviewed', '--evidence', 'record S1'))
        self.good(self.check('--require-complete'))

    def test_invalid_checkpoint_leaves_record_byte_identical(self):
        before = self.record.read_bytes()
        cases = [
            (['--path', 'absent.py', '--status', 'unreviewed'], 'target is absent'),
            (['--path', 'logic.py', '--status', 'reviewed'], 'requires evidence'),
            (['--path', 'logic.py', '--status', 'not_applicable'], 'invalid review status'),
            (['--integration', '--status', 'excluded'], 'invalid review status'),
            (['--integration', '--status', 'unreviewed', '--unit', 'R1'], 'do not take unit'),
            (['--path', 'logic.py', '--status', 'partial', '--unit', 'R1',
              '--evidence-file', 'missing.md'], 'together'),
            (['--path', 'logic.py', '--status', 'reviewed', '--unit', 'R1',
              '--evidence-file', 'missing.md', '--locator', 'S1', '--claim', 'trace'],
             'evidence file does not exist'),
        ]
        for args, message in cases:
            with self.subTest(args=args):
                self.bad(self.checkpoint(*args), message)
                self.assertEqual(self.record.read_bytes(), before)

    def test_stale_checkpoint_cannot_carry_coverage_to_new_head(self):
        before = self.record.read_bytes()
        self.write('logic.py', 'LIMIT = 3\n')
        head = self.commit('later update')
        self.bad(self.checkpoint('--path', 'logic.py', '--status', 'unreviewed', head=head),
                 'Snapshot mismatch')
        self.assertEqual(self.record.read_bytes(), before)

    def test_checkpoint_rejects_tampered_inventory_without_repairing_it(self):
        data = self.load()
        data['files'][0]['change'] = 'M999'
        self.save(data)
        before = self.record.read_bytes()
        self.bad(self.checkpoint('--path', 'logic.py', '--status', 'unreviewed'), 'metadata mismatch')
        self.assertEqual(self.record.read_bytes(), before)

    def test_checkpoint_handles_rename_deleted_and_unusual_paths(self):
        for path in ('new name.txt', 'remove.txt', 'odd\tname\nλ.txt'):
            self.good(self.checkpoint('--path', path, '--status', 'reviewed', '--unit', 'R1',
                                      '--unit', 'R2', '--evidence', 'R1 trace', '--evidence', 'R2 trace'))
        self.good(self.check())

    def test_checkpoint_does_not_change_dirty_source(self):
        self.write('logic.py', 'local edits\n')
        before = self.git('status', '--porcelain')
        self.good(self.checkpoint('--path', 'logic.py', '--status', 'reviewed', '--unit', 'R1',
                                  '--evidence', 'Inspected immutable Git objects.'))
        self.assertEqual(self.git('status', '--porcelain'), before)
        self.assertEqual((self.repo / 'logic.py').read_text(), 'local edits\n')

    def test_interrupted_replace_preserves_record_and_removes_temporary_file(self):
        spec = importlib.util.spec_from_file_location('review_coverage_under_test', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = self.record.read_bytes()
        args = ['record', str(self.record), '--repo', str(self.repo), '--base', self.base,
                '--head', self.head, '--path', 'logic.py', '--status', 'reviewed',
                '--unit', 'R1', '--evidence', 'R1 immutable source trace']
        with patch.object(module.os, 'replace', side_effect=PermissionError('replace denied')):
            self.assertEqual(module.main(args), 1)
        self.assertEqual(self.record.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.coverage.json.*')), [])

    def test_evidence_audit_warns_on_repetition_without_rejecting_complete_groups(self):
        data = self.finish()
        citation = self.local_evidence()
        for row in data['files']:
            row['evidence'] = [dict(citation, locator='S1 / ' + row['path'])]
        self.save(data)
        before = self.record.read_bytes()
        result = self.check('--audit-evidence', '--require-complete')
        self.good(result)
        self.assertIn('Identical primary claim across 6 paths', result.stdout)
        self.assertEqual(self.record.read_bytes(), before)

    def test_common_secondary_evidence_does_not_mask_unique_primary_claims(self):
        data = self.finish()
        shared = self.local_evidence()
        for row in data['files']:
            row['evidence'] = [dict(shared, claim='Inspected specific behavior of ' + row['path']), shared]
        self.save(data)
        result = self.check('--audit-evidence', '--require-complete')
        self.good(result)
        self.assertNotIn('Identical primary claim', result.stdout)

    def test_legacy_evidence_audit_is_advisory(self):
        self.finish()
        result = self.check('--audit-evidence', '--require-complete')
        self.good(result)
        self.assertIn('only free-text evidence', result.stdout)

    def batch(self, value, **kwargs):
        path = self.root / 'batch.json'
        path.write_text(json.dumps(value))
        return self.run_cli('record-batch', str(self.record), '--input', str(path), **kwargs)

    def test_batch_checkpoints_distinct_evidence_and_preserves_untouched_fields(self):
        before = self.load()
        before['custom'] = 'preserve narrative'
        self.save(before)
        citation = self.local_evidence()
        rows = [dict(path=p, status='reviewed', units=['R1'], notes='',
                     evidence=[dict(citation, claim='Boundary checked for ' + p)])
                for p in ['logic.py', 'config.json']]
        self.good(self.batch({'files': rows}))
        after = self.load()
        for row in before['files']:
            replacement = next((r for r in rows if r['path'] == row['path']), None)
            if replacement:
                row.update(replacement)
        self.assertEqual(after, before)
        self.bad(self.check('--require-complete'), 'Coverage incomplete')

    def test_batch_rejects_duplicates_metadata_edits_and_invalid_evidence_atomically(self):
        row = dict(path='logic.py', status='reviewed', units=['R1'], notes='', evidence=['specific trace'])
        for value in [{}, {'files': []}, {'files': [row, row]},
                      {'files': [dict(row, path='unknown.py')]},
                      {'files': [dict(row, head='relabel')]},
                      {'files': [row, dict(row, path='config.json', evidence=[])]},
                      {'integration': {'status': 'reviewed', 'evidence': [], 'notes': ''}}]:
            with self.subTest(value=value):
                before = self.record.read_bytes()
                self.assertNotEqual(self.batch(value).returncode, 0)
                self.assertEqual(self.record.read_bytes(), before)

    def test_batch_integration_and_stale_snapshot_checks(self):
        value = {'integration': {'status': 'reviewed', 'evidence': ['S1 guard/caller trace'], 'notes': ''}}
        self.good(self.batch(value))
        before = self.record.read_bytes()
        self.write('logic.py', 'LIMIT = 8\n')
        later = self.commit('later')
        self.bad(self.batch(value, head=later), 'Snapshot mismatch')
        self.assertEqual(self.record.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)

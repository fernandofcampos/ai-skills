"""Fixture and scoring checks, not an agent-performance benchmark."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import workflow_eval as evaluation


class WorkflowCases(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'corpus'
        self.oracle = evaluation.prepare(self.root)

    def labels(self, arm):
        path = self.root / f'{arm}-labels.json'
        data = json.loads(path.read_text())
        data['conditions'] = dict(model='fixture-test', effort='high', tools='local-only', budget='test-only')
        data['judge'] = 'Synthetic test data; no agent run'
        for row in data['cases']:
            output = self.root / row['output']
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text('Synthetic output for scorer validation only.\n')
            row['matched_defects'] = self.oracle['cases'][row['id']]['defects'][:]
            row['unsupported_findings'] = 0
            row['evidence_notes'] = 'Synthetic test annotation, line 1; not a semantic evaluation.'
        path.write_text(json.dumps(data))
        return path, data

    def test_defect_reachable_through_api_and_fixed_in_followup(self):
        probe = '''from cache import UserCache
from api import get_profile
db = {('a', '7'): 'alice', ('b', '7'): 'bob'}
c = UserCache()
assert get_profile(db, c, {'tenant': 'b'}, 7) == 'bob'
c = UserCache()
assert get_profile(db, c, {'tenant': 'a'}, 7) == 'alice'
assert get_profile(db, c, {'tenant': 'b'}, 7) == 'bob'
c.evict('a', '7')
assert get_profile(db, c, {'tenant': 'b'}, 7) == 'bob'
'''
        for case, success in [('cross-boundary', False), ('follow-up', True), ('mechanical', True)]:
            repo = self.root / 'cases' / case / 'project'
            result = subprocess.run([sys.executable, '-c', probe], cwd=repo, capture_output=True)
            self.assertEqual(result.returncode == 0, success, result.stderr)
        repo = self.root / 'cases/cross-boundary/project'
        evaluation.git(repo, 'checkout', '-q', self.oracle['snapshots']['cross-boundary']['base'])
        result = subprocess.run([sys.executable, '-B', '-c', probe], cwd=repo, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_prepare_is_deterministic_and_never_overwrites(self):
        other = evaluation.prepare(self.root.parent / 'another')
        self.assertEqual(other['corpus_id'], self.oracle['corpus_id'])
        before = (self.root / 'oracle.json').read_bytes()
        with self.assertRaises(ValueError):
            evaluation.prepare(self.root)
        self.assertEqual((self.root / 'oracle.json').read_bytes(), before)

    def test_unfilled_labels_are_not_a_successful_evaluation(self):
        with self.assertRaisesRegex(ValueError, 'Record model'):
            evaluation.compare(self.root / 'oracle.json', self.root / 'baseline-labels.json', self.root / 'skill-labels.json')

    def test_unknowns_stay_unknown_and_matched_defects_score(self):
        a, _ = self.labels('baseline')
        b, _ = self.labels('skill')
        result = evaluation.compare(self.root / 'oracle.json', a, b)
        scored = result['skill']['cases']
        self.assertEqual(scored['cross-boundary']['recall'], 1)
        self.assertIsNone(scored['mechanical']['recall'])
        self.assertIsNone(scored['mechanical']['elapsed_seconds'])
        self.assertTrue(all(v is None for v in scored['concise-adr']['checks'].values()))

    def test_counts_need_trace_and_nonnegative_finite_values(self):
        path, data = self.labels('baseline')
        row = data['cases'][0]
        row['elapsed_seconds'] = 0
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'retained trace'):
            evaluation.score(path, self.oracle, 'baseline')
        (self.root / 'trace.txt').write_text('Synthetic trace for test only\n')
        row['trace'] = 'trace.txt'
        for bad in (-1, float('nan'), float('inf'), True):
            row['elapsed_seconds'] = bad
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'nonnegative'):
                evaluation.score(path, self.oracle, 'baseline')

    def test_missing_artifact_duplicate_case_and_bad_defect_rejected(self):
        path, data = self.labels('baseline')
        original = json.loads(json.dumps(data))
        for mutation in ('missing-output', 'duplicate-case', 'unknown-defect'):
            data = json.loads(json.dumps(original))
            if mutation == 'missing-output':
                data['cases'][0]['output'] = 'absent.md'
            elif mutation == 'duplicate-case':
                data['cases'][1] = data['cases'][0]
            else:
                data['cases'][0]['matched_defects'] = ['unverified-defect']
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                evaluation.score(path, self.oracle, 'baseline')

    def test_comparison_rejects_changed_conditions_or_oracle(self):
        a, _ = self.labels('baseline')
        b, data = self.labels('skill')
        data['conditions']['effort'] = 'low'
        b.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'Conditions differ'):
            evaluation.compare(self.root / 'oracle.json', a, b)
        oracle = json.loads((self.root / 'oracle.json').read_text())
        oracle['cases']['cross-boundary']['defects'] = []
        (self.root / 'oracle.json').write_text(json.dumps(oracle))
        with self.assertRaisesRegex(ValueError, 'Oracle identity'):
            evaluation.compare(self.root / 'oracle.json', a, b)


if __name__ == '__main__':
    unittest.main()

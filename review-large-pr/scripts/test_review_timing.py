#!/usr/bin/env python3
"""Endpoint accuracy, unknown measurements and retrospective phase tests."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from review_coverage import CoverageError
from review_run import validate_events
from review_timing import observation, timing_summary, validate_observation


def stamp(minute):
    return f'2026-01-01T12:{minute:02d}:00+00:00'


def point(name, minute, recorded=50, basis='evidence'):
    return dict(name=name, at=None if basis == 'unknown' else stamp(minute),
                recorded_at=stamp(recorded), basis=basis, source='Saved host checkpoint')


class TimingCases(unittest.TestCase):
    def test_separate_total_lead_and_delivery_durations(self):
        data = dict(timing=dict(milestones=[
            point('intake', 0), point('lead_start', 2), point('lead_complete', 17),
            point('delivery_ready', 19), point('delivered', 23)]))
        durations, warnings = timing_summary(data)
        self.assertFalse(warnings)
        self.assertEqual(durations, dict(end_to_end=1380, intake_to_ready=1140,
            coordination_before_lead=120, lead_execution=900,
            delivery_preparation=120, after_lead_to_delivery=360))

    def test_ready_never_implies_delivered(self):
        durations, warnings = timing_summary(dict(timing=dict(milestones=[
            point('intake', 0), point('delivery_ready', 19)])))
        self.assertIsNone(durations['end_to_end'])
        self.assertEqual(durations['intake_to_ready'], 1140)
        self.assertTrue(any('not delivery' in w for w in warnings))

    def test_unknown_not_zero(self):
        durations, _ = timing_summary(dict(timing=dict(milestones=[
            point('intake', 0, basis='unknown'), point('delivered', 23)])))
        self.assertIsNone(durations['end_to_end'])

    def test_legacy_missing_timing_is_not_total_duration(self):
        durations, warnings = timing_summary({'created_at': stamp(0), 'events': []})
        self.assertEqual(durations, {})
        self.assertIn('unknown', warnings[0])

    def test_missing_retrospective_source_rejected(self):
        for kwargs in [dict(at=stamp(0)), dict(unknown=True), dict(at=stamp(0), unknown=True, source='x')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(CoverageError):
                observation(**kwargs)

    def test_observed_checkpoint_and_unknown(self):
        at, recorded, basis = validate_observation(observation())
        self.assertEqual(at, recorded)
        self.assertEqual(basis, 'observed')
        at, _, basis = validate_observation(observation(unknown=True, source='No measurement'))
        self.assertIsNone(at)
        self.assertEqual(basis, 'unknown')

    def test_invalid_endpoint_evidence(self):
        original = point('intake', 0)
        for patch in [dict(source=''), dict(at=stamp(55)), dict(basis='observed'),
                      dict(basis='unknown'), dict(recorded_at='2026-01-01T12:50:00'),
                      dict(basis='estimated')]:
            with self.subTest(patch=patch), self.assertRaises((CoverageError, ValueError)):
                validate_observation(dict(original, **patch))

    def test_duplicate_out_of_order_or_legacy_milestones_rejected(self):
        for milestones in [
            [point('intake', 0), point('intake', 0)],
            [point('intake', 5), point('lead_start', 2)],
            [point('intake', 0, recorded=50), point('lead_start', 2, recorded=40)],
            [dict(name='intake', at=stamp(0))],
            [point('made_up', 0)],
        ]:
            with self.subTest(milestones=milestones), self.assertRaises(CoverageError):
                timing_summary(dict(timing=dict(milestones=milestones)))

    def events(self):
        return dict(created_at=stamp(10), events=[
            dict(point('unused', 0, recorded=20), owner='lead', phase='context', state='start', note='Earlier work'),
            dict(point('unused', 8, recorded=21), owner='lead', phase='context', state='complete', note='Saved context'),
        ])

    def test_retrospective_phase_predates_manifest(self):
        phases = validate_events(self.events())
        phase = phases[('lead', 'context')]
        self.assertEqual((datetime.fromisoformat(phase['last']['at']) - phase['start']).total_seconds(), 480)

    def test_retrospective_unknown_phase_has_no_start_duration(self):
        data = self.events()
        for row in data['events']:
            row.update(at=None, basis='unknown')
        self.assertIsNone(validate_events(data)[('lead', 'context')]['start'])

    def test_effective_phase_order_and_logging_order_checked_separately(self):
        for patch in [dict(at=stamp(0)), dict(recorded_at=stamp(19)), dict(recorded_at=stamp(9))]:
            data = self.events()
            data['events'][0]['at'] = stamp(2)
            data['events'][1].update(patch)
            with self.subTest(patch=patch), self.assertRaises(CoverageError):
                validate_events(data)

    def test_overlapping_phases_allowed(self):
        data = self.events()
        data['events'].insert(1, dict(point('unused', 3, recorded=20), owner='setup', phase='environment',
                                     state='start', note='Parallel setup'))
        data['events'].append(dict(point('unused', 12, recorded=22), owner='setup', phase='environment',
                                   state='complete', note='Ready'))
        self.assertEqual(len(validate_events(data)), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)

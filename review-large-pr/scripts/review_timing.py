"""Timing evidence shared by the run helper; never infer unobserved delivery."""
from datetime import datetime, timezone

from review_coverage import CoverageError

MILESTONES = ('intake', 'lead_start', 'lead_complete', 'delivery_ready', 'delivered')


def timestamp(value):
    if not isinstance(value, str):
        raise CoverageError('Timestamp must be an ISO string with timezone.')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise CoverageError('Timestamp requires a timezone.')
    return result


def observation(at=None, unknown=False, source=None):
    recorded = datetime.now(timezone.utc).isoformat()
    if at and unknown:
        raise CoverageError('Choose a source-backed timestamp or unknown, not both.')
    if (at or unknown) and (not isinstance(source, str) or not source.strip()):
        raise CoverageError('Retrospective/unknown timing requires a source or explanation.')
    result = dict(at=None if unknown else at or recorded, recorded_at=recorded,
                  basis='unknown' if unknown else 'evidence' if at else 'observed',
                  source=source or 'Checkpoint observed now by the caller')
    validate_observation(result)
    return result


def validate_observation(row):
    """Return effective and logging times, with a separate legacy designation."""
    if 'basis' not in row:
        if 'recorded_at' in row:
            raise CoverageError('Timing with recorded_at requires an explicit basis.')
        at = timestamp(row.get('at'))
        return at, at, 'legacy'
    basis = row.get('basis')
    if basis not in {'observed', 'evidence', 'unknown'}:
        raise CoverageError('Timing basis must be observed, evidence or unknown.')
    if not isinstance(row.get('source'), str) or not row['source'].strip():
        raise CoverageError('Timing requires its source or an unknown-time explanation.')
    recorded = timestamp(row.get('recorded_at'))
    if basis == 'unknown':
        if row.get('at') is not None:
            raise CoverageError('Unknown timing must have a null effective timestamp.')
        return None, recorded, basis
    at = timestamp(row.get('at'))
    if at > recorded:
        raise CoverageError('Effective time cannot be after the observation was recorded.')
    if basis == 'observed' and at != recorded:
        raise CoverageError('Observed time must equal logging time; use evidence for retrospective times.')
    return at, recorded, basis


def timing_summary(data):
    """Durations use only evidenced endpoints, never manifest age as wall time."""
    timing = data.get('timing')
    if timing is None:
        return {}, ['No lifecycle timing: end-to-end duration is unknown.']
    if not isinstance(timing, dict) or not isinstance(timing.get('milestones'), list):
        raise CoverageError('timing.milestones must be an array.')
    points, previous = {}, None
    for row in timing['milestones']:
        if not isinstance(row, dict):
            raise CoverageError('Milestone must be an object.')
        name = row.get('name')
        if name not in MILESTONES or name in points:
            raise CoverageError('Unknown or duplicate lifecycle milestone.')
        at, recorded, basis = validate_observation(row)
        if basis == 'legacy':
            raise CoverageError('Lifecycle milestones require an explicit timing basis.')
        if previous and recorded < previous:
            raise CoverageError('Milestone observations must retain logging order.')
        previous = recorded
        points[name] = at
    effective = [points[n] for n in MILESTONES if points.get(n) is not None]
    if effective != sorted(effective):
        raise CoverageError('Lifecycle endpoints are out of order.')
    pairs = {
        'end_to_end': ('intake', 'delivered'),
        'intake_to_ready': ('intake', 'delivery_ready'),
        'coordination_before_lead': ('intake', 'lead_start'),
        'lead_execution': ('lead_start', 'lead_complete'),
        'delivery_preparation': ('lead_complete', 'delivery_ready'),
        'after_lead_to_delivery': ('lead_complete', 'delivered'),
    }
    durations = {
        label: ((points[end] - points[start]).total_seconds()
                if points.get(start) is not None and points.get(end) is not None else None)
        for label, (start, end) in pairs.items()
    }
    warnings = []
    if durations['end_to_end'] is None:
        warnings.append('User-visible end-to-end duration is unknown; delivery-ready is not delivery.')
    if durations['lead_execution'] is None:
        warnings.append('Lead execution duration is unknown.')
    return durations, warnings

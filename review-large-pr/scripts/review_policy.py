"""Resolve saved model preferences without configuring agents or running project code."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from review_coverage import CoverageError


DEFAULTS = {
    'lead': {'model': 'gpt-6-astra', 'effort': 'xhigh'},
    'reviewer': {'model': 'gpt-6.1-sol', 'effort': 'high'},
    'documentation_author': {'model': 'gpt-6.1-sol', 'effort': 'high'},
}


def validate_preferences(data):
    if (not isinstance(data, dict) or set(data) - {'schema_version', 'models'}
            or type(data.get('schema_version')) is not int or data['schema_version'] != 1):
        raise CoverageError('Model policy requires schema_version: 1 and optional models.')
    models = data.get('models', {})
    if not isinstance(models, dict) or set(models) - set(DEFAULTS):
        raise CoverageError('Policy models supports lead, reviewer and documentation_author only.')
    for role, settings in models.items():
        if not isinstance(settings, dict) or set(settings) != {'model', 'effort'}:
            raise CoverageError(f'Policy {role} requires model and effort.')
        if any(not isinstance(v, str) or not v.strip() for v in settings.values()):
            raise CoverageError(f'Policy {role} model and effort must be nonempty strings.')
    return data


def load_policy(repo=None, explicit=None):
    path = Path(explicit).resolve() if explicit else Path(repo) / '.ai-skills.json' if repo else None
    if path is None or (not explicit and not path.exists()):
        return {'source': 'skill defaults', 'sha256': None,
                'preferences': {'schema_version': 1, 'models': {}}}
    try:
        raw = path.read_bytes()
        data = validate_preferences(json.loads(raw))
    except (OSError, ValueError) as exc:
        raise CoverageError(f'Cannot read model policy {path}: {exc}. Fix the file or choose --policy explicitly.') from exc
    return {'source': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(), 'preferences': data}


def preferences(snapshot=None):
    result = deepcopy(DEFAULTS)
    if snapshot is not None:
        if not isinstance(snapshot, dict) or set(snapshot) != {'source', 'sha256', 'preferences'}:
            raise CoverageError('Saved model policy requires source, sha256 and preferences.')
        if not isinstance(snapshot['source'], str) or not snapshot['source'].strip():
            raise CoverageError('Saved model policy requires its source.')
        digest = snapshot['sha256']
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64
                                  or any(c not in '0123456789abcdef' for c in digest)):
            raise CoverageError('Invalid model policy hash.')
        result.update(validate_preferences(snapshot['preferences']).get('models', {}))
    return result


def preferred_configuration(data, snapshot=None):
    settings = preferences(snapshot)['lead']
    override = data.get('user_override')
    if override is not None:
        if not isinstance(override, dict) or override.get('authority') != 'explicit_user':
            raise CoverageError('A model override requires explicit_user authority and its source.')
        for key in ('model', 'effort', 'source'):
            if not isinstance(override.get(key), str) or not override[key].strip():
                raise CoverageError(f'user_override.{key} must be a nonempty string.')
        settings = override
    return settings['model'], settings['effort']

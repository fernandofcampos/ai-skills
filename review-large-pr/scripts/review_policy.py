"""Resolve saved model preferences without configuring agents or running project code."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from review_coverage import CoverageError


LEGACY_DEFAULTS = {
    'lead': {'model': 'gpt-6-astra', 'effort': 'xhigh'},
    'reviewer': {'model': 'gpt-6.1-sol', 'effort': 'high'},
    'documentation_author': {'model': 'gpt-6.1-sol', 'effort': 'high'},
}

DEFAULTS = {
    'lead': {'model': 'gpt-6.2-astra', 'effort': 'medium'},
    'reviewer': {'model': 'gpt-6.2-sol', 'effort': 'medium'},
    'documentation_author': {'model': 'gpt-6.2-sol', 'effort': 'medium'},
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
    snapshot = {'source': 'skill defaults', 'sha256': None, 'defaults': deepcopy(DEFAULTS),
                'preferences': {'schema_version': 1, 'models': {}}}
    if path is not None and (explicit or path.exists()):
        try:
            raw = path.read_bytes()
            data = validate_preferences(json.loads(raw))
        except (OSError, ValueError) as exc:
            raise CoverageError(f'Cannot read model policy {path}: {exc}. Fix the file or choose --policy explicitly.') from exc
        snapshot.update(source=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), preferences=data)
    return snapshot


def policy_for_record(record):
    snapshot = record.get('model_policy')
    if snapshot is None:
        # Runs created before policy capture used the original skill defaults.
        return {'source': 'skill defaults', 'sha256': None, 'preferences': {'schema_version': 1}}
    return snapshot


def preferences(snapshot=None):
    if snapshot is None:
        return deepcopy(DEFAULTS)
    required = {'source', 'sha256', 'preferences'}
    if not isinstance(snapshot, dict) or set(snapshot) not in (required, required | {'defaults'}):
        raise CoverageError('Saved model policy requires source, sha256 and preferences, with optional defaults.')
    if not isinstance(snapshot['source'], str) or not snapshot['source'].strip():
        raise CoverageError('Saved model policy requires its source.')
    digest = snapshot['sha256']
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64
                              or any(c not in '0123456789abcdef' for c in digest)):
        raise CoverageError('Invalid model policy hash.')
    defaults = snapshot.get('defaults', LEGACY_DEFAULTS)
    validate_preferences({'schema_version': 1, 'models': defaults})
    if set(defaults) != set(DEFAULTS):
        raise CoverageError('Saved defaults must include every model role.')
    overrides = validate_preferences(snapshot['preferences']).get('models', {})
    return deepcopy({**defaults, **overrides})


def preferred_configuration(data, snapshot=None, role='lead'):
    settings = preferences(snapshot)[role]
    override = data.get('user_override')
    if override is not None:
        if not isinstance(override, dict) or override.get('authority') != 'explicit_user':
            raise CoverageError('A model override requires explicit_user authority and its source.')
        for key in ('model', 'effort', 'source'):
            if not isinstance(override.get(key), str) or not override[key].strip():
                raise CoverageError(f'user_override.{key} must be a nonempty string.')
        settings = override
    return settings['model'], settings['effort']

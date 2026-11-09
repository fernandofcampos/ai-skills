#!/usr/bin/env python3
"""Archive selected review evidence with original hashes and portable copies.

No Git/network operations. Integrity checks do not establish review correctness,
source availability, secret-free content or storage retention guarantees.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from urllib.parse import quote, unquote, urlsplit

from review_coverage import CoverageError

FORBIDDEN = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', '.cache',
             '.npm', '.pnpm-store', '.npmrc', '.pypirc', '.netrc', '.env'}
# Single-line inline links, including optional quoted/parenthesized titles.
# Nested bare destinations, reference-style and HTML links need manual audit.
LINK = re.compile(r'''(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^()\s]+)((?:[ \t]+(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*\))''')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
CODE = re.compile(r'(`+)(.+?)\1', re.DOTALL)


def sha(content):
    return hashlib.sha256(content).hexdigest()


def relative_name(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts or str(path) != value or '\\' in value:
        raise CoverageError(f'Expected a normalized relative file path: {value!r}')
    return path


def safe_file(root, name):
    relative_name(name)
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise CoverageError(f'Symlink evidence is not archived: {name}')
    if not path.is_file():
        raise CoverageError(f'Selected evidence is not a regular file: {name}')
    return path


def evidence_references(data):
    """Yield only evidence/coverage pointers; source and installed hashes stay pinned."""
    if isinstance(data, dict):
        if {'path', 'locator', 'claim'} <= data.keys():
            yield data
        for row in data.get('coverage', []) if isinstance(data.get('coverage'), list) else []:
            if isinstance(row, dict) and 'snapshot' in row and 'path' in row:
                yield row
        for value in data.values():
            yield from evidence_references(value)
    elif isinstance(data, list):
        for value in data:
            yield from evidence_references(value)


def review_json_records(raw, root, initial):
    """Follow record identities, never infer roles from arbitrary JSON fixtures."""
    records, pending = set(), list(initial)
    while pending:
        name = pending.pop()
        relative_name(name)
        if name in records:
            continue
        if name not in raw:
            raise CoverageError(f'Include referenced JSON review record: {name}')
        records.add(name)
        data = json.loads(raw[name])
        if not isinstance(data, dict):
            continue
        for ref in data.get('coverage', []) if isinstance(data.get('coverage'), list) else []:
            if isinstance(ref, dict) and {'snapshot', 'path'} <= ref.keys():
                pending.append(local_reference(ref['path'], PurePosixPath(name), root))
        # Selected repair/promotion backups are known historical records too.
        # Unselected history remains provenance, not an implicit file selection.
        history = [row.get('previous_record') for row in data.get('evidence_repairs', [])]
        previous = data.get('previous_record')
        if isinstance(previous, dict):
            history.append(previous.get('path'))
        for value in history:
            if isinstance(value, str):
                target = relocated_path(value, PurePosixPath(name), root)
                if target.is_relative_to(root):
                    relative = target.relative_to(root).as_posix()
                    if relative in raw:
                        pending.append(relative)
    return records


def relocation_aliases(run):
    """Explicit repair history applies to portable copies, never original receipts."""
    aliases = {}
    for repair in run.get('evidence_repairs', []):
        for row in repair['relocations']:
            old, new = row['from_path'], row['to_path']
            if not Path(old).is_absolute() or not Path(new).is_absolute():
                raise CoverageError('Recorded repair aliases must use absolute paths.')
            if old in aliases and aliases[old] != new:
                raise CoverageError('Conflicting evidence relocation history.')
            aliases[old] = new
    return aliases


def relocated_path(value, owner, root, aliases=None):
    path = Path(value)
    target = (path if path.is_absolute() else root / owner.parent / path).resolve()
    seen = set()
    while str(target) in (aliases or {}):
        if str(target) in seen:
            raise CoverageError('Cyclic evidence relocation history.')
        seen.add(str(target))
        target = Path(aliases[str(target)]).resolve()
    return target


def local_reference(value, owner, root, aliases=None):
    if not isinstance(value, str) or not value.strip():
        raise CoverageError('Evidence reference must be a nonempty local path.')
    target = relocated_path(value, owner, root, aliases)
    try:
        return target.relative_to(root).as_posix()
    except ValueError:
        raise CoverageError(f'Evidence outside selected root must be staged explicitly: {value}')


def validate_relocation_contents(run, root, raw, aliases):
    """Reject pathname reuse and validate the actual replacement bytes to archive."""
    captured = {root / name: content for name, content in raw.items()}
    for repair in run.get('evidence_repairs', []):
        for row in repair['relocations']:
            expected = row.get('sha256')
            if (not isinstance(expected, str) or len(expected) != 64
                    or any(c not in '0123456789abcdef' for c in expected)):
                raise CoverageError('Relocation requires a retained SHA-256.')
            old = Path(row['from_path'])
            old_content = captured.get(old)
            if old_content is None and old.exists():
                old_content = old.read_bytes()
            if old_content is not None and sha(old_content) != expected:
                raise CoverageError(f'Ambiguous relocation: old pathname contains different bytes: {old}')
            replacement = relocated_path(row['to_path'], PurePosixPath('.'), root, aliases)
            if replacement not in captured:
                raise CoverageError(f'Select the resolved relocated evidence: {replacement}')
            if sha(captured[replacement]) != expected:
                raise CoverageError(f'Relocated evidence does not match retained SHA-256: {replacement}')


def markdown_links(text, replace):
    """Handle ordinary inline links while preserving fenced/inline code examples."""
    output, fenced = [], None
    for line in text.splitlines(keepends=True):
        marker = FENCE.match(line)
        if fenced:
            output.append(line)
            if marker and marker[1][0] == fenced[0] and len(marker[1]) >= len(fenced) and not marker[2].strip():
                fenced = None
        elif marker:
            fenced = marker[1]
            output.append(line)
        else:
            cursor, pieces = 0, []
            for span in CODE.finditer(line):
                pieces.extend([LINK.sub(replace, line[cursor:span.start()]), span[0]])
                cursor = span.end()
            pieces.append(LINK.sub(replace, line[cursor:]))
            output.append(''.join(pieces))
    return ''.join(output)


def portable_content(raw, name, root, selected, canonical_run=None, aliases=None,
                     *, rewrite_json=False, encode_paths=True):
    owner = PurePosixPath(name)
    suffix = owner.suffix.lower()
    if rewrite_json:
        data = json.loads(raw)
        # Standalone checkpoint inputs use the selected canonical run's directory,
        # even when saved in requests/. Preserve that convention on relocation.
        if isinstance(data, dict) and {'id', 'expected_revision', 'actor', 'note'} <= data.keys():
            if canonical_run is None:
                raise CoverageError('Checkpoint input requires its canonical run context.')
            owner = PurePosixPath(canonical_run)
        for ref in evidence_references(data):
            target = local_reference(ref['path'], owner, root, aliases)
            if target not in selected:
                raise CoverageError(f'Unselected structured evidence: {name} -> {target}')
            ref['path'] = os.path.relpath(target, str(owner.parent))
        return (json.dumps(data, indent=2, ensure_ascii=True) + '\n').encode()
    if suffix == '.md':
        def replace(match):
            value = match[2].removeprefix('<').removesuffix('>')
            url = urlsplit(value)
            sandbox = url.scheme == 'sandbox'
            if sandbox and url.netloc:
                raise CoverageError('sandbox: evidence links must be local, without an authority.')
            if (url.scheme and not sandbox) or url.netloc or not url.path:
                return match[0]
            decoded = unquote(url.path)
            if sandbox and not Path(decoded).is_absolute():
                raise CoverageError('sandbox: evidence links require an absolute local path.')
            # Absolute source links outside the evidence tree remain explicit
            # external dependencies. Internal/relative links must be selected.
            path = relocated_path(decoded, owner, root, aliases)
            if not sandbox and Path(decoded).is_absolute() and not path.is_relative_to(root):
                return match[0]
            target = local_reference(decoded, owner, root, aliases)
            if target not in selected:
                raise CoverageError(f'Unselected Markdown evidence: {name} -> {target}')
            dest = os.path.relpath(target, str(owner.parent))
            if encode_paths:
                # Quote the path separately: #, ?, %, and : are filename data,
                # not fragments, queries, escapes, or a URI scheme.
                dest = quote(Path(dest).as_posix(), safe='/')
            if url.query:
                dest += '?' + url.query
            if url.fragment:
                dest += '#' + url.fragment
            return match[1] + '<' + dest + '>' + match[3]
        return markdown_links(raw.decode('utf-8'), replace).encode()
    return raw


def create(root, output, run, report, includes, json_records=()):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(root):
        raise CoverageError('Archive destination must be new and outside the scratch root.')
    temporary_roots = {Path('/tmp').resolve(), Path(tempfile.gettempdir()).resolve()}
    if any(output.is_relative_to(p) for p in temporary_roots):
        raise CoverageError('Choose durable output outside system temporary storage.')
    selected = set([run, report, *includes, *json_records])
    for name in selected:
        relative_name(name)
        if any(p in FORBIDDEN or p.startswith('.env.') for p in PurePosixPath(name).parts):
            raise CoverageError(f'Cache, dependency or credential file is not review evidence: {name}')
    # Read each selected file once; preserve those exact bytes even if sources
    # later change. The lead must finish writers before archive creation.
    raw = {name: safe_file(root, name).read_bytes() for name in sorted(selected)}
    run_data = json.loads(raw[run])
    if not isinstance(run_data, dict) or run_data.get('schema_version') not in {1, 2} or not run_data.get('coverage'):
        raise CoverageError('Select a run manifest with coverage snapshots.')
    snapshots = []
    for item in run_data['coverage']:
        if run_data['schema_version'] == 2:
            record = item['record']
        else:
            target = local_reference(item['path'], PurePosixPath(run), root)
            if target not in selected:
                raise CoverageError(f'Include referenced coverage record: {target}')
            record = json.loads(raw[target])
        if record.get('snapshot') != item['snapshot']:
            raise CoverageError('Run/coverage snapshot mismatch.')
        snapshots.append(item['snapshot'])
    aliases = relocation_aliases(run_data)
    validate_relocation_contents(run_data, root, raw, aliases)
    records = review_json_records(raw, root, [run, *json_records])
    portable = {name: portable_content(raw[name], name, root, selected, run, aliases,
                                      rewrite_json=name in records) for name in sorted(selected)}
    manifest = dict(schema_version=2, created_at=datetime.now(timezone.utc).isoformat(),
                    source_root=str(root), report=report, run=run, snapshots=snapshots,
                    json_records=sorted(records),
                    files=[dict(path=name, original_sha256=sha(raw[name]),
                                portable_sha256=sha(portable[name])) for name in sorted(selected)],
                    limits=['Selected files only; inspect content for secrets before packaging.',
                            'Git source/installed resource paths remain external; snapshots are unchanged.',
                            'Structured JSON references are checked only in declared review records; other JSON is preserved byte-for-byte.',
                            'Supported single-line inline links (including simple titles) and structured references checked; unsupported syntax and fragments need manual audit.'])
    # Exclusive destination: never overwrite another delivery; clean up only a
    # directory this call successfully created if writing/checking fails.
    output.mkdir()
    try:
        for kind, contents in [('originals', raw), ('files', portable)]:
            for name, content in contents.items():
                dest = output / kind / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
        (output / 'archive.json').write_text(json.dumps(manifest, indent=2) + '\n')
        check(output)
    except Exception:
        shutil.rmtree(output)
        raise
    return manifest


def check(output):
    output = Path(output).resolve()
    manifest = json.loads(safe_file(output, 'archive.json').read_bytes())
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version'] not in {1, 2}:
        raise CoverageError('Expected archive schema_version 1 or 2.')
    rows = manifest.get('files')
    if not isinstance(rows, list) or not rows:
        raise CoverageError('Archive requires a nonempty file inventory.')
    selected, portable = set(), {}
    for row in rows:
        name = row['path']
        relative_name(name)
        if name in selected:
            raise CoverageError('Duplicate archive file.')
        selected.add(name)
        for kind, key in [('originals', 'original_sha256'), ('files', 'portable_sha256')]:
            content = safe_file(output, kind + '/' + name).read_bytes()
            if sha(content) != row[key]:
                raise CoverageError(f'Archive integrity mismatch: {kind}/{name}')
            if kind == 'files':
                portable[name] = content
    if manifest.get('report') not in selected or manifest.get('run') not in selected:
        raise CoverageError('Archive report/run must be selected.')
    # Check relocated references without needing the old scratch or Git checkout.
    root = output / 'files'
    legacy = manifest['schema_version'] == 1
    if legacy:
        # Existing archives used extension-based JSON rewriting and unescaped
        # Markdown destinations. Verify them under that original contract.
        records = {name for name in selected if PurePosixPath(name).suffix.lower() == '.json'}
    else:
        declared = manifest.get('json_records')
        if (not isinstance(declared, list) or any(not isinstance(name, str) for name in declared)
                or len(set(declared)) != len(declared) or not set(declared) <= selected
                or manifest['run'] not in declared):
            raise CoverageError('Archive requires selected, unique JSON review records including its run.')
        records = review_json_records(portable, root, declared)
        if records != set(declared):
            raise CoverageError('Archive JSON record inventory omits referenced records.')
    for name in selected:
        raw = portable[name]
        if name in records:
            for ref in evidence_references(json.loads(raw)):
                if Path(ref['path']).is_absolute():
                    raise CoverageError('Archived evidence reference must be portable.')
        if portable_content(raw, name, root, selected, manifest['run'],
                            rewrite_json=name in records, encode_paths=not legacy) != raw:
            raise CoverageError(f'Archive contains a non-portable or non-normalized evidence reference: {name}')
    run = json.loads(safe_file(root, manifest['run']).read_bytes())
    snapshots = []
    for ref in run['coverage']:
        if run.get('schema_version') == 2:
            coverage = ref['record']
        else:
            target = local_reference(ref['path'], PurePosixPath(manifest['run']), root)
            coverage = json.loads(safe_file(root, target).read_bytes())
        if coverage.get('snapshot') != ref['snapshot']:
            raise CoverageError('Archived run/coverage snapshot mismatch.')
        snapshots.append(ref['snapshot'])
    if snapshots != manifest.get('snapshots'):
        raise CoverageError('Archive snapshot identities changed.')
    original_run = json.loads(safe_file(output / 'originals', manifest['run']).read_bytes())
    if [c['snapshot'] for c in original_run['coverage']] != snapshots:
        raise CoverageError('Portable run changed the original source identities.')
    print(f'PASS: {len(selected)} selected files, original/portable hashes and evidence references. '
          'Source availability, content meaning, fragments and unsupported Markdown forms require separate verification.')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('create')
    build.add_argument('--root', required=True)
    build.add_argument('--output', required=True)
    build.add_argument('--run', default='run.json')
    build.add_argument('--report', default='review-record.md')
    build.add_argument('--include', action='append', default=[])
    build.add_argument('--json-record', action='append', default=[],
                       help='Include a JSON review record and rewrite its evidence pointers; repeat as needed. Other JSON includes stay byte-identical.')
    inspect = sub.add_parser('check')
    inspect.add_argument('archive')
    args = parser.parse_args(argv)
    try:
        if args.command == 'create':
            create(args.root, args.output, args.run, args.report, args.include, args.json_record)
        else:
            check(args.archive)
    except (CoverageError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Check Markdown structure and links; factual and architectural review stays manual."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

try:
    from markdown_it import MarkdownIt
    import yaml
except ImportError as exc:
    sys.exit(
        f"Missing validator dependency: {exc.name}. In a temporary virtual environment, "
        f"run: python -m pip install -r {Path(__file__).with_name('requirements.txt')}"
    )

MARKDOWN = MarkdownIt('commonmark', {'html': True}).enable('table')
MARKDOWN_SUFFIXES = {'.md', '.markdown'}
DISCOVERY_KEY = 'document_feature_design'
DISCOVERY_POINTERS = ('source_inventory', 'review_map', 'critical_invariants', 'integration_scenarios')
METADATA_ALIASES = {
    'Decision status': {'decision status', 'status'},
    'Implementation status': {'implementation status'},
    'Deployment status': {'deployment status'},
    'Decision date': {'decision date', 'date'},
    'Last verified': {'last verified', 'verified at'},
    'Source roots': {'source roots', 'source root'},
    'Source baseline': {'source baseline', 'source baselines'},
}
SECTION_ALIASES = {
    'overview': {'overview', 'feature overview', 'feature and decision overview', 'decision overview'},
    'reference': {'architectural reference', 'technical reference', 'design details', 'technical design', 'architecture'},
    'evidence': {'evidence status', 'evidence classification', 'assumptions and conflicts', 'source conflicts',
                 'evidence status assumptions and conflicts', 'evidence and assumptions'},
}


@dataclass(frozen=True)
class Finding:
    level: str
    path: Path
    message: str
    line: int | None = None

    def render(self):
        return f"{self.level}: {self.path}{':' + str(self.line) if self.line else ''}: {self.message}"


@dataclass
class Heading:
    title: str
    level: int
    start: int
    end: int
    line: int


@dataclass
class Document:
    path: Path
    tokens: list
    frontmatter: dict
    headings: list[Heading]
    anchors: set[str]


def normalise(value):
    return ' '.join(re.sub(r'[^\w\s]', ' ', str(value).replace('_', ' ')).lower().split())


def inline_text(token, include_code=True):
    parts = []
    for child in token.children or []:
        if child.type in {'text', 'image'} or (include_code and child.type == 'code_inline'):
            parts.append(child.content)
        elif child.type in {'softbreak', 'hardbreak'}:
            parts.append('\n')
    return ''.join(parts)


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and (key == 'id' or (tag == 'a' and key == 'name')):
                self.anchors.add(value)

    handle_startendtag = handle_starttag


def check_discovery_keys(raw):
    """Reject ambiguous marker keys without changing legacy metadata conventions."""
    node = yaml.compose(raw)
    entries = [value for key, value in node.value
               if isinstance(key, yaml.ScalarNode) and key.value == DISCOVERY_KEY]
    if len(entries) != 1:
        raise ValueError(f'{DISCOVERY_KEY} must occur exactly once as an explicit top-level key')
    block = entries[0]
    if isinstance(block, yaml.MappingNode):
        keys = [key.value for key, _ in block.value if isinstance(key, yaml.ScalarNode)]
        if len(keys) != len(set(keys)) or '<<' in keys:
            raise ValueError(f'{DISCOVERY_KEY} cannot contain duplicate or merged fields')


def parse_document(path, text):
    frontmatter = {}
    match = re.match(r'\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|$)', text, re.S)
    if match:
        try:
            frontmatter = yaml.safe_load(match[1]) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f'invalid YAML frontmatter: {exc}') from exc
        if not isinstance(frontmatter, dict):
            raise ValueError('YAML frontmatter must be a mapping')
        if DISCOVERY_KEY in frontmatter:
            check_discovery_keys(match[1])
        text = '\n' * text[:match.end()].count('\n') + text[match.end():]
    tokens = MARKDOWN.parse(text)
    headings = []
    generated = set()
    html = AnchorParser()
    for index, token in enumerate(tokens):
        if token.type == 'heading_open':
            title = inline_text(tokens[index + 1])
            level = int(token.tag[1:])
            end = next((i for i in range(index + 1, len(tokens))
                        if tokens[i].type == 'heading_open' and int(tokens[i].tag[1:]) <= level), len(tokens))
            headings.append(Heading(title, level, index, end, token.map[0] + 1))
            # Common GitHub-style fragments: preserve underscores and consecutive
            # hyphens/spaces, including duplicate-name collisions. Custom renderer
            # rules must be checked by that renderer with --anchors skip here.
            base = re.sub(r'[^\w\s-]', '', title.lower())
            base = re.sub(r'\s', '-', base)
            slug, suffix = base, 0
            while slug in generated:
                suffix += 1
                slug = f'{base}-{suffix}'
            generated.add(slug)
        if token.type == 'html_block':
            html.feed(token.content)
        for child in token.children or []:
            if child.type == 'html_inline':
                html.feed(child.content)
    return Document(path, tokens, frontmatter, headings, generated | html.anchors)


def template_markers():
    path = Path(__file__).resolve().parent.parent / 'assets/design-document-template.md'
    text = path.read_text(encoding='utf-8')
    comments = {' '.join(x.split()) for x in re.findall(r'<!--(.*?)-->', text, re.S)}
    placeholders = {x.strip() for x in re.findall(r'(?<!\!)\[([^\]\n]+)\](?!\()', text) if len(x.strip()) >= 4}
    return comments, placeholders


def validate_surface(doc, comments, placeholders):
    findings = []
    h1_count = sum(h.level == 1 for h in doc.headings)
    has_title = isinstance(doc.frontmatter.get('title'), str) and doc.frontmatter['title'].strip()
    if h1_count != 1 and not (h1_count == 0 and has_title):
        findings.append(Finding('ERROR', doc.path, 'expected one H1, or a YAML title when the renderer supplies it'))
    chunks = [(str(v), 1, False) for v in doc.frontmatter.values()]
    for token in doc.tokens:
        line = token.map[0] + 1 if token.map else None
        if token.type == 'html_block':
            chunks.append((token.content, line, True))
        for child in token.children or []:
            if child.type in {'text', 'html_inline'}:
                chunks.append((child.content, line, child.type == 'html_inline'))
    for content, line, is_html in chunks:
        if is_html:
            for body in re.findall(r'<!--(.*?)-->', content, re.S):
                if ' '.join(body.split()) in comments or re.search(
                    r'\b(adapt this template|unused placeholders?|repeat this subsection|remove inapplicable)\b', body, re.I
                ):
                    findings.append(Finding('ERROR', doc.path, 'leftover template instruction comment', line))
            continue
        for value in re.findall(r'\[([^\]\n]+)\]', content):
            if value.strip() in placeholders or re.match(r'TODO\b', value):
                findings.append(Finding('ERROR', doc.path, f"leftover template placeholder '[{value}]'", line))
        if re.search(r'(?<![\w.-])(?:/Users/|/home/|[A-Za-z]:\\Users\\)', content):
            findings.append(Finding('WARNING', doc.path, 'machine-local path; prefer a repository-qualified reference', line))
    return findings


def metadata(doc):
    """Read only primary header metadata, never a nested decision's own status."""
    pairs = list(doc.frontmatter.items())
    stop = next((h.start for h in doc.headings if h.level >= 2), len(doc.tokens))
    row = None
    for token in doc.tokens[:stop]:
        if token.type == 'tr_open':
            row = []
        elif token.type == 'tr_close':
            if row and len(row) == 2:
                pairs.append(tuple(row))
            row = None
        elif token.type == 'inline':
            text = inline_text(token)
            if row is not None:
                row.append(text)
            else:
                for line in text.splitlines():
                    match = re.match(r'^([^:]{1,64}):\s*(.+)$', line)
                    if match:
                        pairs.append((match[1], match[2]))
    values, findings = {}, []
    for key, value in pairs:
        label = next((k for k, aliases in METADATA_ALIASES.items() if normalise(key) in aliases), None)
        if not label or value is None or value == [] or value == {}:
            continue
        value = str(value).strip()
        if not value:
            continue
        if label in values and values[label] != value:
            findings.append(Finding('ERROR', doc.path, f"conflicting primary metadata for '{label}'"))
        values[label] = value
    return values, findings


def validate_metadata(doc):
    values, findings = metadata(doc)
    for label in METADATA_ALIASES:
        if not values.get(label):
            findings.append(Finding('ERROR', doc.path, f"missing populated primary metadata field '{label}'"))
    decision_date = values.get('Decision date', '')
    if decision_date and decision_date.lower() != 'unknown':
        try:
            date.fromisoformat(decision_date)
        except ValueError:
            findings.append(Finding('WARNING', doc.path, 'decision date must be an ISO date or Unknown'))
    verified = values.get('Last verified', '')
    if verified:
        stamp = re.search(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)', verified)
        valid_date = False
        if stamp:
            try:
                date.fromisoformat(stamp[0])
                valid_date = True
            except ValueError:
                pass
        if not (valid_date and re.search(r'\d{2}:\d{2}', verified) and
                re.search(r'Z\b|[+-]\d{2}:?\d{2}|\b(?:UTC|GMT)\b|\b[A-Z][A-Za-z_]+/[A-Za-z_]+', verified)):
            findings.append(Finding('WARNING', doc.path, 'last verified should include a valid ISO date, time, and timezone'))
    baseline = values.get('Source baseline', '').strip(' `')
    if re.fullmatch(r'(?:main|master|develop|development|trunk|HEAD|latest|refs/\S+|'
                    r'(?:feature|fix|chore|release)/\S+|(?:PR|pull request|issue)\s*#?\s*\d+)', baseline, re.I):
        findings.append(Finding('ERROR', doc.path, 'source baseline is only a mutable ref or work-item number; record an exact snapshot'))
    elif baseline.lower() in {'unknown', 'unverified', 'unavailable'}:
        findings.append(Finding('WARNING', doc.path, 'source baseline is unverified; keep affected claims explicitly unverified'))
    return findings


def section_matches(heading, role, mappings):
    if heading.level < 2:
        return False
    title = normalise(heading.title)
    if role in mappings:
        return title in mappings[role]
    if title in SECTION_ALIASES[role]:
        return True
    if role == 'overview':
        return bool(re.match(r'^part (?:i|1)\b', title))
    if role == 'reference':
        return bool(re.match(r'^part (?:ii|2)\b', title))
    return bool(re.match(r'^evidence (?:status|classification)\b', title))


def section_body(doc, heading, include_code=False):
    tokens = doc.tokens[heading.start + 3:heading.end]
    parts = []
    for i, token in enumerate(tokens):
        if token.type == 'inline' and (i == 0 or tokens[i - 1].type != 'heading_open'):
            parts.append(inline_text(token, include_code=include_code))
        elif include_code and token.type in {'fence', 'code_block'}:
            parts.append(token.content)
    return '\n'.join(parts)


def validate_structure(primary, docs, mappings):
    findings = validate_metadata(primary)
    overviews = [(primary, h) for h in primary.headings if section_matches(h, 'overview', mappings)]
    references = [(d, h) for d in docs for h in d.headings if section_matches(h, 'reference', mappings)]
    # An architecture subsection inside the overview is not the second reading layer.
    references = [(d, h) for d, h in references
                  if not any(d.path == od.path and oh.start < h.start < oh.end for od, oh in overviews)]
    evidence = [(d, h) for d in docs for h in d.headings if section_matches(h, 'evidence', mappings)]
    for label, sections in [('overview in the primary document', overviews),
                            ('architectural reference', references), ('evidence-status section', evidence)]:
        if not sections:
            findings.append(Finding('ERROR', primary.path, f'missing {label}; use --section for repository heading names'))
        for doc, heading in sections:
            if not section_body(doc, heading, include_code=True).strip():
                findings.append(Finding('ERROR', doc.path, f"empty section '{heading.title}'", heading.line))
    for doc, heading in overviews:
        if any(d.path == doc.path and h.start == heading.start for d, h in references):
            findings.append(Finding('ERROR', doc.path, 'overview and reference must identify distinct reading sections', heading.line))
    for doc, heading in evidence:
        body = section_body(doc, heading)
        if body.strip() and not re.search(
            r'\b(?:confirmed|approved decision|propos(?:al|ed)|inferen(?:ce|ces)|inferred|unresolved|unverified|'
            r'no material|none (?:identified|found)|no [^.\n]{0,80}(?:conflicts?|assumptions?|inferences?))\b', body, re.I
        ):
            findings.append(Finding('ERROR', doc.path, 'evidence section needs a classified claim or explicit none-found statement', heading.line))
    return findings


def links(doc):
    discovery = doc.frontmatter.get(DISCOVERY_KEY)
    if isinstance(discovery, dict):
        for field in DISCOVERY_POINTERS:
            if isinstance(discovery.get(field), str):
                yield discovery[field], 1
    for token in doc.tokens:
        line = token.map[0] + 1 if token.map else None
        for child in token.children or []:
            if child.type == 'link_open':
                yield child.attrGet('href'), line
            elif child.type == 'image':
                yield child.attrGet('src'), line


def local_target(doc, target, root):
    if not target or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('//'):
        return None
    parts = urlsplit(target)
    decoded = unquote(parts.path)
    if not decoded:
        resolved = doc.path
    elif decoded.startswith('/') and root is not None:
        resolved = (root / decoded.lstrip('/')).resolve()
    else:
        resolved = (doc.path.parent / decoded).resolve()
    return resolved, unquote(parts.fragment)


def validate_discovery(doc, root, *, required=False, primary=True):
    if DISCOVERY_KEY not in doc.frontmatter:
        return [Finding('ERROR', doc.path, f'missing {DISCOVERY_KEY} discovery metadata')] if required else []
    findings = []
    block = doc.frontmatter[DISCOVERY_KEY]
    if not isinstance(block, dict):
        return [Finding('ERROR', doc.path, f'{DISCOVERY_KEY} must be a mapping')]
    if not primary:
        findings.append(Finding('ERROR', doc.path, 'discovery metadata belongs in the primary document, not a companion'))
    if type(block.get('schema_version')) is not int or block['schema_version'] != 1:
        findings.append(Finding('ERROR', doc.path, 'unsupported discovery schema_version; expected integer 1'))
    if block.get('role') != 'primary':
        findings.append(Finding('ERROR', doc.path, 'discovery role must be primary'))
    unknown = set(block) - {'schema_version', 'role', *DISCOVERY_POINTERS}
    if unknown:
        findings.append(Finding('ERROR', doc.path, f'unknown discovery fields: {", ".join(sorted(map(str, unknown)))}'))
    for field in DISCOVERY_POINTERS:
        if field not in block and field != 'source_inventory':
            continue
        value = block.get(field)
        try:
            local = local_target(doc, value, root) if isinstance(value, str) and value.strip() == value else None
            if local is None or not local[1] or local[0].suffix.lower() not in MARKDOWN_SUFFIXES:
                findings.append(Finding('ERROR', doc.path, f'discovery {field} must be a local Markdown section link'))
            elif root is not None and not local[0].is_relative_to(root):
                findings.append(Finding('ERROR', doc.path, f'discovery {field} target is outside project root'))
            elif local[0].exists() and not local[0].is_file():
                findings.append(Finding('ERROR', doc.path, f'discovery {field} target is not a Markdown file'))
        except (OSError, ValueError) as exc:
            findings.append(Finding('ERROR', doc.path, f'invalid discovery {field}: {exc}'))
    return findings


def validate_links(doc, root, cache, anchors):
    findings, destinations = [], set()
    for target, line in links(doc):
        try:
            local = local_target(doc, target, root)
            if local is None:
                continue
            resolved, fragment = local
            destinations.add(resolved)
            if not resolved.exists():
                findings.append(Finding('ERROR', doc.path, f"broken local link '{target}'", line))
                continue
            if anchors == 'skip' or not fragment or not resolved.is_file() or resolved.suffix.lower() not in MARKDOWN_SUFFIXES:
                continue
            if resolved not in cache:
                cache[resolved] = parse_document(resolved, resolved.read_text(encoding='utf-8'))
            if fragment not in cache[resolved].anchors:
                findings.append(Finding('ERROR', doc.path, f"unresolved anchor '#{fragment}' in '{target}'; check renderer-specific anchors separately if applicable", line))
        except (OSError, UnicodeError, ValueError) as exc:
            findings.append(Finding('ERROR', doc.path, f"cannot check local link '{target}': {exc}", line))
    return findings, destinations


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='Primary metadata: Decision status (alias status), Implementation status, Deployment status, '
               'Decision date (date), Last verified (verified_at), Source roots (source_root), Source baseline '
               '(source_baselines). Spaces, hyphens, and underscores in field names are equivalent. '
               'Place metadata in YAML frontmatter or a header table/list before the first H2. '
               'No option verifies claims, Git snapshots, approval, or deployment.'
    )
    parser.add_argument('document', type=Path)
    parser.add_argument('--companion', type=Path, action='append', default=[], help='Repeat for linked companion documents')
    parser.add_argument('--project-root', type=Path, help='Require every supplied document inside this destination root')
    parser.add_argument('--section', action='append', default=[], metavar='ROLE=HEADING',
                        help='Map overview, reference, or evidence to a repository heading; repeat for alternatives')
    parser.add_argument('--anchors', choices=('github', 'skip'), default='github',
                        help='Check common GitHub-style fragments and HTML IDs, or delegate fragments to the renderer')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as failures')
    parser.add_argument('--require-discovery-metadata', action='store_true',
                        help='Require the versioned discovery marker on the primary; legacy documents may omit it otherwise')
    args = parser.parse_args(argv)
    args.mappings = {}
    for value in args.section:
        role, sep, heading = value.partition('=')
        if role not in SECTION_ALIASES or not sep or not heading.strip():
            parser.error('--section requires overview, reference, or evidence followed by =HEADING')
        args.mappings.setdefault(role, set()).add(normalise(heading))
    return args


def main(argv=None):
    args = parse_args(argv)
    paths = [p.expanduser().resolve() for p in [args.document, *args.companion]]
    root = args.project_root.expanduser().resolve() if args.project_root else None
    findings, docs, skipped = [], [], []
    if root is not None and not root.is_dir():
        findings.append(Finding('ERROR', root, 'destination root is not an existing directory'))
    if len(set(paths)) != len(paths):
        findings.append(Finding('ERROR', paths[0], 'duplicate document/companion paths'))
    try:
        comments, placeholders = template_markers()
    except OSError as exc:
        print(f'ERROR: cannot load bundled template: {exc}')
        return 1
    for path in dict.fromkeys(paths):
        if root is not None and not path.is_relative_to(root):
            findings.append(Finding('ERROR', path, f'document is outside project root {root}'))
            continue
        if not path.is_file():
            findings.append(Finding('ERROR', path, 'document does not exist or is not a file'))
            continue
        if path.suffix.lower() not in MARKDOWN_SUFFIXES:
            findings.append(Finding('WARNING', path, 'unsupported format; structural and link checks skipped, use destination tooling'))
            skipped.append(path)
            continue
        try:
            doc = parse_document(path, path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as exc:
            findings.append(Finding('ERROR', path, f'cannot parse document: {exc}'))
            continue
        docs.append(doc)
        findings.extend(validate_surface(doc, comments, placeholders))
    primary = next((d for d in docs if d.path == paths[0]), None)
    if primary:
        findings.extend(validate_structure(primary, docs, args.mappings))
    cache = {d.path: d for d in docs}
    destinations = {}
    for doc in docs:
        findings.extend(validate_discovery(doc, root, required=args.require_discovery_metadata and doc is primary,
                                           primary=doc is primary))
        link_findings, destinations[doc.path] = validate_links(doc, root, cache, args.anchors)
        findings.extend(link_findings)
    if primary:
        for companion in docs:
            if companion.path == primary.path:
                continue
            if companion.path not in destinations[primary.path] or primary.path not in destinations[companion.path]:
                findings.append(Finding('ERROR', companion.path, 'primary and companion must link to each other'))
    if args.anchors == 'skip':
        print('NOTE: fragment checks delegated to destination renderer; local file links still checked.')
    for finding in findings:
        print(finding.render())
    errors = sum(f.level == 'ERROR' for f in findings)
    warnings = sum(f.level == 'WARNING' for f in findings)
    if errors or (args.strict and warnings):
        print(f'FAIL: {errors} error(s), {warnings} warning(s)')
        return 1
    label = 'PARTIAL' if skipped or args.anchors == 'skip' else 'PASS'
    print(f'{label}: structural checks for {len(docs)} Markdown document(s), {len(skipped)} skipped, {warnings} warning(s). Factual and architectural review remains manual.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

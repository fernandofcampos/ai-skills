#!/usr/bin/env python3
"""End-to-end validator regression cases; run with the validator's Python environment."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

SCRIPT = Path(__file__).with_name('validate_design_document.py')
TEMPLATE = SCRIPT.parent.parent / 'assets/design-document-template.md'
META = '''| Field | Value |
| --- | --- |
| Decision status | Proposed |
| Implementation status | Not started |
| Deployment status | Not applicable |
| Decision date | Unknown |
| Last verified | 2026-10-18T12:00:00-03:00 |
| Source roots | supplied queue proposal |
| Source baseline | queue proposal version 1 |
'''
OVERVIEW = '''## Feature overview

Temporary delivery failures can occupy workers indefinitely. This proposal
bounds each job to three attempts, retaining exhausted jobs for inspection.
Worker availability is the dominant criterion. Keeping unlimited retries
would avoid an exhaustion procedure but leave worker occupancy unbounded.
No implementation or deployment is claimed; reviewers must decide the budget.
'''
REFERENCE = '''## Design details

The proposed worker increments the attempt count before delivery and retains
the job after exhaustion. A timeout leaves recipient acceptance ambiguous.
Reconsider the budget if recipient outage duration or worker occupancy changes.

### Evidence status

Proposal: the supplied brief establishes intent. Unresolved: recipient
idempotency is unverified. Confirm it before introducing operator replay.

### Document maintenance

Document ownership is unresolved. Refresh the architecture when implementation
changes; preserve accepted rationale and supersede a changed decision.
'''
BASE = '# Bounded delivery retries\n\n' + META + '\n' + OVERVIEW + '\n' + REFERENCE
DISCOVERY = {
    'schema_version': 1, 'role': 'primary',
    'source_inventory': '#bounded-delivery-retries',
    'review_map': '#design-details', 'critical_invariants': '#design-details',
    'integration_scenarios': '#design-details',
}


def marked(body=BASE, **changes):
    return '---\n' + yaml.safe_dump({'document_feature_design': {**DISCOVERY, **changes}}) + '---\n' + body


class ValidatorCases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def run_validator(self, text=BASE, *, companion=None, args=(), strict=True, filename='design.md'):
        document = self.write(filename, text)
        command = [sys.executable, str(SCRIPT), str(document), '--project-root', str(self.root)]
        if strict:
            command.append('--strict')
        if companion is not None:
            command.extend(['--companion', str(self.write('reference.md', companion))])
        result = subprocess.run(command + list(args), capture_output=True, text=True, check=False)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def good(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS:', result.stdout)

    def bad(self, result, diagnostic):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(diagnostic, result.stdout + result.stderr)

    def test_concise_proposal(self):
        self.good(self.run_validator())

    def test_valid_reference_style_links(self):
        self.write('ops.md', '# Operations\n\n## Recovery\nInspect exhausted jobs.\n')
        self.good(self.run_validator(BASE + '\nSee [operations][ops].\n\n[ops]: ops.md#recovery\n'))

    def test_broken_reference_style_link(self):
        self.bad(self.run_validator(BASE + '\nSee [operations][ops].\n\n[ops]: missing.md\n'), 'broken local link')

    def test_inline_code_and_long_fences_are_examples(self):
        examples = '\n`[link](missing.md)` and `[Feature name]` are syntax.\n\n````markdown\n```text\n# Example title\n```\n[link](missing.md)\n````\n'
        self.good(self.run_validator(BASE + examples))

    def test_comments_cannot_supply_missing_overview(self):
        doc = BASE.replace(OVERVIEW, '<!--\n' + OVERVIEW + '\n-->\n')
        self.bad(self.run_validator(doc), 'missing overview in the primary')

    def test_html_and_case_sensitive_anchors(self):
        self.good(self.run_validator(BASE + '\n<a id="RecoveryPoint"></a>\n\nSee [recovery](#RecoveryPoint).\n'))
        self.bad(self.run_validator(BASE + '\n<a id="RecoveryPoint"></a>\n\nSee [recovery](#recoverypoint).\n'), 'unresolved anchor')

    def test_duplicate_heading_and_hyphen_fragments(self):
        extra = '\n### retry--budget\n\nFirst.\n\n### retry--budget-1\n\nSecond.\n\n### retry--budget\n\nThird.\n\n[First](#retry--budget), [second](#retry--budget-1), [third](#retry--budget-2).\n'
        self.good(self.run_validator(BASE + extra))

    def test_template_part_heading_fragments(self):
        doc = BASE.replace('## Feature overview', '## Part I — Feature and decision overview')
        doc = doc.replace('## Design details', '## Part II — Architectural reference')
        self.good(self.run_validator(doc + '\n[Overview](#part-i--feature-and-decision-overview)\n'))

    def test_nested_evidence_subheadings(self):
        doc = BASE.replace('### Evidence status\n', '### Evidence status\n\n#### Remaining questions\n')
        self.good(self.run_validator(doc))

    def test_evidence_does_not_borrow_from_next_sibling(self):
        doc = BASE.replace('### Evidence status\n', '### Evidence status\n\n### Another section\n')
        self.bad(self.run_validator(doc), 'empty section')

    def test_custom_repository_headings(self):
        doc = BASE.replace('Feature overview', 'Context').replace('Design details', 'Engineering notes').replace('Evidence status', 'Evidence and caveats')
        self.good(self.run_validator(doc, args=['--section', 'overview=Context', '--section', 'reference=Engineering notes', '--section', 'evidence=Evidence and caveats']))

    def test_unknown_headings_require_explicit_mapping(self):
        self.bad(self.run_validator(BASE.replace('Feature overview', 'Context')), '--section')

    def test_layers_cannot_be_the_same_section(self):
        self.bad(self.run_validator(args=['--section', 'overview=Feature overview', '--section', 'reference=Feature overview']), 'distinct reading sections')

    def test_overview_architecture_subsection_is_not_the_reference_layer(self):
        overview = OVERVIEW + '\n### Architecture\n\nQueue to worker to recipient.\n'
        self.bad(self.run_validator('# Retry decision\n\n' + META + '\n' + overview + '\n### Evidence status\n\nProposal only.\n'), 'missing architectural reference')

    def test_diagram_only_reference_is_nonempty(self):
        doc = '# Retry decision\n\n' + META + '\n' + OVERVIEW + '\n## Design details\n\n```mermaid\nflowchart LR\n  Queue --> Worker\n```\n\n## Evidence status\n\nProposal only.\n'
        self.good(self.run_validator(doc))

    def test_valid_split_primary_and_companion(self):
        primary = '# Retry decision\n\n' + META + '\n' + OVERVIEW + '\n## Decision\n\nPropose three attempts, then retain the job.\n\n[Details](reference.md).\n'
        companion = '# Retry reference\n\n[Decision](design.md).\n\n' + REFERENCE
        self.good(self.run_validator(primary, companion=companion))

    def test_companion_cannot_supply_primary_overview(self):
        primary = '# Retry decision\n\n' + META + '\n[Details](reference.md).\n'
        companion = '# Retry reference\n\n[Decision](design.md).\n\n' + OVERVIEW + '\n' + REFERENCE
        self.bad(self.run_validator(primary, companion=companion), 'missing overview in the primary')

    def test_companion_cannot_supply_primary_metadata(self):
        primary = '# Retry decision\n\n' + OVERVIEW + '\n[Details](reference.md).\n'
        companion = '# Retry reference\n\n' + META + '\n[Decision](design.md).\n\n' + REFERENCE
        self.bad(self.run_validator(primary, companion=companion), 'missing populated primary metadata')

    def test_companions_link_back(self):
        self.bad(self.run_validator(BASE + '\n[Details](reference.md).\n', companion='# Retry reference\n\nExtra detail.\n'), 'must link to each other')

    def test_yaml_metadata_and_renderer_title(self):
        yaml = '''---
title: Bounded retries
status: Proposed
implementation_status: Not started
deployment_status: Not applicable
date: Unknown
verified_at: 2026-10-18T12:00:00-03:00
source_roots:
  - supplied proposal
source_baseline: proposal version 1
---
'''
        self.good(self.run_validator(yaml + OVERVIEW + '\n' + REFERENCE))

    def test_bold_list_metadata(self):
        fields = ['Decision status: Proposed', 'Implementation status: Not started', 'Deployment status: Not applicable',
                  'Decision date: Unknown', 'Last verified: 2026-10-18T12:00:00-03:00', 'Source roots: supplied proposal', 'Source baseline: proposal version 1']
        items = '\n'.join('- **' + v.split(':', 1)[0] + ':**' + v.split(':', 1)[1] for v in fields)
        self.good(self.run_validator('# Retry design\n\n' + items + '\n\n' + OVERVIEW + '\n' + REFERENCE))

    def test_malformed_yaml_is_reported(self):
        self.bad(self.run_validator('---\nstatus: [broken\n---\n' + BASE), 'invalid YAML')

    def test_branch_and_work_item_numbers_are_not_baselines(self):
        for baseline in ['main', 'HEAD', 'PR #123', 'feature/retries']:
            with self.subTest(baseline=baseline):
                self.bad(self.run_validator(BASE.replace('queue proposal version 1', baseline)), 'mutable ref or work-item')

    def test_exact_revision_and_retained_working_tree_snapshot(self):
        self.write('snapshot.patch', 'Synthetic scoped patch for this structural fixture.\n')
        value = 'queue-service commit ' + 'a1' * 20 + '; working tree snapshot [patch](snapshot.patch), SHA-256 ' + 'b2' * 32 + '; affected path src/worker.py'
        self.good(self.run_validator(BASE.replace('queue proposal version 1', value)))

    def test_date_only_verification_is_reviewable_warning(self):
        doc = BASE.replace('2026-10-18T12:00:00-03:00', '2026-10-18')
        self.bad(self.run_validator(doc), 'time, and timezone')
        self.assertEqual(self.run_validator(doc, strict=False).returncode, 0)

    def test_local_link_queries_parentheses_and_spaces(self):
        self.write('notes (final).md', '# Notes\n\n## Recovery\nInspect jobs.\n')
        self.good(self.run_validator(BASE + '\n[Notes](<notes (final).md?view=raw#recovery>)\n'))

    def test_root_relative_and_image_links(self):
        self.write('assets/flow.svg', '<svg/>')
        self.good(self.run_validator(BASE + '\n![Flow](/assets/flow.svg)\n'))
        self.bad(self.run_validator(BASE + '\n![Flow](/assets/missing.svg)\n'), 'broken local link')

    def test_missing_cross_document_fragment(self):
        self.write('ops.md', '# Operations\n')
        self.bad(self.run_validator(BASE + '\n[Recovery](ops.md#recovery)\n'), 'unresolved anchor')

    def test_renderer_delegation_is_explicitly_partial(self):
        result = self.run_validator(BASE + '\n[Custom](#renderer-generated)\n', args=['--anchors', 'skip'])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('PARTIAL:', result.stdout)
        self.bad(self.run_validator(BASE + '\n[Missing](missing.md#custom)\n', args=['--anchors', 'skip']), 'broken local link')

    def test_unsupported_format_never_reports_pass(self):
        result = self.run_validator('not Markdown', filename='design.rst', strict=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn('PARTIAL:', result.stdout)
        self.assertNotIn('PASS:', result.stdout)
        self.bad(self.run_validator('not Markdown', filename='design.rst'), 'unsupported format')

    def test_outside_root_including_symlink(self):
        outside = self.write('elsewhere/doc.md', BASE)
        root = self.root / 'allowed'
        root.mkdir()
        (root / 'doc.md').symlink_to(outside)
        result = subprocess.run([sys.executable, str(SCRIPT), str(root/'doc.md'), '--project-root', str(root)], capture_output=True, text=True)
        self.bad(result, 'outside project root')

    def test_untouched_template_is_not_a_deliverable(self):
        self.bad(self.run_validator(TEMPLATE.read_text()), 'leftover template')

    def test_template_placeholders_inside_examples_are_not_leftovers(self):
        self.good(self.run_validator(BASE + '\nExample placeholder syntax: `[Feature name]`.\n'))

    def test_discovery_marker_navigates_existing_sections(self):
        self.good(self.run_validator(marked(), args=['--require-discovery-metadata']))

    def test_legacy_document_remains_valid_but_marker_can_be_required(self):
        self.good(self.run_validator(BASE))
        self.bad(self.run_validator(BASE, args=['--require-discovery-metadata']), 'missing document_feature_design')

    def test_marker_example_or_nested_key_is_not_discovery_metadata(self):
        example = BASE + '\n```yaml\n' + marked().split('---\n')[1] + '```\n'
        nested = '---\ncustom:\n  document_feature_design:\n    schema_version: 1\n---\n' + BASE
        for body in [example, nested]:
            with self.subTest(body=body):
                self.good(self.run_validator(body))
                self.bad(self.run_validator(body, args=['--require-discovery-metadata']), 'missing document_feature_design')

    def test_discovery_marker_must_be_mapping(self):
        for value in ['null', '[]', 'ready']:
            with self.subTest(value=value):
                self.bad(self.run_validator('---\ndocument_feature_design: ' + value + '\n---\n' + BASE), 'must be a mapping')

    def test_discovery_schema_version_is_exact_integer(self):
        for version in [True, 2, '1', None]:
            with self.subTest(version=version):
                self.bad(self.run_validator(marked(schema_version=version)), 'unsupported discovery schema_version')

    def test_discovery_role_and_unknown_fields(self):
        self.bad(self.run_validator(marked(role='companion')), 'role must be primary')
        self.bad(self.run_validator(marked(review_ready=True)), 'unknown discovery fields')

    def test_discovery_requires_inventory_but_other_pointers_are_optional(self):
        block = {'schema_version': 1, 'role': 'primary', 'source_inventory': '#bounded-delivery-retries'}
        self.good(self.run_validator('---\n' + yaml.safe_dump({'document_feature_design': block}) + '---\n' + BASE))
        del block['source_inventory']
        self.bad(self.run_validator('---\n' + yaml.safe_dump({'document_feature_design': block}) + '---\n' + BASE), 'source_inventory must be a local Markdown section link')

    def test_discovery_pointers_require_local_markdown_sections(self):
        for pointer in [None, [], '', ' ', '#', 'design.md', 'https://example.com/design.md#map', '//example.com/a.md#map', 'image.svg#map']:
            with self.subTest(pointer=pointer):
                self.bad(self.run_validator(marked(review_map=pointer)), 'review_map must be a local Markdown section link')

    def test_discovery_broken_files_and_fragments_are_rejected(self):
        self.bad(self.run_validator(marked(review_map='missing.md#map')), 'broken local link')
        self.bad(self.run_validator(marked(review_map='#absent')), 'unresolved anchor')

    def test_discovery_directory_is_not_a_section_target(self):
        (self.root / 'folder.md').mkdir()
        self.bad(self.run_validator(marked(review_map='folder.md#map')), 'not a Markdown file')

    def test_discovery_pointers_can_target_companion_sections(self):
        primary = '# Bounded delivery retries\n\n' + META + '\n' + OVERVIEW + '\n[Details](reference.md).\n'
        companion = '# Retry reference\n\n[Decision](design.md).\n\n' + REFERENCE
        body = marked(primary, review_map='reference.md#design-details', critical_invariants='reference.md#design-details',
                      integration_scenarios='reference.md#design-details')
        self.good(self.run_validator(body, companion=companion, args=['--require-discovery-metadata']))

    def test_companion_cannot_claim_primary_marker(self):
        companion = marked(BASE + '\n[Decision](design.md).\n')
        self.bad(self.run_validator(marked(BASE + '\n[Details](reference.md).\n'), companion=companion), 'not a companion')

    def test_discovery_pointers_cannot_escape_destination_root(self):
        outside = self.write('elsewhere/source.md', '# Sources\n\nProposal version 1.\n')
        root = self.root / 'allowed'
        root.mkdir()
        (root / 'source.md').symlink_to(outside)
        for pointer in ['../elsewhere/source.md#sources', 'source.md#sources']:
            with self.subTest(pointer=pointer):
                document = self.write('allowed/design.md', marked(source_inventory=pointer))
                result = subprocess.run([sys.executable, str(SCRIPT), str(document), '--project-root', str(root)], capture_output=True, text=True)
                self.bad(result, 'outside project root')

    def test_discovery_coexists_with_repository_yaml_metadata(self):
        body = marked().replace('---\n', '---\ntitle: Bounded delivery retries\nsidebar_position: 3\n', 1)
        self.good(self.run_validator(body, args=['--require-discovery-metadata']))

    def test_duplicate_or_merged_discovery_fields_are_rejected(self):
        cases = [
            'document_feature_design: {}\ndocument_feature_design: {}\n',
            'document_feature_design:\n  schema_version: 1\n  schema_version: 1\n',
            'document_feature_design:\n  <<: {schema_version: 1}\n  role: primary\n',
            'shared: &shared\n  document_feature_design: {}\n<<: *shared\n',
        ]
        for block in cases:
            with self.subTest(block=block):
                self.bad(self.run_validator('---\n' + block + '---\n' + BASE), 'document_feature_design')

    def test_discovery_renderer_delegation_remains_partial(self):
        result = self.run_validator(marked(review_map='#custom'), args=['--anchors', 'skip'])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('PARTIAL:', result.stdout)

    def test_invalid_encoding_is_reported_without_traceback(self):
        path = self.root / 'design.md'
        path.write_bytes(b'\xff')
        result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
        self.bad(result, 'cannot parse document')
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()

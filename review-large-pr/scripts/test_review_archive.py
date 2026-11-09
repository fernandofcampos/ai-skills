#!/usr/bin/env python3
"""Archive portability/integrity tests using small isolated local artifacts."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import review_archive as archive
from review_coverage import CoverageError


class ArchiveCases(unittest.TestCase):
    def setUp(self):
        # Durable-output rules still apply to tests; use a disposable directory
        # under the current workspace, not system temporary storage.
        self.tmp = tempfile.TemporaryDirectory(prefix='.review-archive-test-', dir=Path.cwd())
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / 'scratch'; self.root.mkdir()
        (self.root / 'batches').mkdir()
        (self.root / 'batches/trace.md').write_text('## Admission\nA supported request reaches routing.\n')
        (self.root / 'probe.py').write_text('assert 1 + 1 == 2\n')
        snap = dict(repo_root='/external/repo', target_base='a' * 40, comparison_base='a' * 40, head='b' * 40)
        ref = dict(path=str(self.root / 'batches/trace.md'), locator='Admission', claim='Connected path traced')
        self.coverage = dict(schema_version=1, snapshot=snap, files=[dict(path='router.py', evidence=[ref])])
        self.run = dict(schema_version=1, coverage=[dict(path=str(self.root / 'coverage.json'), snapshot=snap)],
                        installed_skill_snapshot=[dict(path='/installed/SKILL.md', sha256='c' * 64)],
                        investigations=[dict(evidence=[ref])])
        (self.root / 'coverage.json').write_text(json.dumps(self.coverage))
        (self.root / 'run.json').write_text(json.dumps(self.run))
        (self.root / 'review-record.md').write_text(
            f'# Review\n[Trace](<{self.root}/batches/trace.md#Admission>)\n[Run](run.json)\n'
            '[Source](/external/repo/router.py)\n')
        self.output = self.home / 'delivery'
        self.includes = ['coverage.json', 'batches/trace.md', 'probe.py']

    def create(self, **kwargs):
        values = dict(root=self.root, output=self.output, run='run.json',
                      report='review-record.md', includes=self.includes)
        values.update(kwargs)
        with redirect_stdout(io.StringIO()):
            return archive.create(**values)

    def test_relocation_and_scratch_deletion_preserve_evidence(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.create()
        self.assertEqual(result['snapshots'], [self.coverage['snapshot']])
        for name, content in before.items():
            self.assertEqual((self.output / 'originals' / name).read_bytes(), content)
            self.assertEqual((self.root / name).read_bytes(), content)
        run = json.loads((self.output / 'files/run.json').read_bytes())
        self.assertEqual(run['coverage'][0]['path'], 'coverage.json')
        self.assertEqual(run['coverage'][0]['snapshot'], self.coverage['snapshot'])
        self.assertEqual(run['installed_skill_snapshot'], self.run['installed_skill_snapshot'])
        self.assertNotIn(str(self.root), (self.output / 'files/review-record.md').read_text())
        relocated = self.home / 'moved'
        self.output.rename(relocated)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(relocated)

    def test_embedded_coverage_and_checkpoint_evidence_survive_relocation(self):
        self.run.update(schema_version=2,
            coverage=[dict(id='service', snapshot=self.coverage['snapshot'], record=self.coverage)],
            checkpoints=[dict(changes=dict(coverage=[dict(id='service',
                files=[dict(path='router.py', evidence=self.coverage['files'][0]['evidence'])])]))])
        (self.root / 'run.json').write_text(json.dumps(self.run))
        self.create(includes=['batches/trace.md', 'probe.py'])
        self.assertFalse((self.output / 'files/coverage.json').exists())
        data = json.loads((self.output / 'files/run.json').read_text())
        self.assertEqual(data['coverage'][0]['record']['files'][0]['evidence'][0]['path'], 'batches/trace.md')
        moved = self.home / 'relocated'; self.output.rename(moved)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(moved)

    def test_nested_checkpoint_inputs_keep_canonical_relative_evidence(self):
        (self.root / 'requests').mkdir()
        request = dict(id='verified', expected_revision=1, actor='lead', note='Completed pass',
                       coverage=[dict(id='service', files=[dict(path='router.py',
                           evidence=[dict(path='batches/trace.md', locator='Admission', claim='Connected path traced')])])])
        raw = json.dumps(request).encode()
        (self.root / 'requests/pass.json').write_bytes(raw)
        self.create(json_records=['requests/pass.json'])
        moved = self.home / 'relocated'; self.output.rename(moved)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(moved)
        self.assertEqual((moved / 'originals/requests/pass.json').read_bytes(), raw)
        portable = json.loads((moved / 'files/requests/pass.json').read_bytes())
        self.assertEqual(portable['coverage'][0]['files'][0]['evidence'][0]['path'], 'batches/trace.md')

    def test_json_fixtures_remain_byte_identical_after_relocation(self):
        fixtures = {
            'compact.json': b'{"message":"caf\xc3\xa9","n":1e0}\r\n',
            'malformed.json': b'{"unfinished":',
            'invalid-utf8.json': b'\xff',
            'evidence-shape.json': b'{"path":"missing.txt","locator":"input","claim":"fixture"}',
            'checkpoint-shape.json': b'{"id":"fixture","expected_revision":0,"actor":"test","note":"input"}',
            'run-shape.json': b'{"schema_version":1,"coverage":[{"snapshot":{},"path":"missing.json"}]}',
        }
        for name, content in fixtures.items():
            (self.root / name).write_bytes(content)
        result = self.create(includes=[*self.includes, *fixtures])
        moved = self.home / 'moved'; self.output.rename(moved)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(moved)
        for name, content in fixtures.items():
            with self.subTest(name=name):
                self.assertEqual((moved / 'originals' / name).read_bytes(), content)
                self.assertEqual((moved / 'files' / name).read_bytes(), content)
                row = next(r for r in result['files'] if r['path'] == name)
                self.assertEqual(row['original_sha256'], row['portable_sha256'])

    def test_byte_sensitive_probe_runs_in_portable_archive(self):
        (self.root / 'fixture.json').write_bytes(b'{"a":1}')
        (self.root / 'fixture_probe.py').write_text(
            'from pathlib import Path\n'
            'assert Path(__file__).with_name("fixture.json").read_bytes() == b\'{"a":1}\'\n')
        self.create(includes=[*self.includes, 'fixture.json', 'fixture_probe.py'])
        shutil.rmtree(self.root)
        for kind in ('originals', 'files'):
            result = subprocess.run([sys.executable, str(self.output / kind / 'fixture_probe.py')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_json_record_cli_rewrites_evidence_and_preserves_original(self):
        raw = json.dumps(dict(path=str(self.root / 'batches/trace.md'),
                              locator='Admission', claim='Connected path traced')).encode()
        (self.root / 'handoff.json').write_bytes(raw)
        with redirect_stdout(io.StringIO()):
            result = archive.main(['create', '--root', str(self.root), '--output', str(self.output),
                '--json-record', 'handoff.json',
                *[arg for name in self.includes for arg in ['--include', name]]])
        self.assertEqual(result, 0)
        self.assertEqual((self.output / 'originals/handoff.json').read_bytes(), raw)
        portable = json.loads((self.output / 'files/handoff.json').read_bytes())
        self.assertEqual(portable['path'], 'batches/trace.md')
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(self.output)

    def test_declared_json_record_still_rejects_invalid_json_and_missing_evidence(self):
        for raw in [b'{', b'{"path":"absent.txt","locator":"test","claim":"checked"}']:
            (self.root / 'handoff.json').write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, CoverageError)):
                self.create(json_records=['handoff.json'])
            self.assertFalse(self.output.exists())

    def test_historical_run_discovers_its_referenced_coverage(self):
        (self.root / 'older-coverage.json').write_text(json.dumps(self.coverage))
        older = dict(self.run, coverage=[dict(path='older-coverage.json', snapshot=self.coverage['snapshot'])])
        (self.root / 'prior.json').write_text(json.dumps(older))
        result = self.create(includes=[*self.includes, 'older-coverage.json'], json_records=['prior.json'])
        self.assertIn('older-coverage.json', result['json_records'])
        portable = json.loads((self.output / 'files/older-coverage.json').read_bytes())
        self.assertEqual(portable['files'][0]['evidence'][0]['path'], 'batches/trace.md')
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(self.output)

    def test_reserved_characters_remain_filename_data_in_markdown_links(self):
        filenames = {
            'trace#1.txt': 'trace%231.txt',
            'trace%20.txt': 'trace%2520.txt',
            'trace?1.txt': 'trace%3F1.txt',
            'trace:1.txt': './trace:1.txt',
            'trace caf\u00e9 (1).txt': 'trace caf\u00e9 (1).txt',
        }
        links = []
        for name, uri in filenames.items():
            (self.root / name).write_text('evidence')
            links.append(f'[Evidence](<{uri}?view=full#Result> "Saved trace")\n')
        (self.root / 'review-record.md').write_text(''.join(links))
        self.create(includes=[*self.includes, *filenames])
        moved = self.home / 'moved'; self.output.rename(moved)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(moved)
        text = (moved / 'files/review-record.md').read_text()
        self.assertEqual(len(text.splitlines()), len(filenames))
        for name, line in zip(filenames, text.splitlines()):
            with self.subTest(name=name):
                target = line.split('(<', 1)[1].split('>', 1)[0]
                url = urlsplit(target)
                self.assertEqual(url.scheme, '')
                self.assertEqual(url.netloc, '')
                self.assertEqual(unquote(url.path), name)
                self.assertEqual(url.query, 'view=full')
                self.assertEqual(url.fragment, 'Result')
                self.assertTrue(line.endswith('> "Saved trace")'))
                self.assertEqual((moved / 'files' / unquote(url.path)).read_text(), 'evidence')

    def test_legacy_archive_with_unescaped_space_still_validates(self):
        (self.root / 'extra note.txt').write_text('evidence')
        (self.root / 'review-record.md').write_text('[Evidence](<extra note.txt>)\n')
        self.create(includes=[*self.includes, 'extra note.txt'])
        manifest_path = self.output / 'archive.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['schema_version'] = 1
        manifest.pop('json_records', None)
        legacy_text = b'[Evidence](<extra note.txt>)\n'
        (self.output / 'files/review-record.md').write_bytes(legacy_text)
        for row in manifest['files']:
            if row['path'] == 'review-record.md':
                row['portable_sha256'] = archive.sha(legacy_text)
        manifest_path.write_text(json.dumps(manifest))
        moved = self.home / 'moved'; self.output.rename(moved)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(moved)

    def test_record_inventory_cannot_omit_required_records_or_add_unselected_files(self):
        self.create()
        path = self.output / 'archive.json'
        original = json.loads(path.read_bytes())
        for records in [None, [], ['run.json'], ['run.json', 'coverage.json', 'absent.json'],
                        ['run.json', 'coverage.json', 'run.json']]:
            changed = dict(original, json_records=records)
            path.write_text(json.dumps(changed))
            with self.subTest(records=records), self.assertRaises(CoverageError):
                archive.check(self.output)

    def test_tampered_original_or_portable_fails(self):
        self.create()
        for kind in ['originals', 'files']:
            path = self.output / kind / 'probe.py'
            original = path.read_bytes()
            path.write_text('different')
            with self.assertRaisesRegex(CoverageError, 'integrity'):
                archive.check(self.output)
            path.write_bytes(original)

    def test_missing_selected_structured_evidence_and_coverage_fail_before_creation(self):
        for omit in ['batches/trace.md', 'coverage.json']:
            with self.subTest(omit=omit), self.assertRaises(CoverageError):
                self.create(includes=[p for p in self.includes if p != omit])
            self.assertFalse(self.output.exists())

    def test_missing_markdown_evidence_fails(self):
        (self.root / 'review-record.md').write_text('[Results](unselected.md)')
        with self.assertRaisesRegex(CoverageError, 'Markdown'):
            self.create()

    def test_titled_inline_links_are_checked_and_preserve_titles(self):
        for title in ['"Trace title"', "'Trace title'", '(Trace title)']:
            with self.subTest(title=title):
                (self.root / 'review-record.md').write_text(
                    f'[Trace](batches/trace.md?view=full#Admission {title})\n')
                self.create()
                text = (self.output / 'files/review-record.md').read_text()
                self.assertIn(f'(<batches/trace.md?view=full#Admission> {title})', text)
                shutil.rmtree(self.output)
                (self.root / 'review-record.md').write_text(f'[Missing](absent.md {title})')
                with self.assertRaisesRegex(CoverageError, 'Markdown'):
                    self.create()
                self.assertFalse(self.output.exists())

    def test_local_sandbox_link_survives_relocation_and_missing_target_fails(self):
        (self.root / 'review-record.md').write_text(
            f'[Trace](sandbox:{self.root}/batches/trace.md "Saved trace")\n')
        self.create()
        self.assertIn('[Trace](<batches/trace.md> "Saved trace")',
                      (self.output / 'files/review-record.md').read_text())
        moved = self.home / 'moved'; self.output.rename(moved)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(moved)

    def test_sandbox_outside_root_or_relative_is_not_silently_external(self):
        for value in ['sandbox:/outside/trace.md', 'sandbox:trace.md', 'sandbox://host/trace.md',
                      f'sandbox:{self.root}/missing.md']:
            (self.root / 'review-record.md').write_text(f'[Trace]({value} "Evidence")')
            with self.subTest(value=value), self.assertRaises(CoverageError):
                self.create()
            self.assertFalse(self.output.exists())

    def relocate_trace(self):
        old = self.root / 'batches/trace.md'
        new = self.root / 'batches/relocated.md'
        old.rename(new)
        ref = dict(path=str(old), locator='Admission', claim='Connected path traced')
        self.run.update(schema_version=2,
            coverage=[dict(id='service', snapshot=self.coverage['snapshot'], record=self.coverage)],
            checkpoints=[dict(changes=dict(evidence=[ref]))],
            evidence_repairs=[dict(relocations=[dict(from_path=str(old), to_path=str(new),
                                                    sha256=archive.sha(new.read_bytes()))])])
        self.run['coverage'][0]['record']['files'][0]['evidence'][0]['path'] = str(new)
        (self.root / 'run.json').write_text(json.dumps(self.run))
        return old, new

    def test_repair_history_relocates_receipt_pointers_only_in_portable_copy(self):
        self.relocate_trace()
        before = (self.root / 'run.json').read_bytes()
        self.create(includes=['batches/relocated.md'])
        self.assertEqual((self.output / 'originals/run.json').read_bytes(), before)
        portable = json.loads((self.output / 'files/run.json').read_bytes())
        self.assertEqual(portable['checkpoints'][0]['changes']['evidence'][0]['path'], 'batches/relocated.md')
        self.assertEqual(portable['coverage'][0]['snapshot'], self.coverage['snapshot'])
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(self.output)

    def test_archive_rejects_relocation_replacement_content_mismatch(self):
        _, replacement = self.relocate_trace()
        replacement.write_text('Different contents after relocation\n')
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(CoverageError, 'Relocated evidence.*retained SHA-256'):
            self.create(includes=['batches/relocated.md'])
        self.assertFalse(self.output.exists())
        self.assertEqual({p.relative_to(self.root): p.read_bytes()
                          for p in self.root.rglob('*') if p.is_file()}, before)

    def test_same_content_old_path_and_chained_relocation_remain_portable(self):
        old, intermediate = self.relocate_trace()
        final = self.root / 'batches/final.md'
        intermediate.rename(final)
        old.write_bytes(final.read_bytes())
        self.run['evidence_repairs'].append(dict(relocations=[dict(
            from_path=str(intermediate), to_path=str(final), sha256=archive.sha(final.read_bytes()))]))
        self.run['coverage'][0]['record']['files'][0]['evidence'][0]['path'] = str(final)
        (self.root / 'run.json').write_text(json.dumps(self.run))
        before = (self.root / 'run.json').read_bytes()
        self.create(includes=['batches/final.md'])
        self.assertEqual((self.output / 'originals/run.json').read_bytes(), before)
        portable = json.loads((self.output / 'files/run.json').read_bytes())
        evidence = portable['checkpoints'][0]['changes']['evidence'][0]
        self.assertEqual(evidence, dict(path='batches/final.md', locator='Admission', claim='Connected path traced'))
        self.assertIn('[Trace](<batches/final.md#Admission>)',
                      (self.output / 'files/review-record.md').read_text())
        relocated = self.home / 'moved'; self.output.rename(relocated)
        shutil.rmtree(self.root)
        with redirect_stdout(io.StringIO()):
            archive.check(relocated)

    def test_relocation_digest_checks_captured_replacement_bytes(self):
        _, replacement = self.relocate_trace()
        retained = replacement.read_bytes()
        replacement.write_text('Mismatched bytes captured for packaging\n')
        original_aliases = archive.relocation_aliases
        def restore_after_capture(run):
            replacement.write_bytes(retained)
            return original_aliases(run)
        with patch.object(archive, 'relocation_aliases', restore_after_capture):
            with self.assertRaisesRegex(CoverageError, 'Relocated evidence.*retained SHA-256'):
                self.create(includes=['batches/relocated.md'])
        self.assertFalse(self.output.exists())

    def test_code_examples_and_external_links_do_not_require_selection(self):
        (self.root / 'review-record.md').write_text(
            '# Review\n```md\n[Example](not-an-artifact.md)\n```\n'
            '`[Inline example](also-not-an-artifact.md)`\n'
            '[Remote](https://example.invalid/report)\n[Local](batches/trace.md)\n')
        self.create()
        text = (self.output / 'files/review-record.md').read_text()
        self.assertIn('[Example](not-an-artifact.md)', text)
        self.assertIn('[Local](<batches/trace.md>)', text)

    def test_nested_relative_evidence_and_space_in_markdown_link(self):
        (self.root / 'batches/extra note.md').write_text('## Extra\nA control.\n')
        (self.root / 'batches/trace.md').write_text('[Control](<extra note.md#Extra>)\n[Report](../review-record.md)\n')
        self.create(includes=self.includes + ['batches/extra note.md'])
        with redirect_stdout(io.StringIO()):
            archive.check(self.output)

    def test_out_of_root_structured_evidence_requires_staging(self):
        self.run['investigations'][0]['evidence'][0]['path'] = str(self.home / 'outside.md')
        (self.home / 'outside.md').write_text('evidence')
        (self.root / 'run.json').write_text(json.dumps(self.run))
        with self.assertRaisesRegex(CoverageError, 'outside'):
            self.create()

    def test_snapshot_mismatch_rejected(self):
        self.run['coverage'][0]['snapshot'] = dict(self.coverage['snapshot'], head='d' * 40)
        (self.root / 'run.json').write_text(json.dumps(self.run))
        with self.assertRaisesRegex(CoverageError, 'snapshot'):
            self.create()

    def test_existing_delivery_never_overwritten(self):
        self.create()
        before = (self.output / 'archive.json').read_bytes()
        with self.assertRaises(CoverageError):
            self.create()
        self.assertEqual((self.output / 'archive.json').read_bytes(), before)

    def test_temp_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(CoverageError, 'durable'):
                self.create(output=Path(tmp) / 'archive')

    def test_unsafe_paths_symlinks_and_common_secrets_rejected(self):
        (self.root / '.npmrc').write_text('registry=https://example.invalid')
        (self.root / 'link.md').symlink_to(self.root / 'batches/trace.md')
        for name in ['../outside.md', str(self.root / 'probe.py'), 'batches/../probe.py',
                     '.npmrc', '.env.production', 'link.md', 'node_modules/module.py']:
            with self.subTest(name=name), self.assertRaises(CoverageError):
                self.create(includes=self.includes + [name])
            self.assertFalse(self.output.exists())

    def test_failed_write_cleans_only_new_output(self):
        original = Path.write_bytes
        def fail(path, data):
            if path.parent.name == 'originals':
                raise OSError('simulated disk error')
            return original(path, data)
        with patch.object(Path, 'write_bytes', fail), self.assertRaises(OSError):
            self.create()
        self.assertFalse(self.output.exists())
        self.assertTrue((self.root / 'run.json').exists())

    def test_cli_check_and_invalid_json(self):
        self.assertEqual(archive.main(['create', '--root', str(self.root), '--output', str(self.output),
            *[arg for name in self.includes for arg in ['--include', name]]]), 0)
        self.assertEqual(archive.main(['check', str(self.output)]), 0)
        (self.output / 'archive.json').write_text('{')
        self.assertEqual(archive.main(['check', str(self.output)]), 1)

    def test_check_rejects_manifest_path_traversal_and_duplicates(self):
        self.create()
        path = self.output / 'archive.json'
        original = json.loads(path.read_bytes())
        for value in ['../outside', original['files'][1]['path']]:
            changed = json.loads(json.dumps(original))
            changed['files'][0]['path'] = value
            path.write_text(json.dumps(changed))
            with self.assertRaises(CoverageError):
                archive.check(self.output)


if __name__ == '__main__':
    unittest.main(verbosity=2)

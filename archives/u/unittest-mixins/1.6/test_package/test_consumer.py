"""Exercise installed unittest-mixins payload without source-tree imports."""
import importlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest


class InstalledConsumer(unittest.TestCase):
    def module(self):
        spec = importlib.util.find_spec('unittest_mixins')
        self.assertIsNotNone(spec, 'Conan-installed unittest_mixins payload is required')
        module = importlib.import_module('unittest_mixins')
        root = Path(os.environ['UNITTEST_MIXINS_PACKAGE_ROOT']).resolve()
        self.assertTrue(Path(module.__file__).resolve().is_relative_to(root))
        return module

    def test_00_installed_artifact_origin(self):
        module = self.module()
        self.assertTrue(callable(module.make_file))
        self.assertTrue(issubclass(module.TempDirMixin, unittest.TestCase))

    def test_temp_directory_unicode_binary_and_cleanup(self):
        module = self.module()
        class Fixture(module.TempDirMixin, unittest.TestCase):
            def runTest(self):
                self.make_file('nested/Unicode.txt', 'text: \u4e2d\u6587\n')
                self.make_file('nested/data.bin', bytes=b'\x00\x80\xff')
                self.assertEqual(Path('nested/Unicode.txt').read_text(encoding='utf-8'), 'text: \u4e2d\u6587\n')
                self.assertEqual(Path('nested/data.bin').read_bytes(), b'\x00\x80\xff')
        case = Fixture()
        result = unittest.TestResult()
        case.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertFalse(Path(case.temp_dir).exists())

    def test_cleanup_after_real_test_failure(self):
        module = self.module()
        class Fixture(module.TempDirMixin, unittest.TestCase):
            def runTest(self):
                self.make_file('temporary.txt', 'before failure')
                self.fail('controlled failure must still run cleanup')
        case = Fixture()
        result = unittest.TestResult()
        case.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.errors, [])
        self.assertFalse(Path(case.temp_dir).exists())

    def test_environment_restoration(self):
        module = self.module()
        name = 'UNITTEST_MIXINS_CONSUMER_VALUE'
        previous = os.environ.get(name)
        class Fixture(module.EnvironmentAwareMixin, unittest.TestCase):
            def runTest(self):
                self.set_environ(name, 'changed-by-consumer')
                self.assertEqual(os.environ[name], 'changed-by-consumer')
        result = unittest.TestResult()
        Fixture().run(result)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(os.environ.get(name), previous)

    def test_module_cleaner_restores_import_namespace(self):
        module = self.module()
        name = '_unittest_mixins_real_consumer_fixture'
        self.assertNotIn(name, sys.modules)
        cleaner = module.ModuleCleaner()
        with tempfile.TemporaryDirectory(prefix='umix-consumer-module-') as directory:
            source = Path(directory) / (name + '.py')
            source.write_text('value = 41 + 1\n', encoding='utf-8')
            spec = importlib.util.spec_from_file_location(name, source)
            fixture = importlib.util.module_from_spec(spec)
            sys.modules[name] = fixture
            try:
                spec.loader.exec_module(fixture)
                self.assertEqual(fixture.value, 42)
                cleaner.cleanup_modules()
                self.assertNotIn(name, sys.modules)
            finally:
                sys.modules.pop(name, None)

    def test_sys_path_context_restoration(self):
        module = self.module()
        original = list(sys.path)
        with module.saved_sys_path():
            sys.path.insert(0, '/temporary-consumer-path')
            self.assertNotEqual(sys.path, original)
        self.assertEqual(sys.path, original)

    def test_stream_capture_and_restoration(self):
        module = self.module()
        original_out, original_err = sys.stdout, sys.stderr
        class Fixture(module.StdStreamCapturingMixin, unittest.TestCase):
            def runTest(self):
                print('consumer-out')
                print('consumer-err', file=sys.stderr)
                self.assertIn('consumer-out', self.stdout())
                self.assertIn('consumer-err', self.stderr())
        result = unittest.TestResult()
        Fixture().run(result)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertIs(sys.stdout, original_out)
        self.assertIs(sys.stderr, original_err)

    def test_delayed_assertions_preserve_both_failures(self):
        module = self.module()
        case = module.DelayedAssertionMixin()
        with self.assertRaises(AssertionError) as caught:
            with case.delayed_assertions():
                case.assertEqual('first-a', 'first-b')
                case.assertEqual('second-a', 'second-b')
        self.assertIn('2 failed assertions', str(caught.exception))
        self.assertIn('first-a', str(caught.exception))
        self.assertIn('second-a', str(caught.exception))


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Independent real HMDFS permission-normalization/cleanup integration."""
import importlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest


class HarmonyOSHMDFSMechanism(unittest.TestCase):
    def test_normalized_mode_capability_and_mixin_cleanup(self):
        self.assertNotEqual(os.geteuid(), 0, 'Must validate real non-root HarmonyOS user semantics')
        module = importlib.import_module('unittest_mixins')
        package_root = Path(os.environ['UNITTEST_MIXINS_PACKAGE_ROOT']).resolve()
        self.assertTrue(Path(module.__file__).resolve().is_relative_to(package_root))
        mounts = Path('/proc/self/mountinfo').read_text(encoding='utf-8').splitlines()
        directory = Path(tempfile.gettempdir()).resolve()
        matches = []
        for line in mounts:
            left, right = line.split(' - ', 1)
            fields = left.split()
            mountpoint = Path(fields[4])
            if directory.is_relative_to(mountpoint):
                matches.append((len(str(mountpoint)), right.split()[0], line))
        self.assertTrue(matches, 'Actual target mount evidence is required')
        _, filesystem, mount_record = max(matches)
        self.assertEqual(filesystem, 'hmdfs', 'Independent test is specific to the real HMDFS task directory')
        self.assertIn('hmmac=genfs', mount_record)
        evidence = {}
        class Fixture(module.TempDirMixin, unittest.TestCase):
            def runTest(self):
                self.make_file('before.txt', 'created via mixin')
                requested = 0o500
                os.chmod(self.temp_dir, requested)
                observed = stat.S_IMODE(os.stat(self.temp_dir).st_mode)
                self.assertNotEqual(observed, requested, 'Validate actual HMDFS mode normalization, not ordinary POSIX denial')
                self.make_file('after-mode.txt', 'actual capability after chmod')
                self.assertEqual(Path('after-mode.txt').read_text(), 'actual capability after chmod')
                evidence.update(requested_mode=oct(requested), observed_mode=oct(observed),
                                actual_write_succeeded=True, directory=self.temp_dir)
        case = Fixture()
        result = unittest.TestResult()
        case.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertFalse(Path(case.temp_dir).exists(), 'Mixin cleanup must remove the real HMDFS directory')
        evidence.update(filesystem=filesystem, mount_record=mount_record,
                        uid=os.getuid(), cleanup_removed_directory=True)
        print('HARMONYOS_HMDFS_MECHANISM ' + json.dumps(evidence, sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)

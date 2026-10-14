#!/usr/bin/env python3
# test_package for slrn 1.0.3 - HarmonyOS consumer test.
#
# Runs two shell scripts against the installed binary:
#   test_slrn.sh       CLI contract: --help/--version output and compiled-in
#                      feature flags (+nntp, +ssl).
#   ohos_slrn_test.sh  HarmonyOS platform-specific checks: the binary must
#                      report "Operating System: OpenHarmony" via uname, the
#                      runtime S-Lang version must come from the dynamically
#                      loaded libslang.so (musl ldso chain), and a custom init
#                      file placed in $TMPDIR (HMDFS) must be honored by the
#                      embedded S-Lang config engine.
#
# Upstream ships no test suite (no check/test target in any Makefile), so
# the upstream test count is 0; all checks here are new consumer tests.
# Counting unit: independent check items (see MANIFEST.yml).
import os

from conan import ConanFile
from conan.tools.build import can_run


class SlrnTestConan(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    generators = 'VirtualRunEnv'
    test_type = 'explicit'

    def requirements(self):
        # run=True so VirtualRunEnv injects the packaged bin/ into PATH.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        dep = self.dependencies.get('slrn')
        if dep is None:
            return ''
        rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else 'bin'
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        if os.path.isdir(cand):
            return cand
        return os.path.join(dep.package_folder, 'bin')

    def _tmpdir(self):
        tmpdir = (os.environ.get('TMPDIR') or os.environ.get('TMP')
                  or os.environ.get('TEMP') or '')
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, 'tmp')
        os.makedirs(tmpdir, exist_ok=True)
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMP'] = tmpdir
        os.environ['TEMP'] = tmpdir
        os.environ['TEMPDIR'] = tmpdir
        return tmpdir

    def test(self):
        if not can_run(self):
            self.output.info('cross-building: skipping runtime execution')
            return

        bindir = self._bindir()
        self.output.info('slrn bindir=%s' % bindir)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tmpdir = self._tmpdir()
        # slrn initializes the S-Lang terminal layer even for --show-config;
        # give headless CI a sane fallback terminal and home directory.
        os.environ.setdefault('TERM', 'xterm')
        os.environ.setdefault('HOME', tmpdir)
        shell = os.environ.get('CONFIG_SHELL') or '/bin/sh'

        self.run('"%s" "%s" "%s" "%s"'
                 % (shell, os.path.join(script_dir, 'test_slrn.sh'),
                    bindir, tmpdir),
                 env='conanrun')
        self.run('"%s" "%s" "%s" "%s"'
                 % (shell, os.path.join(script_dir, 'ohos_slrn_test.sh'),
                    bindir, tmpdir),
                 env='conanrun')

#!/usr/bin/env python3
"""Conan test_package for pd-vbap — real Pd host consumer test.

The packaged artefacts are Pd plugins (`<name>.pd_linux`), so the only
meaningful check is to load them into an actual Pd engine, create the objects and
verify the DSP result.  This test does that on top of `libpd`:

  * stage the three externals next to the consumer patch (Pd resolves a class by
    looking in the patch's own directory first);
  * compile `consumer_e2e.c` (compiler from the Conan profile, R33);
  * run it with LD_PRELOAD=<libpd.so> — runtime step only.

It then runs the three upstream unit-test patches (`unittests/*-unittest.pd`)
verbatim in the packaged Pd host (`puredata`), driven by
`run_upstream_pd_tests.py`; the `testtools/unit-test-frame` those patches expect
but upstream does not ship is provided by `upstream_pd_tests/` (see its README).

Why the LD_PRELOAD: the externals relocate against Pd engine symbols
(`gensym`/`pd_error`/`class_new`); on musl a dlopen()ed library does not enter
the global symbol scope of a later dlopen(), so the host must be forced into the
process-wide scope (the equivalent of the pd binary's own `-rdynamic`).  The
injected dependency lib directory must never reach the compile/link step (it
would shadow the SDK's own libraries).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy


class PdVbapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Pd engine used as the plugin host for the consumer test.
        self.requires("libpd/0.16.1")
        # Pd host binary that runs the upstream unit-test patches.
        self.requires("puredata/0.54.1")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        ext_src = os.path.join(pkg, "lib", "pd-externals")
        libpd = self.dependencies["libpd"].package_folder
        libpd_lib = os.path.join(libpd, "lib")
        libpd_so = os.path.join(libpd_lib, "libpd.so")

        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") or "clang"
        # Writable scratch dir: the OHOS target has a read-only /tmp, so clang
        # needs an explicit TMPDIR, and the staged artefacts live here too.
        # It is wiped first: the CI destructive negative test (L1e/R34) removes
        # the package's lib/ and re-runs this test, so a stage left over from the
        # previous run would make a sabotaged package still look testable.
        stage = os.path.join(self.build_folder, "build", "consumer")
        shutil.rmtree(stage, ignore_errors=True)
        os.makedirs(stage, exist_ok=True)

        copy(self, "*.pd_linux", src=ext_src, dst=stage)
        copy(self, "*.pd", src=self.source_folder, dst=stage)

        # The test must genuinely consume the package: fail loudly if the tested
        # package does not hand us its artefacts.
        missing = [n for n in ("vbap", "rvbap", "define_loudspeakers")
                   if not os.path.isfile(os.path.join(stage, n + ".pd_linux"))]
        if missing:
            raise ConanException(
                "packaged Pd externals missing from the tested package: {}".format(missing))

        exe = os.path.join(stage, "consumer_e2e")
        # Compile step: only the header path of libpd, no LD_LIBRARY_PATH /
        # LD_PRELOAD injection (that would shadow SDK libraries).
        self.run('TMPDIR="{tmp}" {cc} -O2 -Wall -D_GNU_SOURCE -I{inc} -o {exe} {src} -lm -ldl'.format(
            tmp=stage, cc=cc, inc=os.path.join(libpd, "include", "libpd"),
            exe=exe, src=os.path.join(self.source_folder, "consumer_e2e.c")),
            cwd=stage)

        # Run step: libpd into the global symbol scope + its lib dir on the
        # loader path (runtime only).
        self.run('TMPDIR="{tmp}" LD_PRELOAD="{so}" LD_LIBRARY_PATH="{lib}" {exe} {ext} {pd} {so}'.format(
            tmp=stage, so=libpd_so, lib=libpd_lib, exe=exe, ext=stage, pd=stage),
            cwd=stage)

        # Upstream unit-test patches, run verbatim in the packaged Pd host.  The
        # runner asserts per patch: loads, no unresolved object, no failed
        # connection, no host error, and the frame echoes the expected test name.
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder, "bin", "pd")
        if not os.path.isfile(pd_bin):
            raise ConanException("Pd host binary missing: %s" % pd_bin)
        self.run('TMPDIR="{tmp}" {py} {script} --pd "{pd}" --externals "{ext}" '
                 '--tests "{tests}" --work "{work}"'.format(
                     tmp=stage, py=sys.executable,
                     script=os.path.join(self.source_folder, "run_upstream_pd_tests.py"),
                     pd=pd_bin, ext=ext_src,
                     tests=os.path.join(self.source_folder, "upstream_pd_tests"),
                     work=os.path.join(stage, "pd-tests")),
                 cwd=stage)

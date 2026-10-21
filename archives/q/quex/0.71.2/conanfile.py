#!/usr/bin/env python3
"""Conan recipe -- quex 0.71.2 (Python lexical analyzer generator).

Quex generates directly-coded lexical analyzers in C/C++ with Unicode
support. Upstream ships pure Python sources (quex/ package plus
quex-exe.py entry point); there is no configure/CMake build step.
This recipe installs the Python engine under share/quex and provides
a bin/quex wrapper that sets QUEX_PATH for the user.

Upstream test audit (0.71.2 zip, 2021-05-03, 1799 entries):
  top-level holds quex-exe.py, quex/, demo/ (430 example files), manpage/,
  README and unit_test_results.txt (0 bytes in this zip, not a harness).
  There is no tests/ or test/ directory, no `make check` target and no
  ctest/pytest registration. 11 test-*.py drivers live under
  quex/engine/analyzer/examine/TEST-later/ but the "-later" suffix is
  upstream's own disabled marker (hwut only scans TEST dirs) and the hwut
  runner is not shipped, so they cannot run as pytest/ctest/make check.
  algebra/TESTS holds a helper/essay fragment only, code_base/TESTS holds
  generator scripts, demo/C and demo/Cpp are ready-to-build examples
  (each with Makefile/CMakeLists that build a pre-generated lexer.c),
  not automated assertions.
  Conclusion: no runnable upstream suite to execute in build();
  build() runs a --help smoke plus a source-tree audit and emits a
  no_tests marker. Functional coverage lives in test_package.
"""

import json
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QuexConan(ConanFile):
    name = "quex"
    version = "0.71.2"
    description = "Lexical analyzer generator for C/C++ (Unicode supported)"
    license = "MIT"
    homepage = "https://quex.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lexer", "lexical-analyzer", "code-generator", "unicode")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "quex supports Linux/OHOS native builds, got %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _python(self):
        for cand in (
            os.environ.get("HMBS_PYTHON3"),
            self.conf.get("user.hmbs:python_path", check_type=str),
        ):
            if cand and os.path.isfile(cand):
                return cand
        return "python3"

    def build(self):
        exe = os.path.join(self.source_folder, "quex-exe.py")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration("quex-exe.py missing in source tree")
        py = self._python()
        # Smoke: entry point must print help without traceback.
        # quex-exe.py requires QUEX_PATH to locate the quex/ package and
        # code_base templates. In the unpacked source tree the install root
        # is source_folder itself (holds quex-exe.py + quex/).
        os.environ["QUEX_PATH"] = self.source_folder
        self.run('QUEX_PATH="%s" %s "%s" --help' % (self.source_folder, py, exe))
        # Source-tree audit: upstream 0.71.2 ships hwut-based developer
        # material but NO runnable automated suite out of the box.
        # Evidence collected deterministically with os.walk (lists only,
        # no stdout string counting):
        #  - quex/engine/analyzer/examine/TEST-later/: 11 test-*.py drivers
        #    + helper.py + hwut-info.dat. The directory suffix "-later" is
        #    upstream's own marker for deferred/disabled tests: hwut only
        #    scans directories named TEST, so TEST-later is never picked up
        #    by a plain `hwut` run. Each driver needs `hwut` (external
        #    runner, not shipped in the zip) plus a shape argument and
        #    GOOD/ reference comparison; it cannot run as `pytest`/`ctest`
        #    /`make check`.
        #  - quex/engine/state_machine/algebra/TESTS/: essay-pickled-dfas.py
        #    (fragment referencing undefined names, no test entry) plus
        #    helper.py only; no runnable driver remains (hwut-info excludes
        #    test-cut_in.py which is absent from the zip).
        #  - quex/code_base/TESTS/: generator scripts
        #    (code_base_instatiation.py, generate-TestAnalyzer.py) plus
        #    test_c fixtures, not test drivers.
        #  - unit_test_results.txt: 0 bytes in the 0.71.2 zip (empty log,
        #    not a harness).
        #  - demo/C and demo/Cpp: ready-to-build examples with
        #    Makefile/CMakeLists around pre-generated lexer.c, no
        #    TESTS/ctest/pytest registration.
        import shutil
        later_drivers = []
        algebra_py = []
        codebase_py = []
        hwut_infos = []
        demo_makefiles = []
        for root, _dirs, files in os.walk(self.source_folder):
            rel = os.path.relpath(root, self.source_folder).replace(os.sep, "/")
            for fn in files:
                low = fn.lower()
                if low == "hwut-info.dat":
                    hwut_infos.append(rel + "/" + fn)
                if "test-later" in rel.lower() and low.startswith("test-") and low.endswith(".py"):
                    later_drivers.append(rel + "/" + fn)
                elif rel.endswith("state_machine/algebra/TESTS") and low.endswith(".py"):
                    algebra_py.append(fn)
                elif "/code_base/TESTS" in rel and low.endswith(".py"):
                    codebase_py.append(rel + "/" + fn)
                if rel.startswith("demo/") and fn in ("Makefile", "CMakeLists.txt"):
                    demo_makefiles.append(rel + "/" + fn)
        unit_path = os.path.join(self.source_folder, "unit_test_results.txt")
        try:
            unit_size = os.path.getsize(unit_path)
        except OSError:
            unit_size = -1
        hwut_bin = shutil.which("hwut")
        self.output.info("quex upstream audit: TEST-later drivers=%d (%s)" % (len(later_drivers), ",".join(sorted(later_drivers)[:3])))
        for hit in sorted(later_drivers)[:12]:
            self.output.info("quex audit TEST-later (disabled, needs hwut): %s" % hit)
        self.output.info("quex upstream audit: algebra/TESTS py=%s hwut-info=%s" % (sorted(algebra_py), len([h for h in hwut_infos if "algebra" in h])))
        self.output.info("quex upstream audit: code_base/TESTS py=%d hwut-info total=%d demo build files=%d unit_test_results.txt bytes=%d hwut on PATH=%s" % (len(codebase_py), len(hwut_infos), len(demo_makefiles), unit_size, bool(hwut_bin)))
        result = {
            "status": "no_tests",
            "framework": "custom",
            "command": "%s quex-exe.py --help + source audit (hwut TEST-later disabled / no runnable harness)" % py,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "quex 0.71.2 has no runnable suite: 11 test-*.py live under TEST-later (upstream-disabled suffix, hwut-only, runner not shipped); algebra/TESTS holds helper/essay fragment only; code_base/TESTS holds generators; unit_test_results.txt is 0 bytes; demo/ holds examples only (see test_package/MANIFEST.yml audit)",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        src = self.source_folder
        dst_share = os.path.join(self.package_folder, "share", "quex")
        copy(self, "quex-exe.py", src=src, dst=dst_share, keep_path=False)
        copy(self, "*.py", src=os.path.join(src, "quex"), dst=os.path.join(dst_share, "quex"), keep_path=True)
        # Runtime C/C++ templates and helpers live under quex/code_base.
        copy(self, "*", src=os.path.join(src, "quex", "code_base"), dst=os.path.join(dst_share, "quex", "code_base"))
        copy(self, "COPYRIGHT.txt", src=src, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "MIT-License.txt", src=src, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # bin/quex wrapper: sets QUEX_PATH then delegates to python3.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "quex")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write('QUEX_BIN_DIR="$(cd "$(dirname "$0")" && pwd)"\n')
            f.write('QUEX_SHARE="${QUEX_BIN_DIR}/../share/quex"\n')
            f.write('export QUEX_PATH="${QUEX_SHARE}"\n')
            f.write('exec python3 "${QUEX_SHARE}/quex-exe.py" "$@"\n')
        try:
            st = os.stat(wrapper)
            os.chmod(wrapper, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass
        try:
            exe = os.path.join(dst_share, "quex-exe.py")
            st = os.stat(exe)
            os.chmod(exe, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define("QUEX_PATH", os.path.join(self.package_folder, "share", "quex"))

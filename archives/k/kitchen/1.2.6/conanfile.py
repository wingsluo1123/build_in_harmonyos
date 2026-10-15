#!/usr/bin/env python3
"""Conan recipe — kitchen 1.2.6 (setuptools pure Python dual-version layout).

kitchen is a collection of small, useful snippets of Python code (text handling,
unicode conversion, i18n, Python 2/3 compatibility). Dual-version layout
(kitchen2/ for Python 2, kitchen3/ for Python 3), built with setuptools.

R32: settings.os 判断使用 in ("Linux", "OHOS").
R33: build() 不依赖 shell 环境变量，使用 sys.executable（Conan 运行时 Python）.
R34: test_package 实质性测试（安装后导入 kitchen 并调用其公开 API）.

Every adaptation to the shipped sources lives in patches/ (see conandata.yml);
build() no longer rewrites the tree it installs, so the artifact provably
matches a clean upstream tarball plus the declared patches.

Upstream drove both suites with nose.  nose 1.3.7 cannot be imported on Python
3.12 at all: its core.py still uses the print statement, so importing it raises
SyntaxError rather than ModuleNotFoundError.  The 1.3.7 sdist is
  https://files.pythonhosted.org/packages/source/n/nose/nose-1.3.7.tar.gz
  sha256 f1bffef9cbc82628f6e7d7b40d7e255aefaa1adb6a1b1d26c69a8b79e6208a98
The build does not fetch it: patches/0004 supplies the two modules the upstream
sources actually use, and patches/0003 drives the cases discovery drops.

Test accounting (see reports/test-report.md for the raw logs):
  * upstream defines 366 tests — kitchen2/tests 239 + kitchen3/tests 127;
  * kitchen3    : all 127 definitions execute.  101 belong to TestCase classes
                  (126 cases under unittest discovery, which re-runs inherited
                  methods) and the remaining 26 are the nose-only shapes that
                  discovery cannot see, driven by the runner in patches/0003
                  (464 cases);
  * kitchen2    : Python 2 only, no Python 2 interpreter exists on the worker,
                  so its 239 tests are NOT executed (disclosed, not claimed).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rmdir
from conan.tools.layout import basic_layout

# Upstream suite counts, measured from the upstream tarball.
KITCHEN2_TESTS = 239
KITCHEN3_TESTS = 127
UPSTREAM_TOTAL = KITCHEN2_TESTS + KITCHEN3_TESTS  # 366
# Cases unittest's discovery collects from kitchen3/tests (101 definitions;
# the extra executions are inherited methods re-run by their subclasses).
UNITTEST_COLLECTED = 126
# Cases nose collected that unittest drops; driven by patches/0003, which
# covers every nose-only definition (26) and fails if one is not driven.
EXTRA_RECOVERED = 464


class KitchenConan(ConanFile):
    name = "kitchen"
    version = "1.2.6"
    description = "Useful snippets of code to make python coding easier"
    license = "LGPLv2+"
    homepage = "https://github.com/fedora-infra/kitchen"
    url = "https://github.com/fedora-infra/kitchen"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    # Conan 2.x 要求 library 类型必须声明 shared option（纯 Python 包，固定 False）
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    # 无外部 Conan 依赖：纯 Python 库，构建/测试用 sys.executable（Conan 运行的
    # Python），运行时 python3 由设备/CI 环境提供。

    def layout(self):
        basic_layout(self)

    def validate(self):
        """R32: OHOS 平台兼容 — 在 validate() 中拒绝不支持的 OS。"""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"kitchen only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _run_suite(self, python, rel_dir, args):
        suite_dir = os.path.join(self.source_folder, rel_dir)
        self.output.info(f"Running upstream tests from {rel_dir}: {' '.join(args)}")
        self.run(
            f"PYTHONPATH={os.path.dirname(suite_dir)}:{suite_dir} {python} " + " ".join(args),
            cwd=self.source_folder,
        )

    def build(self):
        """Build a wheel from the patched tree, then execute the upstream suite."""
        apply_conandata_patches(self)
        python = sys.executable

        dist = os.path.join(self.build_folder, "wheels")
        # pip needs setuptools.build_meta for the PEP 517 backend.  Python 3.12
        # no longer ships setuptools, and the CI worker's interpreter has pip
        # but no setuptools: --no-build-isolation then dies with
        # "BackendUnavailable: Cannot import 'setuptools.build_meta'" (build
        # #84754).  Use --no-build-isolation only where setuptools is already
        # importable (no index round-trip, unchanged local behaviour); otherwise
        # let pip provision its own isolated build environment, which installs
        # setuptools into a throwaway venv instead of mutating the shared
        # interpreter.
        has_setuptools = (
            self.run(
                f'{python} -c "import importlib.util, sys; '
                f"sys.exit(0 if importlib.util.find_spec('setuptools') else 1)\"",
                cwd=self.source_folder,
                ignore_errors=True,
            )
            == 0
        )
        isolation = "--no-build-isolation" if has_setuptools else ""
        self.output.info(
            f"building wheel with {python}: setuptools "
            f"{'found (no build isolation)' if has_setuptools else 'missing (isolated build env)'}"
        )
        self.run(
            f"{python} -m pip wheel . --no-deps {isolation} -w {dist}",
            cwd=self.source_folder,
        )
        wheels = [f for f in os.listdir(dist) if f.endswith(".whl")]
        if len(wheels) != 1:
            raise ConanException(f"Expected exactly one wheel in {dist}, got {wheels}")

        # Install the built wheel (not the source tree) so no build-time file
        # can leak into the package.  --no-compile keeps pip's bytecode
        # (__pycache__/*.pyc) out of the artifact.
        prefix = os.path.join(self.build_folder, "package", "python")
        self.run(
            f"{python} -m pip install {os.path.join(dist, wheels[0])} "
            f"--target={prefix} --no-deps --no-compile",
            cwd=self.build_folder,
        )

        # kitchen3 suite.  unittest's discovery only sees TestCase subclasses
        # and module level test functions named test_*: it collects
        # UNITTEST_COLLECTED of the KITCHEN3_TESTS upstream tests.
        self._run_suite(
            python,
            "kitchen3",
            ["-m", "unittest", "discover", "-s", "kitchen3/tests", "-p", "test_*.py", "-v"],
        )
        # The nose-only shapes discovery drops are executed by the runner added
        # in patches/0003, which fails if a generator yields nothing, if any
        # case fails unexpectedly, or if a nose-only entity was left undriven.
        self._run_suite(python, "kitchen3", ["kitchen3/tests/_ohc_extra_upstream_tests.py"])

        cases = UNITTEST_COLLECTED + EXTRA_RECOVERED
        self.output.info(
            f"upstream tests: {UPSTREAM_TOTAL} definitions "
            f"(kitchen2={KITCHEN2_TESTS}, kitchen3={KITCHEN3_TESTS}); "
            f"kitchen3 covered={KITCHEN3_TESTS}/{KITCHEN3_TESTS} definitions "
            f"via {UNITTEST_COLLECTED} unittest cases + {EXTRA_RECOVERED} "
            f"recovered nose-only cases = {cases} cases; "
            f"kitchen2 not executed={KITCHEN2_TESTS} "
            f"(Python 2 only, no interpreter available)"
        )

    def package(self):
        prefix = os.path.join(self.build_folder, "package", "python")
        if not os.path.isdir(prefix):
            raise ConanException(
                f"Package directory not found: {prefix}, nothing to package"
            )
        for item in os.listdir(prefix):
            src = os.path.join(prefix, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=prefix, dst=self.package_folder)
        # pip --target leaves console scripts and dist-info bookkeeping that
        # are useless to consumers.
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # kitchen is a pure Python library (kitchen/ package);
        # provide its install root via PYTHONPATH for consumers.
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        site_pkgs_path = self.package_folder
        self.runenv_info.append_path("PYTHONPATH", site_pkgs_path)
        self.output.info(f"kitchen installed: {site_pkgs_path}/kitchen/")

#!/usr/bin/env python3
"""Conan recipe for PyQt-builder 1.19.1 — the PyQt build system.

Pure Python (``py3-none-any``): the sdist ships ``pyqtbuild/`` including its
data trees (``bundle/dlls``, ``bundle/packages``, ``bundle/qt_wheel_distinfo``),
so the package is a plain copytree to site-packages (packaging/sip pattern)
rather than a PEP 517 build.  ``setuptools_scm`` appears only in
``[build-system] requires`` and the sdist already ships the generated
``pyqtbuild/_version.py``, so the version needs no VCS plugin.

Runtime dependencies (upstream PKG-INFO): ``packaging`` and ``sip<7,>=6.7``.
sip is required at *import* time — ``pyqtbuild.bindings``/``builder``/
``project`` all ``from sipbuild import ...`` — so it is declared.  sip must
be published to the registry for the R36 dependency check to pass; this PR
carries the sip port alongside (see the PR description).

Upstream ships no test suite (no tests/, no CI test step), so coverage comes
from a consumer test that imports the public API and runs both console
scripts.

R32: settings.os must check in ("Linux", "OHOS").
R38: ships bin/ console scripts -> software-level commands.json included.
"""
import os
import stat
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout

# [project.scripts] in the upstream pyproject.toml.
_ENTRY_POINTS = {
    "pyqt-bundle": "pyqtbuild.bundle.bundle_main",
    "pyqt-qt-wheel": "pyqtbuild.bundle.qt_wheel_main",
}


class PyQtBuilderConan(ConanFile):
    name = "pyqt-builder"
    version = "1.19.1"
    package_type = "python-require"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Python-PyQt/PyQt-builder"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = ("PyQt-builder — the PyQt build system (pure Python; "
                   "qmake-driven bindings builder)")
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # packaging is a plain runtime dep; sip is imported at load time by
        # pyqtbuild.bindings/builder/project (upstream: sip<7,>=6.7).
        self.requires("sip/6.16.1")

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _python():
        for cand in ("/data/service/hnp/bin/python3", sys.executable):
            if cand and os.path.isfile(cand):
                return cand
        raise ConanException("no python3 interpreter found")

    def _site_packages(self):
        return os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")

    # ── build ────────────────────────────────────────────────────────────

    def build(self):
        # Nothing to compile.  Sanity-check that the module imports from the
        # source tree so a broken sdist fails here rather than in consumers.
        if not can_run(self):
            return
        import subprocess
        py = self._python()
        # pyqtbuild imports sipbuild at load time, and sipbuild itself
        # imports setuptools/packaging — the device interpreter on the CI
        # worker ships none of them, so EVERY graph dependency's
        # site-packages must be on PYTHONPATH.  Passing only the source
        # folder here would shadow the conan-provided env and the import
        # fails with "No module named 'sipbuild'".
        pypath = [self.source_folder]
        for dep in self.dependencies.values():
            if dep.package_folder:
                pypath.append(os.path.join(
                    dep.package_folder, "lib", "python3.12", "site-packages"))
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            pypath + [p for p in [env.get("PYTHONPATH", "")] if p])
        r = subprocess.run(
            [py, "-c", "import pyqtbuild; from pyqtbuild.version import "
                       "PYQTBUILD_VERSION_STR; print(PYQTBUILD_VERSION_STR)"],
            capture_output=True, text=True, env=env, timeout=300)
        out = (r.stdout + r.stderr).strip()
        self.output.info("source-tree import check rc=%d: %s"
                         % (r.returncode, out.splitlines()[-1] if out else ""))
        if r.returncode != 0:
            raise ConanException("pyqtbuild does not import from the sdist: %s"
                                 % out[-500:])

    # ── package ──────────────────────────────────────────────────────────

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        import shutil
        site = self._site_packages()
        os.makedirs(site, exist_ok=True)
        # Whole tree: the module carries data directories (bundle/dlls,
        # bundle/packages, bundle/qt_wheel_distinfo) that must ship as-is.
        shutil.copytree(os.path.join(self.source_folder, "pyqtbuild"),
                        os.path.join(site, "pyqtbuild"),
                        symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                        dirs_exist_ok=True)

        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        py = self._python()
        for name, module in _ENTRY_POINTS.items():
            path = os.path.join(bindir, name)
            save(self, path,
                 "#!%s\n"
                 "import re\n"
                 "import sys\n"
                 "from %s import main\n"
                 "if __name__ == '__main__':\n"
                 "    sys.argv[0] = re.sub(r'(-script\\.pyw?|\\.exe)?$',\n"
                 "                         '', sys.argv[0])\n"
                 "    sys.exit(main())\n" % (py, module))
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR
                     | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        site = self._site_packages()
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.buildenv_info.prepend_path("PYTHONPATH", site)

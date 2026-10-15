#!/usr/bin/env python3
"""Conan recipe for pox 0.3.7 — utilities for filesystem exploration and
automated builds (pure Python, uqfoundation).

HarmonyOS (aarch64) adaptation.  pox is a pure-Python distribution: it is
installed with ``pip wheel`` and unpacked into the package site-packages,
then exposed to consumers through the run environment's PYTHONPATH (same
shape as snakeviz / aiohttp-fast-zlib).

Build notes:
* Upstream ships a real pytest suite (``pox/tests/test_utils.py`` and
  ``pox/tests/test_shutils.py``); ``build()`` runs it for real (R51).
* One upstream assertion cannot hold here: ``test_shutils`` walks
  ``rootdir()`` — ``/`` — which this sandbox refuses to list (EACCES on
  musl/OHOS), so patch 0001 walks the (listable) working directory
  instead.  The assertion itself is untouched and still exercises
  ``walk(folders=True)``.
* ``username()`` returns ``$USER`` which is numeric here; the upstream
  test only compares it against ``homedir()``, so no change is needed.

R32: settings.os must check in ("Linux", "OHOS").
R38: no bin/ executables are shipped -> no commands.json is required.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# The python minor used by the OHOS python3 (site-packages layout).
PY_MINOR = "3.12"

# Stdlib fallback runner for the upstream test suite.  Both upstream test
# modules are plain assert-based functions (no pytest imports, no fixtures),
# so executing them directly runs the exact same assertions; an AssertionError
# propagates and exits non-zero exactly like the pytest run would.
_UPSTREAM_TEST_RUNNER = r'''
"""Stdlib runner for the upstream pox tests (pytest unavailable fallback)."""
import importlib
import os
import sys

sys.path.insert(0, os.getcwd())  # cwd is the source folder -> import pox.tests

for modname, funcname in (("pox.tests.test_utils", "test_utils"),
                          ("pox.tests.test_shutils", "test_shutils")):
    mod = importlib.import_module(modname)
    getattr(mod, funcname)()
    print("%s.%s OK" % (modname, funcname))
print("UPSTREAM-TESTS-OK (stdlib runner)")
'''


class PoxConan(ConanFile):
    name = "pox"
    version = "0.3.7"
    description = ("pox — utilities for filesystem exploration and automated "
                   "builds (pure Python)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/uqfoundation/pox"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure-Python wheel: Conan 2 has no "python" package type and "library"
    # would demand a shared/static artifact (snakeviz / aiohttp-fast-zlib
    # precedent).
    package_type = "build-scripts"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pox is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # sdist ships a plain setup.py; build in-source.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        python3 = shutil.which("python3")
        if not python3:
            raise ConanException("python3 is required to build pox")

        # 1) Wheel the distribution (no runtime deps to resolve).
        # Build isolation must stay ON: the CI python does not ship setuptools,
        # and pyproject.toml declares build-backend "setuptools.build_meta", so
        # disabling isolation fails with
        #   BackendUnavailable: Cannot import 'setuptools.build_meta'
        # Letting pip provision the backend is what the repo's other pure-Python
        # packages (snakeviz, aiohttp-fast-zlib) do on the same worker.  Retries
        # cover the CDN hiccups seen on this network.
        self.run('"%s" -m pip wheel . --no-deps --retries 5 --timeout 120 '
                 '-w dist' % python3, cwd=self.source_folder)

        # 2) Run the real upstream pytest suite (R51).
        #
        # The suite asserts homedir()/username() consistency and walks
        # homedir()/.. looking for the user entry, and findpackage() recurses
        # into $HOME.  The sandbox's real HOME ("/storage/Users/currentUser")
        # sits under "/storage/Users", which is NOT listable (EPERM), and the
        # real $USER is a bare uid ("100"), so those assertions cannot hold
        # against ambient state.  Run the suite against a controlled, writable
        # HOME whose basename is the username: every assertion then exercises
        # the same code paths with consistent, real values.
        user = "ohos"
        home_parent = os.path.join(self.build_folder, "test-home")
        home = os.path.join(home_parent, user)
        tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(home, exist_ok=True)
        os.makedirs(tmp, exist_ok=True)

        env = Environment()
        env.define("HOME", home)
        env.define("USER", user)
        env.define("LOGNAME", user)
        env.define("TMPDIR", tmp)

        # pytest availability is environment-dependent: the dev box ships it,
        # the CI worker's python3 does not ("No module named pytest").  Three
        # tiers so the upstream suite always runs (R51):
        #   1. ambient pytest, as before;
        #   2. pip install pytest into a build-local --target dir from a PyPI
        #      mirror (never touches the worker's site-packages);
        #   3. a stdlib runner: both upstream test modules are plain
        #      assert-based functions with no pytest imports or fixtures, so
        #      executing them directly runs the same assertions; any failure
        #      propagates and the process exits non-zero.
        import subprocess
        probe = subprocess.run([python3, "-c", "import pytest"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        has_pytest = probe.returncode == 0
        pytest_libs = os.path.join(self.build_folder, "pytest-libs")
        runner_path = None
        if not has_pytest:
            self.output.warning(
                "pytest is not importable with %s; installing it into a "
                "build-local directory (worker site-packages untouched)"
                % python3)
            self.run(
                '"%s" -m pip install --retries 3 --timeout 60 '
                '--index-url https://pypi.tuna.tsinghua.edu.cn/simple '
                '--target "%s" pytest' % (python3, pytest_libs),
                ignore_errors=True)
            has_pytest = (os.path.isdir(os.path.join(pytest_libs, "pytest"))
                          and os.path.isdir(os.path.join(pytest_libs, "_pytest")))
            if has_pytest:
                env.prepend_path("PYTHONPATH", pytest_libs)
            else:
                self.output.warning(
                    "pip install pytest failed too; falling back to the "
                    "stdlib runner (same assertions, no pytest)")
                runner_path = os.path.join(
                    self.build_folder, "_run_upstream_tests.py")
                with open(runner_path, "w", encoding="utf-8") as fh:
                    fh.write(_UPSTREAM_TEST_RUNNER)

        self.output.info("upstream pytest HOME=%s USER=%s" % (home, user))
        with env.vars(self).apply():
            if runner_path is None:
                self.run('"%s" -m pytest pox/tests -q' % python3,
                         cwd=self.source_folder)
            else:
                self.run('"%s" "%s"' % (python3, runner_path),
                         cwd=self.source_folder)

    def package(self):
        import glob
        dist = os.path.join(self.source_folder, "dist")
        wheels = glob.glob(os.path.join(dist, "*.whl"))
        if not wheels:
            raise ConanException("pip wheel produced no wheel in %s" % dist)
        site = os.path.join(self.package_folder, "lib",
                            "python" + PY_MINOR, "site-packages")
        os.makedirs(site, exist_ok=True)
        # Unpack the wheel payload (zip) into site-packages.
        import zipfile
        for whl in wheels:
            with zipfile.ZipFile(whl) as zf:
                zf.extractall(site)
        if not os.path.isdir(os.path.join(site, "pox")):
            raise ConanException("pox package missing from %s" % site)
        for extra in ("LICENSE", "README.md"):
            src = os.path.join(self.source_folder, extra)
            if os.path.isfile(src):
                dst = os.path.join(self.package_folder, "licenses", extra)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        site = os.path.join(self.package_folder, "lib",
                            "python" + PY_MINOR, "site-packages")
        # Consumers import pox straight from the payload -> PYTHONPATH.
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.define_path("POX_PACKAGE_ROOT", site)
        self.conf_info.define("user.pox:sitedir", site)

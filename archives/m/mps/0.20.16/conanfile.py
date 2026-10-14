#!/usr/bin/env python3
"""Conan recipe for mps 0.20.16 (setuptools, pure Python CLI)."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MpsConan(ConanFile):
    name = "mps"
    version = "0.20.16"
    description = "Search, Stream and Download MP3"
    license = "GPL-3.0-only"
    homepage = "https://github.com/np1/mps"
    url = "https://github.com/np1/mps"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mps supports Linux and OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _python3(self):
        return os.environ.get("HMBS_PYTHON3", "python3")

    def _ensure_setuptools(self):
        import subprocess
        python = self._python3()
        # Probe first: avoid mutating the system interpreter when setuptools
        # is already importable (common on HMBS/CI images).
        try:
            subprocess.run([python, "-c", "import setuptools"],
                           cwd=self.source_folder, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=60)
            return
        except Exception:
            pass
        # PEP 668 (externally-managed-environment, e.g. Homebrew python on
        # the HMBS preflight host) rejects bare `pip install` to the system
        # interpreter. --break-system-packages is the documented bypass for
        # this build-time-only bootstrap; fall back to a plain install for
        # older pip that does not know the flag.
        try:
            self.run(
                "%s -m pip install --break-system-packages setuptools --quiet" % python,
                cwd=self.source_folder)
        except Exception:
            self.run("%s -m pip install setuptools --quiet" % python,
                     cwd=self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        python = self._python3()
        self._ensure_setuptools()
        ret = self.run("%s setup.py build" % python, cwd=self.source_folder)
        if ret != 0:
            raise ConanException("setup.py build failed with exit code %d" % ret)
        import json as _hmbs_json
        _hmbs_data = {
            "status": "no_tests",
            "framework": "pytest",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "mps 0.20.16 upstream ships no test suite: sdist has no tests/test directory, no test_*.py, no pytest/unittest registration (see test_package/MANIFEST.yml audit)",
        }
        _hmbs_msg = "HMBS_UPSTREAM_TEST_RESULT=" + _hmbs_json.dumps(_hmbs_data)
        print(_hmbs_msg, flush=True)
        self.output.info(_hmbs_msg)

    def package(self):
        ret = self.run("%s setup.py install --prefix=%s" % (self._python3(), self.package_folder),
                        cwd=self.source_folder)
        if ret != 0:
            raise ConanException("setup.py install failed with exit code %d" % ret)
        # Normalize the console script location: `setup.py install --prefix`
        # lands scripts in <prefix>/bin on most interpreters, but Homebrew /
        # framework / Debian-patched Pythons may use <prefix>/local/bin or
        # another scheme. test_package requires bin/mps, so relocate any
        # installed `mps` script found elsewhere under the package folder.
        import shutil
        dest_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dest_bin, exist_ok=True)
        want = os.path.join(dest_bin, "mps")
        if not os.path.isfile(want):
            found = None
            for root, _dirs, files in os.walk(self.package_folder):
                if "mps" in files:
                    cand = os.path.join(root, "mps")
                    # Skip the destination itself and egg-info metadata dirs.
                    if os.path.abspath(cand) == os.path.abspath(want):
                        continue
                    if ".egg-info" in cand or ".dist-info" in cand:
                        continue
                    found = cand
                    break
            if found:
                self.output.info("package: relocating console script %s -> %s" % (found, want))
                shutil.copy2(found, want)
        if not os.path.isfile(want):
            # Last resort: setuptools did not emit a script at all (e.g.
            # `install` shim behavior change). Generate an equivalent
            # console-script wrapper calling the real entry point
            # `mps = mps_pkg.main:main` so the packaged CLI stays runnable.
            self.output.warning("package: no installed `mps` script found; generating bin/mps wrapper")
            with open(want, "w", encoding="utf-8", newline="\n") as f:
                f.write("#!/usr/bin/env python3\n"
                        "import sys\n"
                        "from mps_pkg.main import main\n"
                        "if __name__ == '__main__':\n"
                        "    sys.exit(main())\n")
        try:
            os.chmod(want, 0o755)
        except OSError:
            # HMDFS/true-machine may not support chmod (HMBS_CAP_CHMOD=0);
            # the test only needs the file present, exec bit is best-effort.
            pass
        self.output.info("package: console script ready: %s" % want)
        for doc in ("README.rst", "PKG-INFO"):
            try:
                copy(self, doc, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
            except Exception:
                continue

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        import sys
        pyver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib", pyver, "site-packages"))

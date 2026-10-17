#!/usr/bin/env python3
"""Conan test_package for puf 1.0.0 — CLI smoke + functional HTTP fetch test.

puf is an application (single `puf` executable), so there is no library to
link; instead test.sh substantively invokes the packaged binary:
  * `puf -h` prints the full usage table (real option-parsing path)
  * bare `puf` prints short usage and exits 2 (argument handling)
  * a real loopback HTTP fetch with content-check (puf's core function)
The Python interpreter needed for the local HTTP server is resolved here
(as root/Python code, no shell-substitution pitfalls) and passed to
test.sh as argv; puf's bindir is likewise resolved from package_folder.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class PufTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv injects bin/ of the consumed package into
        # PATH so the `puf` binary resolves in the isolated test env.
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            return
        # Locate the installed puf binary.
        puf_dep = self.dependencies.get("puf")
        if puf_dep is None:
            raise RuntimeError("puf dependency not found in test graph")
        try:
            rel = puf_dep.cpp_info.bindirs[0] if puf_dep.cpp_info.bindirs else "bin"
        except Exception:
            rel = "bin"
        bin_dir = rel if os.path.isabs(rel) else os.path.join(
            puf_dep.package_folder, rel)
        self.output.info("puf package_folder=%s bindir=%s"
                         % (puf_dep.package_folder, bin_dir))

        # Seed a writable TMPDIR (HMBS injects one; fall back to a local tmp).
        tmpdir = (os.environ.get("TMPDIR")
                  or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["TEMPDIR"] = tmpdir
        os.environ.setdefault("XDG_CACHE_HOME", tmpdir)

        # Python for the hermetic loopback HTTP server (HMBS_PYTHON3 path
        # preferred, else PATH lookup). Resolved here as root-level Python,
        # avoiding shell command-substitution pitfalls in test.sh.
        python = os.environ.get("HMBS_PYTHON3") or ""
        if not python:
            python = shutil.which("python3") or ""
        self.output.info("test python interpreter: %s" % (python or "<none>"))

        script = os.path.join(self.source_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # Quote args defensively (paths may contain spaces).
        self.run('"%s" "%s" "%s" "%s"' % (shell, script, bin_dir, python),
                 env="conanrun")
        self.output.info("puf test_package: OK")

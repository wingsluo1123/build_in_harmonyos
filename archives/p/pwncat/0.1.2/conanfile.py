#!/usr/bin/env python3
"""Conan recipe — pwncat 0.1.2 (pure Python, stdlib-only) for HarmonyOS aarch64.

pwncat is "netcat on steroids": a netcat replacement with firewall/IDS/IPS
evasion, bind and reverse shells, port forwarding and PSE (Pwncat Scripting
Engine) support, fully scriptable from Python. Upstream ships exactly one
payload — the executable script ``bin/pwncat`` — plus a man page and docs.
``setup.py`` declares ``scripts=["bin/pwncat"]`` and ``install_requires=[]``,
so there is nothing to compile and no runtime dependency to declare.

Adaptation notes
----------------
* **No source patch is needed.** ``bin/pwncat`` is pure Python 3 stdlib and runs
  unmodified on the OHOS aarch64 runtime. Measured with the full upstream
  integration suite: 63/72 scripts (506/515 executed rounds) pass on the OHOS
  runtime once two *test-harness* shims are supplied (toybox ``ps`` BSD syntax
  and the missing ``::1 localhost`` alias). Neither touches the shipped script.
  The 9 remaining scripts fail for environment/harness reasons only — 4 hardcode
  ``www.google.com:80`` (no outbound internet here), 2 trip a harness
  ``grep ERROR`` false positive, 3 are the revshell-double variants of the CnC
  self-inject test (2 abort in ``create_remote_tmpfile``, 1 never completes its
  handshake) while the plain-peer and one delayed variant of that same test pass.
  See reports/test-report.md. The recipe is therefore a straight "install the
  script" recipe.

* **PyPI sdist, not the GitHub tag tarball.** The immutable PyPI sdist is what
  ``pip install pwncat==0.1.2`` installs and carries an authoritative sha256;
  the GitHub tag tarball's checksum cannot be verified from this environment
  (only mirror proxies are reachable). The sdist omits ``tests/``, so the
  upstream suite was run from the full GitHub ``v0.1.2`` tree during adaptation
  rather than from the recipe source.

* **No C/C++ and no build system.** No compiler is used and no build system is
  invoked; ``build()`` for an interpreted application is "does the shipped
  script parse and does its CLI entry point run on this interpreter".
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class PwncatConan(ConanFile):
    name = "pwncat"
    version = "0.1.2"
    description = ("Netcat on steroids with firewall/IDS evasion, bind and "
                   "reverse shells and port forwarding (pure Python PSE)")
    license = "MIT"
    homepage = "https://pwncat.org/"
    url = "https://github.com/cytopia/pwncat"

    # The artifact is the executable script bin/pwncat.
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def configure(self):
        # Pure Python: the payload is independent of the OHOS release, so drop
        # os.version from the package id (and avoid requiring it in the profile).
        self.settings.rm_safe("os.version")

    def export_sources(self):
        # No patches are declared (conandata.yml has no `patches` key): pwncat is
        # pure stdlib Python and runs unmodified on OHOS, so there is no patches/
        # directory. The standard hooks are kept so the recipe shape stays uniform
        # with the rest of the archive — both are no-ops here.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        script = os.path.join(self.source_folder, "bin", "pwncat")
        if not os.path.isfile(script):
            raise ConanException("pwncat script missing from source tree: " + script)
        with open(script, encoding="utf-8") as handle:
            shebang = handle.readline().strip()
        if not shebang.startswith("#!") or "python3" not in shebang:
            raise ConanException("unexpected pwncat shebang: " + shebang)
        # Building an interpreted application == proving the shipped script runs
        # on this interpreter: --version imports the module and drives the CLI
        # entry point, --help exercises the full argparse surface.
        self.run("'{}' '{}' --version".format(sys.executable, script))
        self.run("'{}' '{}' --help".format(sys.executable, script))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        target = os.path.join(bin_dir, "pwncat")
        shutil.copy2(os.path.join(self.source_folder, "bin", "pwncat"), target)
        os.chmod(target, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []

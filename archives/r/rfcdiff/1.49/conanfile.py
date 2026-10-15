#!/usr/bin/env python3
"""Conan recipe for rfcdiff 1.49 — diff two Internet-Drafts / RFCs.

rfcdiff is one self-contained bash script (with embedded awk programs). It
strips page headers/footers from two text drafts and renders the changes as a
side-by-side HTML diff, a changebar text file, a plain diff or a wdiff view.
There are no compilation units and no build system, and no Conan
dependencies: the runtime needs `bash`, `awk`, `diff`, `sed`, `grep`, `tr`,
`cp`, `mv`, `tar` — operating-system tools, not packages. `wdiff` (word-level
diff), `wget` (http/ftp arguments) and a web browser (`--browse`) are optional
and detected at run time by the script itself.

HarmonyOS adaptation (patches/0001-rfcdiff.patch,
3 one-line changes):
  1. shebang `#!/bin/bash` -> `#!/data/service/hnp/bin/bash`. HarmonyOS has no
     `/bin/bash`; the bash interpreter lives under /data/service/hnp/bin
     (knowledge entry E165). The script needs bash (`$(< file)`, `echo -en`,
     `==` in `[ ]`), so /system/bin/sh is not an option.
  2. work directory `/tmp/rfcdiff-$$` -> `${TMPDIR:-/tmp}/rfcdiff-$$`.
     `/tmp` is read-only on HarmonyOS (E002); upstream aborts with
     "Failed to create temporary directory" there.
  3. `--keep` branch `cd /tmp` -> `cd "${workdir%/*}"` so the packed
     workfiles are created next to the work directory instead of in /tmp.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class RfcdiffConan(ConanFile):
    name = "rfcdiff"
    version = "1.49"
    description = ("Show changes between two Internet-Drafts or RFCs as "
                   "side-by-side HTML, changebars, plain diff or wdiff")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ietf-tools/rfcdiff"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("diff", "rfc", "internet-draft", "ietf", "bash", "script", "ohos")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # No compilation: the upstream artifact is a finished bash script.
        apply_conandata_patches(self)

        script = os.path.join(self.source_folder, "rfcdiff")
        if not os.path.isfile(script):
            raise ConanException("upstream rfcdiff script missing from source archive")

        # Fail early if the portability patch did not land: the OHOS shebang
        # is what makes the installed tool directly executable on the device.
        with open(script, "r", encoding="utf-8") as fh:
            shebang = fh.readline().strip()
        if shebang != "#!/data/service/hnp/bin/bash":
            raise ConanException(f"unexpected shebang after patching: {shebang!r}")
        self.output.info("Validated patched rfcdiff script; no compilation required")

    def package(self):
        copy(self, "rfcdiff", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "rfcdiff"),
             keep_path=False)

        # Best-effort exec bit: on HMDFS (HarmonyOS) chmod is frequently
        # ignored or normalised, so the tests fall back to an explicit
        # interpreter instead of asserting on the permission bits.
        binary = os.path.join(self.package_folder, "bin", "rfcdiff")
        try:
            os.chmod(binary, 0o755)
        except OSError as exc:  # pragma: no cover - defensive
            self.output.warning(f"chmod on {binary} failed: {exc}")

    def package_id(self):
        # Pure script: independent of arch/compiler/build_type. `os` is kept
        # because the packaged script carries a HarmonyOS-specific shebang.
        del self.info.settings.arch
        del self.info.settings.compiler
        del self.info.settings.build_type

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

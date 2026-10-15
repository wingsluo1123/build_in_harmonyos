#!/usr/bin/env python3
"""Conan recipe for semtag 0.2.0 — semantic version tagging for Git, in Bash.

semtag is a single, self-contained Bash script: no compilation units and no
build system. It derives the next version from the Git tags of the current
repository (getlast / getfinal / getcurrent / final / candidate / beta / alpha)
and can create the annotated tag itself. The runtime needs `bash` (>= 4.3: it
uses associative arrays, namerefs and mapfile) and `git`; both are operating
system tools rather than Conan packages, so the recipe has no requires.

HarmonyOS adaptation (patches/0001-semtag.patch — one hunk):
  shebang `#!/usr/bin/env bash` -> `#!/data/service/hnp/bin/bash`. HarmonyOS
  has no /usr/bin/env (knowledge entry E037) and bash lives under the hnp
  prefix. Without this the installed tool cannot be exec'd directly, which is
  what the software-level commands.json declaration expects.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class SemtagConan(ConanFile):
    name = "semtag"
    version = "0.2.0"
    description = ("Semantic version tagging for Git: bumps and creates "
                   "version tags from the repository's own tag history")
    license = "Apache-2.0"
    homepage = "https://github.com/nico2sh/semtag"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("git", "semver", "versioning", "bash", "script", "ohos")

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
        # No compilation: the upstream artifact is a finished Bash script.
        apply_conandata_patches(self)

        script = os.path.join(self.source_folder, "semtag")
        if not os.path.isfile(script):
            raise ConanException("upstream semtag script missing from source archive")

        # Fail early if the portability patch did not land: the hnp bash
        # shebang is what makes the installed tool directly executable.
        with open(script, "r", encoding="utf-8") as fh:
            shebang = fh.readline().strip()
        if shebang != "#!/data/service/hnp/bin/bash":
            raise ConanException(f"unexpected shebang after patching: {shebang!r}")
        self.output.info("Validated patched semtag script; no compilation required")

    def package(self):
        copy(self, "semtag", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "semtag"),
             keep_path=False)

        # Best-effort exec bit: on HMDFS (HarmonyOS) chmod is frequently
        # ignored or normalised, so the tests invoke the script through an
        # explicit interpreter instead of relying on the permission bits.
        binary = os.path.join(self.package_folder, "bin", "semtag")
        try:
            os.chmod(binary, 0o755)
        except OSError as exc:  # pragma: no cover - defensive
            self.output.warning(f"chmod on {binary} failed: {exc}")

    def package_id(self):
        # Pure shell script: independent of arch/compiler/build_type. `os` is
        # kept because the packaged script carries a HarmonyOS-specific shebang.
        del self.info.settings.arch
        del self.info.settings.compiler
        del self.info.settings.build_type

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

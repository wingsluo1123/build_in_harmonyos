#!/usr/bin/env python3
"""Conan recipe for xcv 1.0.1 — cut/copy/paste files from the bash command line.

xcv is a single bash script (no compilation). The OHOS adaptation point is the
shebang: upstream hard-codes ``#!/bin/bash`` which does not exist on OpenHarmony
PC, so package() rewrites it to ``#!/usr/bin/env bash`` and the recipe declares
the published ``bash`` package as a runtime dependency.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XcvConan(ConanFile):
    name = "xcv"
    version = "1.0.1"
    description = "Cut, Copy and Paste files with Bash"
    license = "ISC"
    homepage = "https://github.com/busterc/xcv"
    url = "https://github.com/busterc/xcv"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bash/5.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        script = os.path.join(self.source_folder, "xcv")
        if not os.path.isfile(script):
            raise ConanException(f"xcv script not found in source: {script}")
        dest = os.path.join(bindir, "xcv")

        with open(script, "r", encoding="utf-8") as fh:
            content = fh.read()
        # OHOS has no /bin/bash; resolve bash through PATH (bash/5.3 dependency).
        if not content.startswith("#!/bin/bash\n"):
            raise ConanException("unexpected xcv shebang, expected '#!/bin/bash'")
        content = "#!/usr/bin/env bash\n" + content[len("#!/bin/bash\n"):]
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.chmod(dest, 0o755)

        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "xcv"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

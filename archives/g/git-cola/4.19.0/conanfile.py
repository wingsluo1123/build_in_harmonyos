#!/usr/bin/env python3
"""Conan recipe for git-cola — a powerful Git GUI written in Python + Qt.

git-cola is a pure Python application that uses Makefile + pip for installation.
No C/C++ compilation is needed.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class GitColaConan(ConanFile):
    name = "git-cola"
    version = "4.19.0"
    description = "Git Cola is a powerful Git GUI with a slick and intuitive user interface."
    license = "GPL-2.0"
    homepage = "https://github.com/git-cola/git-cola"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # git-cola is a pure Python app — no compilation step.
        # The "build" is handled by pip during package().

    def package(self):
        # Install Python module via pip --target
        site_packages = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        self.run(
            f'pip3 install --no-deps --no-build-isolation '
            f'--target="{site_packages}" .',
            cwd=self.source_folder,
        )

        # Create entry point scripts in bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        scripts = {
            "cola": ("cola.main", "main"),
            "git-cola": ("cola.main", "main"),
            "git-dag": ("cola.dag", "main"),
            "git-cola-sequence-editor": ("cola.sequenceeditor", "main"),
        }
        for name, (module, func) in scripts.items():
            script_path = os.path.join(bin_dir, name)
            with open(script_path, "w") as f:
                f.write(f"#!/usr/bin/env python3\n")
                f.write(f"import sys\n")
                f.write(f"from {module} import {func}\n")
                f.write(f"if __name__ == '__main__':\n")
                f.write(f"    sys.exit({func}())\n")
            os.chmod(script_path, 0o755)

        # Install desktop files, icons, docs, metainfo
        share = os.path.join(self.package_folder, "share")
        for subdir in ["applications", "icons/hicolor/scalable/apps",
                       "doc/git-cola", "metainfo"]:
            os.makedirs(os.path.join(share, subdir), exist_ok=True)

        src = self.source_folder
        copy(self, "*.desktop", src=os.path.join(src, "share", "applications"),
             dst=os.path.join(share, "applications"))
        copy(self, "git-cola.svg", src=os.path.join(src, "cola", "icons"),
             dst=os.path.join(share, "icons", "hicolor", "scalable", "apps"))
        copy(self, "*.html", src=os.path.join(src, "cola", "data"),
             dst=os.path.join(share, "doc", "git-cola"))
        copy(self, "*.xml", src=os.path.join(src, "share", "metainfo"),
             dst=os.path.join(share, "metainfo"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/python3.12/site-packages"]

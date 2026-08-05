#!/usr/bin/env python3
"""Conan recipe — diff-so-fancy 1.4.10 (Perl script, no compilation)"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class DiffSoFancyConan(ConanFile):
    name = "diff-so-fancy"
    version = "1.4.10"
    description = "Human-readable Git diff output formatter"
    license = "MIT"
    homepage = "https://github.com/so-fancy/diff-so-fancy"
    url = "https://github.com/so-fancy/diff-so-fancy"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][0]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            filename="diff-so-fancy-1.4.10.tar.gz",
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        # Fix shebang to use system perl on OHOS (R32: platform guard)
        script = os.path.join(self.source_folder, "diff-so-fancy")
        if self.settings.os in ("Linux", "OHOS"):
            replace_in_file(self, script, "#!/usr/bin/env perl", "#!/data/service/hnp/bin/perl")
        # Verify the script can be syntax-checked
        self.run(f'perl -c "{script}"')

    def package(self):
        # Copy main script
        copy(
            self,
            "diff-so-fancy",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        # Copy lib/DiffHighlight.pm
        copy(
            self,
            "DiffHighlight.pm",
            src=os.path.join(self.source_folder, "lib"),
            dst=os.path.join(self.package_folder, "bin", "lib"),
            keep_path=False,
        )
        # Make executable
        installed = os.path.join(self.package_folder, "bin", "diff-so-fancy")
        os.chmod(
            installed,
            os.stat(installed).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

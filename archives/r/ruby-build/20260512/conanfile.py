#!/usr/bin/env python3
"""Conan recipe for ruby-build 20260512 — pure Shell (Bash) script project.

ruby-build is a command-line tool for compiling and installing Ruby from source.
It is a pure Shell script project with no compilation step; "installation"
consists of copying scripts from bin/ and share/ruby-build/ to the package.

Platform adaptations for OHOS:
  1. Shebang fix: #!/bin/bash → #!/usr/bin/env bash (no /bin/bash on OHOS)
  2. No patches needed — ruby-build scripts already use portable shebangs.

R32: settings.os check uses `in ("Linux", "OHOS")` where applicable.
R28: test_package/ exists.
R34: test_package calls ruby-build --version and --list to verify real functionality.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RubyBuildConan(ConanFile):
    name = "ruby-build"
    version = "20260512"
    description = "Compile and install Ruby from source (pure Bash scripts)"
    license = "MIT"
    homepage = "https://github.com/rbenv/ruby-build"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # --- Platform adaptation: fix shebangs ---
        # Some ruby-build scripts use #!/bin/bash; fix to /usr/bin/env bash
        bin_dir = os.path.join(self.source_folder, "bin")
        if os.path.isdir(bin_dir):
            for fname in os.listdir(bin_dir):
                fpath = os.path.join(bin_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                with open(fpath, "r") as f:
                    first_line = f.readline()
                if first_line.startswith("#!/bin/bash"):
                    with open(fpath, "r") as f:
                        content = f.read()
                    content = content.replace("#!/bin/bash", "#!/usr/bin/env bash", 1)
                    with open(fpath, "w") as f:
                        f.write(content)
                    self.output.info(f"Fixed shebang: {fname}")

    def package(self):
        # Copy scripts to bin/
        src_bin = os.path.join(self.source_folder, "bin")
        if os.path.isdir(src_bin):
            copy(self, "*", src=src_bin, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
            # Ensure scripts are executable
            dst_bin = os.path.join(self.package_folder, "bin")
            for fname in os.listdir(dst_bin):
                fpath = os.path.join(dst_bin, fname)
                if os.path.isfile(fpath):
                    os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        # Copy Ruby version definitions to share/ruby-build/
        src_share = os.path.join(self.source_folder, "share", "ruby-build")
        if os.path.isdir(src_share):
            copy(self, "*", src=src_share, dst=os.path.join(self.package_folder, "share", "ruby-build"), keep_path=False)

    def package_info(self):
        # Pure script project: executables in bin/, data in share/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

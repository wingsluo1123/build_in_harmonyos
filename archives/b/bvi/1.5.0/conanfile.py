#!/usr/bin/env python3
"""Conan recipe — bvi 1.5.0 (Autotools).

bvi is a vi-like binary editor using ncurses.
On OHOS: ncurses headers are manually installed to /storage/Users/currentUser/usr/local/include.
Patches are applied via git apply (patch_tool: git) because toybox patch 0.8.12
cannot handle unified diff format correctly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BviConan(ConanFile):
    name = "bvi"
    version = "1.5.0"
    description = "bvi - vi-like binary editor"
    license = "MIT"
    homepage = "https://bvi.sourceforge.net/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        ncurses_inc = "/storage/Users/currentUser/usr/local/include"
        ncurses_lib = "/storage/Users/currentUser/usr/local/lib"
        tc.extra_cflags.append("-I.")  # find config.h in build dir
        tc.extra_cflags.append(f"-I{ncurses_inc}")
        tc.extra_ldflags.append(f"-L{ncurses_lib}")
        tc.generate()

    def build(self):
        # Apply patches using git apply (patch_tool: git in conandata.yml)
        apply_conandata_patches(self)

        # Set environment for OHOS
        os.environ["CC"] = "/data/service/hnp/bin/clang"
        os.environ["CXX"] = "/data/service/hnp/bin/clang++"
        os.environ["AWK"] = "/data/service/hnp/bin/awk"
        os.environ["MAKEINFO"] = "true"
        os.environ["TMPDIR"] = "/storage/Users/currentUser/tmp"
        os.environ["LIBS"] = "/storage/Users/currentUser/usr/local/lib/libncursesw.a"

        # Use configure --no-create + patch config.status workaround
        # Pass --host/--build to skip config.guess detection
        autotools = Autotools(self)
        autotools.configure(args=[
            "--no-create",
            "--host=aarch64-unknown-linux-gnu",
            "--build=aarch64-unknown-linux-gnu",
        ])

        # Patch config.status: fix umask 077 -> 022 for temp dirs
        config_status = os.path.join(self.build_folder, "config.status")
        if os.path.exists(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            content = content.replace(
                "exec 7>/dev/null",
                "exec 7>/dev/null\nchmod +x $tmp/out 2>/dev/null || true"
            )
            with open(config_status, "w") as f:
                f.write(content)
            self.run(config_status)

        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        build_dir = self.build_folder
        src_dir = self.source_folder

        # Copy bmore.help from source to build dir
        help_src = os.path.join(src_dir, "bmore.help")
        help_dst = os.path.join(build_dir, "bmore.help")
        if os.path.exists(help_src) and not os.path.exists(help_dst):
            shutil.copy2(help_src, help_dst)

        # Copy man pages from source to build dir
        for man in ["bvi.1", "bmore.1"]:
            man_src = os.path.join(src_dir, man)
            man_dst = os.path.join(build_dir, man)
            if os.path.exists(man_src) and not os.path.exists(man_dst):
                shutil.copy2(man_src, man_dst)
            elif not os.path.exists(man_dst):
                with open(man_dst, "w") as f:
                    f.write('.TH ' + man.replace('.1', '') + ' 1 "2024" "bvi 1.5.0"\n'
                            '.SH NAME\n' + man.replace('.1', '') + ' \\- binary editor\n')

        autotools = Autotools(self)
        autotools.install(args=["-j1", "MAKEINFO=true"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

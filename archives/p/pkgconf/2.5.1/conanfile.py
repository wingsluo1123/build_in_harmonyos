#!/usr/bin/env python3
"""Conan recipe for pkgconf 2.5.1.

pkgconf is a pkg-config replacement providing a library (libpkgconf) and
command-line tools (pkgconf, bomtool). It uses the meson build system.

R26: Static build by default (system-name library — avoids polluting /lib).
R38: Command-line tool — commands.json declared at software-level directory.
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class PkgconfConan(ConanFile):
    name = "pkgconf"
    version = "2.5.1"
    description = "pkgconf is a package compiler and configuration tool (pkg-config replacement)"
    license = "ISC"
    homepage = "https://github.com/pkgconf/pkgconf"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = "build"
        self.cpp.build.libdirs = ["lib"]
        self.cpp.build.bindirs = ["bin"]
        self.cpp.build.includedirs = ["include"]
        self.cpp.package.libdirs = ["lib"]
        self.cpp.package.bindirs = ["bin"]
        self.cpp.package.includedirs = ["include", "include/pkgconf"]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System-name libraries default to static
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Disable tests (kyua/atf-sh not available on OHOS)
        tc.project_options["tests"] = "disabled"
        tc.generate()

    def build(self):
        # Fix compiler/tool paths in generated meson native file.
        # CI profile points to /data/service/hnp/bin/clang which may not exist
        # on dev machines — replace with resolved path if invalid.
        # Always resolve ar/ranlib/strip to full paths: bare 'llvm-ar' from the
        # AR env var may not be in PATH on CI workers, causing meson to fail.
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        profile_clang = '/data/service/hnp/bin/clang'
        profile_clangxx = '/data/service/hnp/bin/clang++'

        if os.path.exists(native_file):
            clang = shutil.which('clang') or ''
            clangxx = shutil.which('clang++') or ''
            ar = shutil.which('llvm-ar') or shutil.which('ar') or ''
            ranlib = shutil.which('llvm-ranlib') or shutil.which('ranlib') or ''
            strip = shutil.which('llvm-strip') or shutil.which('strip') or ''
            with open(native_file, 'r') as f:
                content = f.read()
            # Fix compiler paths only if profile path is invalid
            if not os.path.exists(profile_clang) and clang:
                content = content.replace(profile_clang, clang)
            if not os.path.exists(profile_clangxx) and clangxx:
                content = content.replace(profile_clangxx, clangxx)
            # Always ensure ar/ranlib/strip use full paths
            if ar:
                content = content.replace("ar = 'llvm-ar'", f"ar = '{ar}'")
                content = content.replace("ar = 'ar'", f"ar = '{ar}'")
            if 'ar =' not in content and ar:
                extra_lines = f"\nar = '{ar}'"
                if ranlib:
                    extra_lines += f"\nranlib = '{ranlib}'"
                if strip:
                    extra_lines += f"\nstrip = '{strip}'"
                content = content.replace(
                    f"cpp = '{clangxx or profile_clangxx}'",
                    f"cpp = '{clangxx or profile_clangxx}'{extra_lines}"
                )
            with open(native_file, 'w') as f:
                f.write(content)

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["pkgconf"]
        self.cpp_info.includedirs = ["include", "include/pkgconf"]
        self.cpp_info.set_property("cmake_file_name", "pkgconf")
        self.cpp_info.set_property("cmake_target_name", "pkgconf::pkgconf")

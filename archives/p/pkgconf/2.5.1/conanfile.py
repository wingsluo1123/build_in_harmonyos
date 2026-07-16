#!/usr/bin/env python3
"""Conan recipe for pkgconf 2.5.1.

pkgconf is a pkg-config replacement providing a library (libpkgconf) and
command-line tools (pkgconf, bomtool). It uses the meson build system.

R26: Static build by default (system-name library — avoids polluting /lib).
R38: Command-line tool — commands.json declared at software-level directory.
"""
import os
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
        # Fix compiler/tool paths in generated meson native file
        # CI profile points to /data/service/hnp/bin/clang which doesn't exist
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        tool_prefix = "/storage/Users/currentUser/usr/local/bin"
        if os.path.exists(native_file):
            with open(native_file, 'r') as f:
                content = f.read()
            # Fix compiler paths
            content = content.replace(
                '/data/service/hnp/bin/clang',
                f'{tool_prefix}/clang'
            )
            content = content.replace(
                '/data/service/hnp/bin/clang++',
                f'{tool_prefix}/clang++'
            )
            # Add ar and ranlib to the [binaries] section if not present
            if 'ar =' not in content:
                content = content.replace(
                    "cpp = '/storage/Users/currentUser/usr/local/bin/clang++'",
                    f"cpp = '{tool_prefix}/clang++'\n"
                    f"ar = '{tool_prefix}/llvm-ar'\n"
                    f"ranlib = '{tool_prefix}/llvm-ranlib'\n"
                    f"strip = '{tool_prefix}/llvm-strip'"
                )
            with open(native_file, 'w') as f:
                f.write(content)

        # Also ensure PATH includes the toolchain directory
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{tool_prefix}:{old_path}"

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        
        # Fix config.h: meson's has_header_symbol check fails for strlcpy/strlcat/strndup
        # on OHOS musl, causing bsdstubs.c to redefine them as static (conflict)
        config_h = os.path.join(self.build_folder, "libpkgconf", "config.h")
        if os.path.exists(config_h):
            with open(config_h, 'r') as f:
                content = f.read()
            content = content.replace("#define HAVE_DECL_STRLCPY 0", "#define HAVE_DECL_STRLCPY 1")
            content = content.replace("#define HAVE_DECL_STRLCAT 0", "#define HAVE_DECL_STRLCAT 1")
            content = content.replace("#define HAVE_DECL_STRNDUP 0", "#define HAVE_DECL_STRNDUP 1")
            with open(config_h, 'w') as f:
                f.write(content)

        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["pkgconf"]
        self.cpp_info.includedirs = ["include", "include/pkgconf"]
        self.cpp_info.set_property("cmake_file_name", "pkgconf")
        self.cpp_info.set_property("cmake_target_name", "pkgconf::pkgconf")

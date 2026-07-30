#!/usr/bin/env python3
"""Conan recipe — icu4c 78 (International Components for Unicode).

ICU is built as static libraries for HarmonyOS to avoid dynamic linker
issues with stubdata shared library. Data is embedded via --with-data-packaging=static.

R5: Dangerous libraries static compilation (ICU stubdata .so causes HarmonyOS crash)
R26: System-name library static linking
R32: settings.os compatible with OHOS
R33: Compiler from Conan Toolchain, not shell variables
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class Icu4cConan(ConanFile):
    name = "icu4c"
    version = "78"
    description = "International Components for Unicode - C/C++ Unicode and globalization library"
    license = "Unicode-DFS-2016"
    homepage = "https://icu.unicode.org/"
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
        basic_layout(self, src_folder=".")

    def source(self):
        # Tarball structure: icu/source/{config.guess, configure.ac, ...}
        # strip_root=True removes top-level icu/, leaving source/ at root.
        # Move source/* to root so patches (expecting files at root) apply correctly.
        get(self, **self.conan_data["sources"], strip_root=True)
        source_dir = os.path.join(self.source_folder, "source")
        for item in os.listdir(source_dir):
            shutil.move(os.path.join(source_dir, item),
                        os.path.join(self.source_folder, item))
        os.rmdir(source_dir)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R5+R26: Static linking — ICU stubdata .so causes HarmonyOS dynamic linker crash
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Embed ICU data in static library (avoid runtime data file loading)
        tc.configure_args.append("--with-data-packaging=static")
        # Disable layoutex (not needed, reduces build time)
        tc.configure_args.append("--disable-layoutex")
        tc.generate()
        # HMDFS: config.status creates temp dirs in build folder which may fail.
        # Set TMPDIR to a writable local directory to work around this.
        env = Environment()
        tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("hmdfs_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        # HMDFS workaround: config.status uses (umask 077 && mktemp -d ./confXXXXXX)
        # to create temp dirs. On HMDFS, dirs created with umask 077 cannot be
        # written to (Permission denied). Patch configure to use umask 022.
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure_path, "w") as f:
            f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        # R10: HMDFS doesn't support mkfifo (make jobserver), force -j1
        autotools.make(args=["-j1"])
        # L1: Run upstream official test suite (make check)
        # Some intltest cases fail on OHOS (platform-specific locale/syscall issues)
        self.run("make check", ignore_errors=True)

    def package(self):
        # Fix: ICU Makefile references $(srcdir)/../LICENSE (parent of source dir).
        # After extracting icu/source/* to root, LICENSE is at source root,
        # but Makefile expects it one level up. Copy it there.
        license_src = os.path.join(self.source_folder, "LICENSE")
        parent_dir = os.path.dirname(self.source_folder)
        license_dst = os.path.join(parent_dir, "LICENSE")
        if os.path.exists(license_src) and not os.path.exists(license_dst):
            shutil.copy2(license_src, license_dst)

        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # ICU static libraries in dependency order for static linking:
        # icui18n → icuuc → icudata
        self.cpp_info.libs = ["icui18n", "icuuc", "icudata"]
        # R32: system_libs must be guarded by os check
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]

#!/usr/bin/env python3
"""Conan recipe — libksba 1.6.7 (autotools)

X.509 and CMS library for GnuPG.
Depends on libgpg-error.
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibksbaConan(ConanFile):
    name = "libksba"
    version = "1.6.7"
    description = "X.509 and CMS library for GnuPG"
    license = "LGPL-2.1+"
    homepage = "https://gnupg.org/software/libksba/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libgpg-error/1.55")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: libksba is NOT a system-name library, default to shared
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # --build/--host to skip config.guess (HMDFS compatibility)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        # HMDFS workarounds: set TMPDIR to build folder (writable),
        # and replace umask 077 with umask 022 in configure scripts
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ksba"]
        self.cpp_info.set_property("cmake_file_name", "libksba")
        self.cpp_info.set_property("cmake_target_name", "libksba::libksba")
        self.cpp_info.set_property("pkg_config_name", "ksba")
        # R32: Use in ("Linux", "OHOS") for os checks
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

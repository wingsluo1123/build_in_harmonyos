#!/usr/bin/env python3
"""Conan recipe — lhasa 0.6.0.

Lhasa provides liblhasa plus the lha command-line tool.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LhasaConan(ConanFile):
    name = "lhasa"
    version = "0.6.0"
    description = "Library and command-line tool for reading LHA/LZH archives"
    license = "ISC"
    homepage = "https://github.com/fragglet/lhasa"
    url = "https://github.com/fragglet/lhasa"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

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
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
            tc.extra_ldflags.append("-static")
        tc.configure_args.append("--prefix=/")
        tc.generate()

        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("env_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._fix_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lhasa"]
        self.cpp_info.includedirs = ["include/liblhasa-0.6.0"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "liblhasa")

    def _fix_umask(self):
        for rel in ("configure", "config.status"):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

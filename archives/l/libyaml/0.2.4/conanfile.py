#!/usr/bin/env python3
"""Conan recipe for libyaml 0.2.4 — Autotools (configure + make).

Patches:
  - config-guess-harmonyos.patch: Add HarmonyOS recognition to config.guess

Platform workarounds (in build method):
  - Fix configure/config.status umask 077 mktemp issue on HMDFS
  - Fix libtool wrapper script bash shebang for OHOS
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibyamlConan(ConanFile):
    name = "libyaml"
    version = "0.2.4"
    description = "YAML parser/emitter library"
    license = "MIT"
    homepage = "https://pyyaml.org/wiki/LibYAML"
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
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix HMDFS umask 077 issue: mktemp -d with umask 077 creates
        # directories that cannot be written to on HarmonyOS HMDFS.
        # Remove umask 077 from configure script before running it.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace(
                '(umask 077 && mktemp -d "./confXXXXXX")',
                '(mktemp -d "./confXXXXXX")'
            )
            content = content.replace(
                '(umask 077 && mkdir "$tmp")',
                '(mkdir "$tmp")'
            )
            with open(configure_path, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # Fix libtool wrapper scripts: replace '#! bash' with full path
        bash_path = shutil.which("bash") or "/data/service/hnp/bin/bash"
        tests_dir = os.path.join(self.source_folder, "tests")
        if os.path.isdir(tests_dir):
            for fn in os.listdir(tests_dir):
                fpath = os.path.join(tests_dir, fn)
                if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                    try:
                        with open(fpath, "r") as f:
                            first_line = f.readline()
                        if first_line.startswith("#! bash"):
                            self.run(f'sed -i "1s|#! bash|#! {bash_path}|" "{fpath}"')
                    except Exception:
                        pass

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["yaml"]

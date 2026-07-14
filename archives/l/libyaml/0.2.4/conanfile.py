#!/usr/bin/env python3
"""Conan recipe for libyaml 0.2.4 — Autotools (configure + make).
Source: GitHub archive (needs autoreconf to generate configure).
Platform workarounds: HMDFS umask fix, HarmonyOS config.guess, bash shebang.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibyamlConan(ConanFile):
    name = "libyaml"
    version = "0.2.4"
    description = "YAML parser/emitter library"
    license = "MIT"
    homepage = "https://pyyaml.org/wiki/LibYAML"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # Generate configure from configure.ac (GitHub archive lacks pre-generated files)
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            self.run("autoreconf -fi", cwd=self.source_folder)

        # Fix config.guess: add HarmonyOS recognition
        cg = os.path.join(self.source_folder, "config", "config.guess")
        if os.path.isfile(cg):
            with open(cg, "r") as f:
                content = f.read()
            if "HarmonyOS" not in content:
                content = content.replace(
                    'case "$UNAME_SYSTEM" in\nLinux|GNU|GNU/*)',
                    'case "$UNAME_SYSTEM" in\nHarmonyOS|HongMeng)\n\tUNAME_SYSTEM=Linux\n\tLIBC=musl\n\t;;\nLinux|GNU|GNU/*)'
                )
                with open(cg, "w") as f:
                    f.write(content)

        # Fix HMDFS umask 077 mktemp issue in configure script
        cp = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cp):
            with open(cp, "r") as f:
                content = f.read()
            content = content.replace(
                '(umask 077 && mktemp -d "./confXXXXXX")',
                '(mktemp -d "./confXXXXXX")'
            )
            content = content.replace(
                '(umask 077 && mkdir "$tmp")',
                '(mkdir "$tmp")'
            )
            with open(cp, "w") as f:
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
                            self.run('sed -i "1s|#! bash|#! {}|" "{}"'.format(bash_path, fpath))
                    except Exception:
                        pass

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["yaml"]

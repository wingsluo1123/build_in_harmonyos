#!/usr/bin/env python3
"""Conan recipe for yara 4.5.5 — Pattern matching tool for malware identification.

Build system: autotools (configure + make)
Products: libyara (library) + yara/yarac (CLI tools)
License: Apache-2.0
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YaraConan(ConanFile):
    name = "yara"
    version = "4.5.5"
    description = "Pattern matching tool for malware identification and classification"
    license = "Apache-2.0"
    homepage = "https://github.com/VirusTotal/yara"
    url = ""

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
        self._bootstrap()

        autotools = Autotools(self)
        autotools.configure()

        # Patch Makefile to prevent make from trying to regenerate autotools
        # files (aclocal.m4, Makefile.in, etc.) which requires aclocal/automake/perl
        makefile = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(makefile):
            with open(makefile, "r") as f:
                content = f.read()
            content = content.replace(
                "$(ACLOCAL_M4)",
                "# $(ACLOCAL_M4) - disabled for OHOS cross-compile"
            )
            content = re.sub(
                r"^Makefile:\s.*$",
                "# Makefile: disabled self-regen for OHOS",
                content,
                flags=re.MULTILINE
            )
            with open(makefile, "w") as f:
                f.write(content)

        autotools.make(args=["-j1"])

    def _bootstrap(self):
        """Generate configure script and set up build-aux directory."""
        src = self.source_folder

        # Fix configure.ac: comment out PKG_CHECK_MODULES (protobuf-c optional)
        configure_ac = os.path.join(src, "configure.ac")
        if os.path.exists(configure_ac):
            with open(configure_ac, "r") as f:
                content = f.read()
            content = content.replace(
                "PKG_CHECK_MODULES([PROTOBUF_C], [libprotobuf-c >= 1.0.0])",
                "# PKG_CHECK_MODULES skipped - protobuf-c optional, not available on OHOS",
            )
            with open(configure_ac, "w") as f:
                f.write(content)

        # Set up build-aux directory with auxiliary files
        build_aux = os.path.join(src, "build-aux")
        os.makedirs(build_aux, exist_ok=True)

        automake_dirs = [
            os.path.join(os.environ.get("HOME", ""), "usr/local/share/automake-1.16"),
            "/storage/Users/currentUser/usr/local/share/automake-1.16",
            "/usr/share/automake-1.16",
        ]

        aux_files = [
            "config.guess", "config.sub", "install-sh", "compile",
            "ar-lib", "missing", "test-driver", "depcomp", "py-compile",
        ]

        for aux_file in aux_files:
            target = os.path.join(build_aux, aux_file)
            if not os.path.exists(target):
                for am_dir in automake_dirs:
                    src_file = os.path.join(am_dir, aux_file)
                    if os.path.exists(src_file):
                        shutil.copy2(src_file, target)
                        os.chmod(target, 0o755)
                        break

        # ltmain.sh from libtool
        ltmain_candidates = [
            "/storage/Users/currentUser/tmp/libtool-2.4.7/build-aux/ltmain.sh",
            "/usr/share/libtool/build-aux/ltmain.sh",
            "/usr/local/share/libtool/build-aux/ltmain.sh",
        ]
        ltmain_target = os.path.join(build_aux, "ltmain.sh")
        if not os.path.exists(ltmain_target):
            for lt in ltmain_candidates:
                if os.path.exists(lt):
                    shutil.copy2(lt, ltmain_target)
                    os.chmod(ltmain_target, 0o755)
                    break

        # Run autoconf to generate configure
        self.run("autoconf -I m4", cwd=src)

        # Fix umask 077 -> 022 in configure (HMDFS permission issue)
        configure = os.path.join(src, "configure")
        if os.path.exists(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["yara"]

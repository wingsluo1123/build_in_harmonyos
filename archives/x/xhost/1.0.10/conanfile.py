#!/usr/bin/env python3
"""Conan recipe for X.Org xhost 1.0.10 (X server access-control CLI)."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XhostConan(ConanFile):
    name = "xhost"
    version = "1.0.10"
    description = "X.Org X server access-control command-line utility"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xhost"
    url = "https://gitlab.freedesktop.org/xorg/app/xhost"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xhost supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libXmu supplies libXmuu/libX11/libXau. Declare xorgproto directly
        # because the root recipe needs its xproto.pc from share/pkgconfig.
        self.requires("libxmu/1.3.1.1")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # HMFS may reject getcwd() even when chdir(path) succeeds. Preserve the
        # logical path for Autoconf, and use a writable temp directory for
        # config.guess probes. The configure patch handles config.status's own
        # relative confXXXXXX directory.
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        tmp_dir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        pc_paths = [self.generators_folder]
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                pc_paths.append(
                    os.path.join(dependency.package_folder, "lib", "pkgconfig")
                )
                pc_paths.append(
                    os.path.join(dependency.package_folder, "share", "pkgconfig")
                )
        pkg_config_path = ":".join(dict.fromkeys(pc_paths))

        # Some published X.Org .pc files contain an unre-based /usr/local prefix.
        # Add Conan's actual package include/lib directories from CppInfo as well.
        cppflags = []
        ldflags = []
        seen_cppflags = set()
        seen_ldflags = set()
        for dependency in self.dependencies.host.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            cpp_infos = [dependency.cpp_info]
            cpp_infos.extend(dependency.cpp_info.components.values())
            for cpp_info in cpp_infos:
                for directory in cpp_info.includedirs:
                    path = directory if os.path.isabs(directory) else os.path.join(package_folder, directory)
                    flag = "-I" + shlex.quote(path)
                    if os.path.isdir(path) and flag not in seen_cppflags:
                        seen_cppflags.add(flag)
                        cppflags.append(flag)
                for directory in cpp_info.libdirs:
                    path = directory if os.path.isabs(directory) else os.path.join(package_folder, directory)
                    flag = "-L" + shlex.quote(path)
                    if os.path.isdir(path) and flag not in seen_ldflags:
                        seen_ldflags.add(flag)
                        ldflags.append(flag)

        previous_pkg_config_path = os.environ.get("PKG_CONFIG_PATH")
        previous_tmpdir = os.environ.get("TMPDIR")
        previous_cppflags = os.environ.get("CPPFLAGS")
        previous_ldflags = os.environ.get("LDFLAGS")
        old_umask = os.umask(0)
        os.environ["PKG_CONFIG_PATH"] = pkg_config_path
        os.environ["TMPDIR"] = tmp_dir
        if cppflags:
            os.environ["CPPFLAGS"] = " ".join(cppflags + ([previous_cppflags] if previous_cppflags else []))
        if ldflags:
            os.environ["LDFLAGS"] = " ".join(ldflags + ([previous_ldflags] if previous_ldflags else []))
        self.output.info(f"PKG_CONFIG_PATH (scoped) = {pkg_config_path}")
        self.output.info(f"CPPFLAGS (dependency dirs) = {os.environ.get('CPPFLAGS', '')}")
        self.output.info(f"LDFLAGS (dependency dirs) = {os.environ.get('LDFLAGS', '')}")
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            # The upstream Automake tree has no TESTS/check_PROGRAMS, so this
            # target is expected to report an empty test suite (0 upstream cases).
            autotools.make(target="check")
        finally:
            os.umask(old_umask)
            if previous_pkg_config_path is None:
                os.environ.pop("PKG_CONFIG_PATH", None)
            else:
                os.environ["PKG_CONFIG_PATH"] = previous_pkg_config_path
            if previous_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = previous_tmpdir
            if previous_cppflags is None:
                os.environ.pop("CPPFLAGS", None)
            else:
                os.environ["CPPFLAGS"] = previous_cppflags
            if previous_ldflags is None:
                os.environ.pop("LDFLAGS", None)
            else:
                os.environ["LDFLAGS"] = previous_ldflags

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # xhost is a CLI application, not a linkable library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
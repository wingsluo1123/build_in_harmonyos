#!/usr/bin/env python3
"""Conan recipe for the X.Org xkill 1.0.7 command-line utility."""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XkillConan(ConanFile):
    name = "xkill"
    version = "1.0.7"
    description = "Utility for forcing the X server to close a client connection"
    license = "MIT-open-group"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xkill"
    url = "https://gitlab.freedesktop.org/xorg/app/xkill"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xkill links libXmuu and libX11. xorgproto provides xproto.pc,
        # required by upstream's configure.ac version check.
        self.requires("libx11/1.8.13", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

        # libX11's DT_NEEDED chain must be available to consumers at runtime.
        self.requires("libxcb/1.17.0", run=True)
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="xkill-1.0.7.tar.xz",
            strip_root=True,
            **self.conan_data["sources"],
        )
        # Patch the extracted tree before Conan copies it into the build folder.
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The bundled config.guess may not recognize HarmonyOS.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def _ensure_xmuu_pc_alias(self):
        """Expose the packaged libxmuu component under upstream's xmuu.pc name."""
        target = os.path.join(self.generators_folder, "xmuu.pc")
        if os.path.isfile(target):
            return

        candidates = glob.glob(os.path.join(self.generators_folder, "*xmuu*.pc"))
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                candidates.extend(
                    glob.glob(
                        os.path.join(dep.package_folder, libdir, "pkgconfig", "*xmuu*.pc")
                    )
                )
        candidates = [p for p in candidates if os.path.isfile(p)]
        if candidates:
            shutil.copyfile(candidates[0], target)
            self.output.info(f"Created xmuu.pc alias from {candidates[0]}")
            return

        # Conan's published libxmu component metadata does not use the module
        # spelling expected by xkill's upstream PKG_CHECK_MODULES call.
        dep = self.dependencies["libxmu"]
        libdir = dep.cpp_info.libdirs[0]
        includedir = dep.cpp_info.includedirs[0]
        with open(target, "w", encoding="utf-8") as pc:
            pc.write(
                "prefix={prefix}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir=${{prefix}}/{libdir}\n"
                "includedir=${{prefix}}/{includedir}\n"
                "\n"
                "Name: Xmuu\n"
                "Description: Xt-independent X11 miscellaneous utility library\n"
                "Version: 1.3.1.1\n"
                "Requires: x11\n"
                "Libs: -L${{libdir}} -lXmuu\n"
                "Cflags: -I${{includedir}}\n".format(
                    prefix=dep.package_folder,
                    libdir=libdir,
                    includedir=includedir,
                )
            )
        self.output.info("Created xmuu.pc alias from libxmu package metadata")

    def _pkg_config_path(self):
        paths = [self.generators_folder]
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                pcdir = os.path.join(dep.package_folder, libdir, "pkgconfig")
                if os.path.isdir(pcdir):
                    paths.append(pcdir)
        previous = os.environ.get("PKG_CONFIG_PATH", "")
        if previous:
            paths.append(previous)
        return os.pathsep.join(dict.fromkeys(paths))

    def build(self):
        self._ensure_xmuu_pc_alias()

        previous = os.environ.get("PKG_CONFIG_PATH")
        previous_shared_storage = os.environ.get("XKILL_HMOS_SHARED_FS")
        os.environ["PKG_CONFIG_PATH"] = self._pkg_config_path()
        self.output.info(f"PKG_CONFIG_PATH={os.environ['PKG_CONFIG_PATH']}")
        if str(self.settings.os) == "OHOS":
            # HarmonyOS shared storage creates files as file_manager; config.status
            # needs its temporary directory to retain the device user's inherited ACL.
            os.environ["XKILL_HMOS_SHARED_FS"] = "1"
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            # Automake supplies an empty generic check target here; the
            # upstream release declares no TESTS/check_PROGRAMS.
            autotools.make(args=["check"])
        finally:
            if previous is None:
                os.environ.pop("PKG_CONFIG_PATH", None)
            else:
                os.environ["PKG_CONFIG_PATH"] = previous
            if previous_shared_storage is None:
                os.environ.pop("XKILL_HMOS_SHARED_FS", None)
            else:
                os.environ["XKILL_HMOS_SHARED_FS"] = previous_shared_storage

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
        # xkill is a command-line application, not a linkable library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]

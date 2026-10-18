#!/usr/bin/env python3
"""Conan recipe for the Osmocom shared ASN.1 runtime library."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class OsmoLibasn1cConan(ConanFile):
    name = "osmo-libasn1c"
    version = "0.9.38"
    description = "Shared asn1c runtime library used by the Osmocom cellular stack"
    license = "BSD-2-Clause"
    homepage = "https://gitea.osmocom.org/cellular-infrastructure/libasn1c"
    url = "https://gitea.osmocom.org/cellular-infrastructure/libasn1c"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"osmo-libasn1c is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "osmo-libasn1c is an asn1c runtime shared library; a static "
                "override would produce object-level symbol collisions")

    def requirements(self):
        self.requires("talloc/2.4.4")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_flags(self):
        incs, libdirs, libs = [], [], []
        for dep in self.dependencies.host.values():
            for path in dep.cpp_info.includedirs:
                p = os.path.join(dep.package_folder, path)
                if p not in incs:
                    incs.append(p)
            for path in dep.cpp_info.libdirs:
                p = os.path.join(dep.package_folder, path)
                if p not in libdirs:
                    libdirs.append(p)
            for name in list(dep.cpp_info.libs or []) + list(dep.cpp_info.system_libs or []):
                if name not in libs:
                    libs.append(name)
        return incs, libdirs, libs

    def build(self):
        # This Debian orig tarball intentionally contains configure.ac and
        # Makefile.am but no generated configure script.  Automake is not
        # available on the OHOS host, so reproduce the libtool link directly.
        incs, libdirs, libs = self._dependency_flags()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        srcs = sorted(glob.glob(os.path.join(self.source_folder, "src", "*.c")))
        if len(srcs) < 40:
            raise ConanInvalidConfiguration(
                "expected the complete asn1c runtime source set, found %d files" % len(srcs))

        os.makedirs(self.build_folder, exist_ok=True)
        cmd = [
            f'"{cc}"',
            "-shared",
            "-fPIC",
            "-O2",
            "-Wall",
            "-Wextra",
            f'-I"{os.path.join(self.source_folder, "include")}"',
            f'-I"{os.path.join(self.source_folder, "include", "asn1c")}"',
        ]
        cmd += [f'-I"{path}"' for path in incs]
        cmd += [f'-L"{path}"' for path in libdirs]
        cmd += [
            "-Wl,-soname,libasn1c.so.1",
            "-o",
            "libasn1c.so.1.0.2",
        ]
        cmd += [f'"{src}"' for src in srcs]
        cmd += [f"-l{name}" for name in libs]
        cmd += ["-lm"]
        self.output.info("osmo-libasn1c link: %s" % " ".join(cmd))
        self.run(" ".join(cmd), cwd=self.build_folder, env="conanbuild")

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        copy(self, "libasn1c.so*", self.build_folder, libdir)
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "include", "asn1c"),
            os.path.join(self.package_folder, "include", "asn1c"),
        )

        target = os.path.join(libdir, "libasn1c.so.1.0.2")
        for name in ("libasn1c.so.1", "libasn1c.so"):
            path = os.path.join(libdir, name)
            try:
                if os.path.lexists(path):
                    os.remove(path)
                os.symlink("libasn1c.so.1.0.2", path)
            except OSError:
                shutil.copyfile(target, path)

        pc_dir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        save(
            self,
            os.path.join(pc_dir, "libasn1c.pc"),
            "\n".join(
                [
                    "prefix=%s" % self.package_folder,
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    "",
                    "Name: asn1c runtime library",
                    "Description: C Utility Library",
                    "Version: %s" % self.version,
                    "Libs: -L${libdir} -lasn1c -ltalloc",
                    "Cflags: -I${includedir}/ -I${includedir}/asn1c",
                    "",
                ]
            ),
        )

    def package_info(self):
        self.cpp_info.libs = ["asn1c"]
        # Public headers use both <asn1c/foo.h> from applications and
        # <foo.h> internally, matching upstream libasn1c.pc.
        self.cpp_info.includedirs = ["include", "include/asn1c"]
        self.cpp_info.set_property("cmake_file_name", "osmo-libasn1c")
        self.cpp_info.set_property("cmake_target_name", "osmo-libasn1c::osmo-libasn1c")

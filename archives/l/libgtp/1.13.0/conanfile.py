#!/usr/bin/env python3
"""Conan recipe for the Osmocom GTP library from osmo-ggsn."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class LibgtpConan(ConanFile):
    name = "libgtp"
    version = "1.13.0"
    description = "GTP protocol library between SGSN and GGSN from OsmoGGSN"
    license = "GPL-2.0-or-later"
    homepage = "https://gitea.osmocom.org/cellular-infrastructure/osmo-ggsn"
    url = "https://gitea.osmocom.org/cellular-infrastructure/osmo-ggsn"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libgtp is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "this recipe packages the upstream libgtp shared library")

    def requirements(self):
        self.requires("libosmocore/1.11.0")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="osmo-ggsn.tar.xz",
            strip_root=True,
        )

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
        for name in ("osmocore",):
            if name not in libs:
                libs.append(name)
        return incs, libdirs, libs

    def build(self):
        incs, libdirs, libs = self._dependency_flags()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        save(
            self,
            os.path.join(self.source_folder, "config.h"),
            "\n".join(
                [
                    "#define HAVE_STDINT_H 1",
                    "#define HAVE_STRING_H 1",
                    "#define HAVE_UNISTD_H 1",
                    "#define HAVE_SYS_TIME_H 1",
                    "#define HAVE_SYS_SOCKET_H 1",
                    "#define HAVE_ARPA_INET_H 1",
                    "#define HAVE_NETINET_IN_H 1",
                    "#define HAVE_NETDB_H 1",
                    "#define HAVE_STDLIB_H 1",
                    "#define HAVE_SYS_IOCTL_H 1",
                    "#define HAVE_FCNTL_H 1",
                    '#define VERSION "1.13.0"',
                    "#define PACKAGE_VERSION \"1.13.0\"",
                    "",
                ]
            ),
        )

        sources = sorted(glob.glob(os.path.join(self.source_folder, "gtp", "*.c")))
        if len(sources) != 6:
            raise ConanInvalidConfiguration(
                "expected 6 libgtp C sources, found %d" % len(sources))
        os.makedirs(self.build_folder, exist_ok=True)
        output = os.path.join(self.build_folder, "libgtp.so.11.0.0")
        command = [
            f'"{cc}"',
            "-shared",
            "-fPIC",
            "-O2",
            "-std=gnu11",
            "-fno-emulated-tls",
            "-fno-builtin",
            "-Wall",
            "-Wextra",
            "-Wno-unused-parameter",
            f'-I"{os.path.join(self.source_folder, "include")}"',
            f'-I"{os.path.join(self.source_folder, "gtp")}"',
        ]
        command += [f'-I"{path}"' for path in incs]
        command += [f'-L"{path}"' for path in libdirs]
        command += [
            "-Wl,-soname,libgtp.so.11",
            "-Wl,--no-undefined",
            f'-o"{output}"',
        ]
        command += [f'"{path}"' for path in sources]
        command += [f"-l{name}" for name in libs]
        command += ["-lm", "-lpthread", "-ldl"]
        self.output.info("libgtp link: %s" % " ".join(command))
        self.run(" ".join(command), cwd=self.build_folder, env="conanbuild")

        for link in ("libgtp.so.11", "libgtp.so"):
            path = os.path.join(self.build_folder, link)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink("libgtp.so.11.0.0", path)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        os.makedirs(libdir, exist_ok=True)
        copy(self, "libgtp.so*", self.build_folder, libdir)
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "include", "osmocom", "gtp"),
            os.path.join(incdir, "osmocom", "gtp"),
        )
        # Legacy include compatibility from upstream libgtp.pc.
        for header in ("gsn.h", "gtp.h", "gtpie.h", "pdp.h"):
            copy(
                self,
                header,
                os.path.join(self.source_folder, "include", "osmocom", "gtp"),
                incdir,
            )

        target = os.path.join(libdir, "libgtp.so.11.0.0")
        for link, link_target in (
            ("libgtp.so.11", "libgtp.so.11.0.0"),
            ("libgtp.so", "libgtp.so.11"),
        ):
            path = os.path.join(libdir, link)
            if not os.path.lexists(path):
                source = target if link_target == "libgtp.so.11.0.0" else os.path.join(libdir, link_target)
                shutil.copyfile(source, path)

        pc_dir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        save(
            self,
            os.path.join(pc_dir, "libgtp.pc"),
            "\n".join(
                [
                    "prefix=%s" % self.package_folder,
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    "",
                    "Name: OsmoGGSN GTP Library",
                    "Description: C Utility Library",
                    "Version: %s" % self.version,
                    "Libs: -L${libdir} -lgtp",
                    "Cflags: -I${includedir}/osmocom/gtp/ -I${includedir}/",
                    "Requires: libosmocore",
                    "",
                ]
            ),
        )

    def package_info(self):
        self.cpp_info.libs = ["gtp"]
        self.cpp_info.includedirs = ["include", "include/osmocom/gtp"]
        self.cpp_info.requires = ["libosmocore::osmocore"]
        self.cpp_info.set_property("cmake_file_name", "libgtp")
        self.cpp_info.set_property("cmake_target_name", "libgtp::libgtp")
        self.cpp_info.set_property("pkg_config_name", "libgtp")

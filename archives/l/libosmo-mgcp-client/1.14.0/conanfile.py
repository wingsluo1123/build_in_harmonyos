#!/usr/bin/env python3
"""Conan recipe for the Osmocom MGCP client library from osmo-mgw."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class LibosmoMgcpClientConan(ConanFile):
    name = "libosmo-mgcp-client"
    version = "1.14.0"
    description = "Osmocom Media Gateway Control Protocol client library"
    license = "AGPL-3.0-or-later"
    homepage = "https://gitea.osmocom.org/cellular-infrastructure/osmo-mgw"
    url = "https://gitea.osmocom.org/cellular-infrastructure/osmo-mgw"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libosmo-mgcp-client is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "this recipe packages the upstream MGCP client shared library")

    def requirements(self):
        self.requires("libosmocore/1.11.0")
        self.requires("libosmo-abis/2.0.0")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="osmo-mgw.tar.xz",
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
        for name in ("osmocore", "osmovty"):
            if name not in libs:
                libs.append(name)
        return incs, libdirs, libs

    def build(self):
        incs, libdirs, libs = self._dependency_flags()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        generated_include = os.path.join(
            self.build_folder, "include", "osmocom", "mgcp_client"
        )
        os.makedirs(generated_include, exist_ok=True)
        save(
            self,
            os.path.join(generated_include, "mgcp_common.h"),
            "/* Automatic copy of <osmocom/mgcp/mgcp_common.h>. */\n"
            + open(
                os.path.join(self.source_folder, "include", "osmocom", "mgcp", "mgcp_common.h"),
                encoding="utf-8",
            ).read(),
        )

        sources = sorted(
            glob.glob(
                os.path.join(
                    self.source_folder, "src", "libosmo-mgcp-client", "*.c"
                )
            )
        )
        if len(sources) != 5:
            raise ConanInvalidConfiguration(
                "expected 5 MGCP client C sources, found %d" % len(sources))

        output = os.path.join(self.build_folder, "libosmo-mgcp-client.so.14.1.0")
        command = [
            f'"{cc}"',
            "-shared",
            "-fPIC",
            "-O2",
            "-std=gnu11",
            "-fno-emulated-tls",
            "-Wall",
            "-Wextra",
            "-Wno-unused-parameter",
            f'-I"{os.path.join(self.source_folder, "include")}"',
            f'-I"{os.path.join(self.build_folder, "include")}"',
        ]
        command += [f'-I"{path}"' for path in incs]
        command += [f'-L"{path}"' for path in libdirs]
        command += [
            "-Wl,-soname,libosmo-mgcp-client.so.14",
            "-Wl,--no-undefined",
            f'-o"{output}"',
        ]
        command += [f'"{path}"' for path in sources]
        command += [f"-l{name}" for name in libs]
        command += ["-lm", "-lpthread", "-ldl"]
        self.output.info("libosmo-mgcp-client link: %s" % " ".join(command))
        self.run(" ".join(command), cwd=self.build_folder, env="conanbuild")

        for link in ("libosmo-mgcp-client.so.14", "libosmo-mgcp-client.so"):
            path = os.path.join(self.build_folder, link)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink("libosmo-mgcp-client.so.14.1.0", path)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        os.makedirs(libdir, exist_ok=True)
        copy(self, "libosmo-mgcp-client.so*", self.build_folder, libdir)

        public_headers = [
            "defs.h",
            "mgcp_client.h",
            "mgcp_client_endpoint_fsm.h",
            "mgcp_client_fsm.h",
            "mgcp_client_pool.h",
        ]
        for header in public_headers:
            copy(
                self,
                header,
                os.path.join(self.source_folder, "include", "osmocom", "mgcp_client"),
                os.path.join(incdir, "osmocom", "mgcp_client"),
            )
        copy(
            self,
            "mgcp_common.h",
            os.path.join(self.build_folder, "include", "osmocom", "mgcp_client"),
            os.path.join(incdir, "osmocom", "mgcp_client"),
        )

        target = os.path.join(libdir, "libosmo-mgcp-client.so.14.1.0")
        for link, link_target in (
            ("libosmo-mgcp-client.so.14", "libosmo-mgcp-client.so.14.1.0"),
            ("libosmo-mgcp-client.so", "libosmo-mgcp-client.so.14"),
        ):
            path = os.path.join(libdir, link)
            if not os.path.lexists(path):
                source = target if link_target == "libosmo-mgcp-client.so.14.1.0" else os.path.join(libdir, link_target)
                shutil.copyfile(source, path)

        pc_dir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        save(
            self,
            os.path.join(pc_dir, "libosmo-mgcp-client.pc"),
            "\n".join(
                [
                    "prefix=%s" % self.package_folder,
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    "",
                    "Name: Osmocom Media Gateway Control Protocol Client library",
                    "Description: C Utility Library",
                    "Version: %s" % self.version,
                    "Libs: -L${libdir} -losmo-mgcp-client",
                    "Cflags: -I${includedir}/",
                    "Requires: libosmocore",
                    "",
                ]
            ),
        )

    def package_info(self):
        self.cpp_info.libs = ["osmo-mgcp-client"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "libosmocore::osmocore",
            "libosmocore::osmovty",
            "libosmo-abis::osmoabis",
        ]
        self.cpp_info.set_property("cmake_file_name", "libosmo-mgcp-client")
        self.cpp_info.set_property("cmake_target_name", "libosmo-mgcp-client::libosmo-mgcp-client")
        self.cpp_info.set_property("pkg_config_name", "libosmo-mgcp-client")

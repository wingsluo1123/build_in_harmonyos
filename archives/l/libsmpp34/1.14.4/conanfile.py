#!/usr/bin/env python3
"""Conan recipe for the Open SMPP 3.4 PDU library."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class Libsmpp34Conan(ConanFile):
    name = "libsmpp34"
    version = "1.14.4"
    description = "Open SMPP 3.4 PDU packaging and unpackaging library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitea.osmocom.org/cellular-infrastructure/libsmpp34"
    url = "https://gitea.osmocom.org/cellular-infrastructure/libsmpp34"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libsmpp34 is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "this recipe packages the upstream libsmpp34 shared library")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libsmpp34.tar.xz",
            strip_root=True,
        )

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        sources = sorted(
            glob.glob(os.path.join(self.source_folder, "src", "*.c"))
        )
        if len(sources) != 7:
            raise ConanInvalidConfiguration(
                "expected 7 libsmpp34 C sources, found %d" % len(sources))

        os.makedirs(self.build_folder, exist_ok=True)
        output = os.path.join(self.build_folder, "libsmpp34.so.1.2.1")
        command = [
            f'"{cc}"',
            "-shared",
            "-fPIC",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Wno-unused-parameter",
            "-D_REENTRANT",
            "-DBSD_COMP",
            "-D_POSIX_PTHREAD_SEMANTICS",
            f'-I"{self.source_folder}"',
            f'-I"{os.path.join(self.source_folder, "src")}"',
            "-Wl,-soname,libsmpp34.so.1",
            "-Wl,--no-undefined",
            f'-o"{output}"',
        ]
        command += [f'"{path}"' for path in sources]
        command += ["-lpthread", "-lrt"]
        self.output.info("libsmpp34 link: %s" % " ".join(command))
        self.run(" ".join(command), cwd=self.build_folder, env="conanbuild")

        for link in ("libsmpp34.so.1", "libsmpp34.so"):
            path = os.path.join(self.build_folder, link)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink("libsmpp34.so.1.2.1", path)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        copy(self, "libsmpp34.so*", self.build_folder, libdir)
        copy(self, "*.h", os.path.join(self.source_folder, "src"), incdir)
        copy(
            self,
            "*.frame",
            os.path.join(self.source_folder, "def_frame"),
            os.path.join(incdir, "def_frame"),
        )

        # Conan extraction does not guarantee symlink preservation.
        target = os.path.join(libdir, "libsmpp34.so.1.2.1")
        for link, link_target in (
            ("libsmpp34.so.1", "libsmpp34.so.1.2.1"),
            ("libsmpp34.so", "libsmpp34.so.1"),
        ):
            path = os.path.join(libdir, link)
            if not os.path.lexists(path):
                source = target if link_target == "libsmpp34.so.1.2.1" else os.path.join(libdir, link_target)
                shutil.copyfile(source, path)

        pc_dir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        save(
            self,
            os.path.join(pc_dir, "libsmpp34.pc"),
            "\n".join(
                [
                    "prefix=%s" % self.package_folder,
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    "",
                    "Name: Open SMPP 3.4 Library",
                    "Description: SMPP (SMS Peer to Peer) v3.4 Library",
                    "Version: %s" % self.version,
                    "Libs: -L${libdir} -lsmpp34 -lpthread -lrt",
                    "Cflags: -I${includedir}/",
                    "",
                ]
            ),
        )

    def package_info(self):
        self.cpp_info.libs = ["smpp34"]
        self.cpp_info.system_libs = ["pthread", "rt"]
        self.cpp_info.set_property("cmake_file_name", "libsmpp34")
        self.cpp_info.set_property("cmake_target_name", "libsmpp34::libsmpp34")
        self.cpp_info.set_property("pkg_config_name", "libsmpp34")

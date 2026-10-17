#!/usr/bin/env python3
"""Conan recipe — mdtest 1.9.3 (GNU Makefile) for HarmonyOS PC."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MdtestConan(ConanFile):
    name = "mdtest"
    version = "1.9.3"
    description = "MPI-coordinated parallel filesystem metadata benchmark"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/mdtest/"
    url = "https://sourceforge.net/projects/mdtest/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mpich/5.0.1.2")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "mdtest/1.9.3 is validated only for OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # The SourceForge archive is intentionally flat and has no root folder.
        get(self, **self.conan_data["sources"])

    def _mpi_tool(self, name):
        mpi = self.dependencies.host["mpich"]
        for bindir in mpi.cpp_info.bindirs or ["bin"]:
            folder = bindir if os.path.isabs(bindir) else os.path.join(
                mpi.package_folder, bindir
            )
            candidate = os.path.join(folder, name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("mpich does not provide {}".format(name))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf(self, path):
        if not self._is_elf(path):
            raise ConanInvalidConfiguration("expected ELF executable: {}".format(path))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration("OHOS ELF signing tools are unavailable")
        unsigned = path + ".unsigned"
        signed = path + ".signed"
        env = {k: v for k, v in os.environ.items() if not k.startswith("LD_LIBRARY")}
        try:
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )
            subprocess.run(
                [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                 "-selfSign", "1"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )
            os.replace(signed, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (unsigned, signed):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def build(self):
        apply_conandata_patches(self)
        mpicc = self._mpi_tool("mpicc")
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        target_cc = compilers.get("c") or "/data/service/hnp/bin/clang"
        mpi_root = self.dependencies.host["mpich"].package_folder
        flags = (
            "-O2 -Wall -Wextra "
            "-ffile-prefix-map={}=/usr/src/mdtest-1.9.3 "
            "-fdebug-prefix-map={}=/usr/src/mdtest-1.9.3 "
            "-ffile-prefix-map={}=/usr -fdebug-prefix-map={}=/usr"
        ).format(
            self.source_folder, self.source_folder, mpi_root, mpi_root
        )
        self.run(
            'make -C "{}" -j1 MPI_CC="{}" MPICH_CC="{}" '
            'MDTEST_FLAGS="{}"'.format(
                self.source_folder, mpicc, target_cc, flags
            ),
            env="conanrun",
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "mdtest", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "mdtest.1", src=self.source_folder, dst=mandir, keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "mdtest"),
             keep_path=False)
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        executable = os.path.join(bindir, "mdtest")
        strip_tool = "/data/service/hnp/bin/llvm-strip"
        if not os.path.isfile(strip_tool):
            raise ConanInvalidConfiguration("OHOS llvm-strip is unavailable")
        subprocess.run([strip_tool, "--strip-debug", executable], check=True)
        self._sign_elf(executable)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

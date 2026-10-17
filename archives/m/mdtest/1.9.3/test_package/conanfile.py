#!/usr/bin/env python3
"""Target-side tests for the packaged mdtest command."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class MdtestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_mdtest.py", "mpi_delay.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

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

    def _sign_elf(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration("OHOS ELF signing tools are unavailable")
        temporary = path + ".signing"
        try:
            shutil.copy2(path, temporary)
            subprocess.run([objcopy, "--remove-section", ".codesign", temporary],
                           check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
            subprocess.run([signer, "sign", "-inFile", temporary,
                            "-outFile", temporary, "-selfSign", "1"],
                           check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
            os.replace(temporary, path)
            os.chmod(path, 0o755)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def build(self):
        mpicc = self._mpi_tool("mpicc")
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        target_cc = compilers.get("c") or "/data/service/hnp/bin/clang"
        source = os.path.join(self.source_folder, "mpi_delay.c")
        output = os.path.join(self.build_folder, "libmdtest_delay.so")
        self.run(
            'MPICH_CC="{}" "{}" -shared -fPIC -O2 -o "{}" "{}"'.format(
                target_cc, mpicc, output, source
            ),
            env="conanrun",
        )
        self._sign_elf(output)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "mdtest validation must execute in the OHOS target environment"
            )
        package = self.dependencies["mdtest"].package_folder
        executable = os.path.join(package, "bin", "mdtest")
        script = os.path.join(self.source_folder, "test_mdtest.py")
        interposer = os.path.join(self.build_folder, "libmdtest_delay.so")
        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            raise ConanInvalidConfiguration("OHOS llvm-readelf is unavailable")
        self.run(
            'python3 "{}" --mdtest "{}" --mpiexec "{}" '
            '--interposer "{}" --readelf "{}"'.format(
                script, executable, self._mpi_tool("mpiexec"), interposer, readelf
            ),
            env="conanrun",
        )

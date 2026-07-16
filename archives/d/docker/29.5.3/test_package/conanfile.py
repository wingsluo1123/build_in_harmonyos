#!/usr/bin/env python3
"""Conan test_package for Docker CLI 29.5.3.

Verifies that the docker binary is built correctly and reports its version.
On HarmonyOS, binaries must be signed before execution (ELF signing requirement).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout

SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"


def _sign_elf(elf_path):
    """Sign an ELF binary for HarmonyOS."""
    if not os.path.isfile(SIGN_TOOL):
        return False
    tmp = elf_path + ".signed.tmp"
    subprocess.run([OBJCOPY, "--remove-section", ".codesign", elf_path],
                   capture_output=True, timeout=10)
    for _ in range(3):
        r = subprocess.run(
            [SIGN_TOOL, "sign", "-inFile", elf_path,
             "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.isfile(tmp):
            shutil.move(tmp, elf_path)
            os.chmod(elf_path, 0o755)
            return True
        import time; time.sleep(1)
    if os.path.isfile(tmp):
        os.unlink(tmp)
    return False


class DockerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must actually exercise the built package
        dep = self.dependencies["docker"]
        src_bin = os.path.join(dep.package_folder, "bin", "docker")

        if str(self.settings.os) == "OHOS":
            # Copy to temp dir and sign for HarmonyOS
            import tempfile
            test_dir = tempfile.mkdtemp(prefix="docker-test-")
            test_bin = os.path.join(test_dir, "docker")
            shutil.copy(src_bin, test_bin)
            _sign_elf(test_bin)
            self.run(f'"{test_bin}" --version')
            shutil.rmtree(test_dir, ignore_errors=True)
        else:
            self.run(f'"{src_bin}" --version', env="conanrun")

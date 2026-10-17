#!/usr/bin/env python3
"""Installed-package tests for modsecurity-apache 2.9.13.

Two real consumer cases (no stubs, no skipped assertions):
  1. modsec_module_load — statically verifies the packaged
     mod_security2.so is a genuine Apache DSO: ELF ET_DYN, minimum size,
     security2_module entry exported (nm -D when available, else dynstr
     proof) plus the httpd host import ap_log_perror. No dlopen(): musl
     resolves all relocations eagerly (BIND_NOW), so a standalone dlopen
     without a running httpd host always fails even for a good module.
  2. modsec_conf_check — open the packaged modsecurity.conf-recommended
     and assert it carries real engine directives (SecRuleEngine,
     SecRequestBodyAccess). Guards against packaging an empty fixture
     (toybox-tar lesson: never trust a green harness over empty files).
"""

import json
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

TEST_EXECUTABLES = ("modsec_module_load", "modsec_conf_check")


class ModsecurityApacheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        toolchain = CMakeToolchain(self)
        pkg = self.dependencies["modsecurity-apache"].package_folder
        toolchain.variables["MODSEC_LIBDIR"] = os.path.join(pkg, "lib").replace("\\", "/")
        toolchain.variables["MODSEC_RESDIR"] = os.path.join(pkg, "res").replace("\\", "/")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("modsecurity-apache consumers are not runnable here")
        runtime_dir = None
        passed = 0
        failed_names = []
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile.mkdtemp(
                    prefix="modsec-test-", dir="/data/storage/el2/base/cache"
                )
            for name in TEST_EXECUTABLES:
                executable = os.path.join(self.cpp.build.bindir, name)
                if runtime_dir is not None:
                    staged = os.path.join(runtime_dir, name)
                    shutil.copy2(executable, staged)
                    self._sign_ohos_elf(staged)
                    executable = staged
                # Per-case evidence: a failing consumer must still leave a
                # truthful marker behind, so record and continue instead of
                # letting the first failure skip the marker entirely.
                try:
                    self.run(f'"{executable}"', env="conanrun")
                    passed += 1
                except Exception as error:  # noqa: BLE001 - collected, re-raised below
                    failed_names.append(name)
                    self.output.warning(f"consumer {name} failed: {error}")
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(
                {
                    "executed": True,
                    "passed": passed == len(TEST_EXECUTABLES),
                    "command": "modsec_module_load + modsec_conf_check",
                    "discovered": len(TEST_EXECUTABLES),
                    "passedCount": passed,
                }
            )
        )
        if failed_names:
            raise ConanException(f"failing consumers: {', '.join(failed_names)}")

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True, capture_output=True, text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

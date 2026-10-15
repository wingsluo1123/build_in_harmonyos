#!/usr/bin/env python3
"""Conan recipe — crypto-algorithms cfbde48414.

Upstream (B-Con/crypto-algorithms) is a public-domain collection of basic
cryptography algorithm implementations. Each algorithm ships as an independent
.c/.h pair with NO build system (README: "Compiling them should be as easy as
adding the relevant source code to the project"). This recipe therefore:

1. redistributes headers + algorithm sources into include/ (consumers compile
   the .c files they need, matching upstream usage), and
2. in build(), compiles and runs all 10 upstream known-answer test programs
   (R51 upstream test three-step method; R34 real API usage in test_package).

License: public domain (upstream README: "released into the public domain free
of any restrictions").
"""

import json
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Each algorithm is a {name: (impl_source, test_source)} pair.
ALGORITHMS = {
    "aes": ("aes.c", "aes_test.c"),
    "arcfour": ("arcfour.c", "arcfour_test.c"),
    "base64": ("base64.c", "base64_test.c"),
    "blowfish": ("blowfish.c", "blowfish_test.c"),
    "des": ("des.c", "des_test.c"),
    "md2": ("md2.c", "md2_test.c"),
    "md5": ("md5.c", "md5_test.c"),
    "rot-13": ("rot-13.c", "rot-13_test.c"),
    "sha1": ("sha1.c", "sha1_test.c"),
    "sha256": ("sha256.c", "sha256_test.c"),
}


class CryptoalgorithmsConan(ConanFile):
    name = "crypto-algorithms"
    version = "cfbde48414"
    description = "Basic implementations of standard cryptography algorithms (AES, SHA-1, SHA-256, MD5, etc.)"
    license = "public-domain"
    homepage = "https://github.com/B-Con/crypto-algorithms"
    url = ""  # CI fills this

    package_type = "header-library"

    # No compiled artifacts: settings kept only for structural consistency;
    # package_id is cleared in package_id() so every configuration shares
    # one package (see conanfile-headeronly template).
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No build system upstream: instead of a fake compile, verify the
        # package by compiling and running all 10 upstream known-answer tests
        # with the conan toolchain compiler (R51; R34 real usage in tests).
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        build_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(build_dir, exist_ok=True)

        results = []
        for name, (impl, test) in ALGORITHMS.items():
            exe = os.path.join(build_dir, f"{name}_test")
            src_files = [os.path.join(self.source_folder, impl),
                         os.path.join(self.source_folder, test)]
            cmd = f"{shlex.quote(cc)} -O2 -o {shlex.quote(exe)} " + \
                  " ".join(shlex.quote(s) for s in src_files)
            build_proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
            if build_proc.returncode != 0:
                self.output.error(f"upstream test compile failed: {name}\n{build_proc.stdout[-2000:]}")
                raise RuntimeError(f"upstream test compile failed: {name}")
            run_proc = subprocess.run([exe], stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True)
            if run_proc.returncode != 0:
                self.output.error(f"upstream test run failed: {name}\n{run_proc.stdout[-2000:]}")
                raise RuntimeError(f"upstream test run failed: {name}")
            results.append((name, run_proc.stdout.strip(), run_proc.returncode))

        passed = sum(1 for _, _, rc in results if rc == 0)
        detail = "; ".join(f"{n}: {out}" for n, out, _ in results)
        result = {
            "status": "passed" if passed == len(results) else "failed",
            "framework": "plain-C-known-answer-programs",
            "command": "clang -O2 <impl> <test> && <exe> (per algorithm)",
            "discovered": len(results),
            "executed": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "skipped": 0,
            "detail": detail,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        # Redistribute headers + algorithm sources (consumers compile the .c
        # files they need, exactly as upstream intends). Test files are NOT
        # packaged.
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        for _, (impl, _test) in ALGORITHMS.items():
            copy(self, impl, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"),
                 keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # Consumers must compile the algorithm .c files they use (upstream
        # design); no prebuilt library is shipped.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "crypto-algorithms")
        self.cpp_info.set_property("cmake_target_name", "crypto-algorithms::crypto-algorithms")

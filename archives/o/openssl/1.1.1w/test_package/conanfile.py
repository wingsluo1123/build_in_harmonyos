#!/usr/bin/env python3
"""Consumer test for the OpenSSL 1.1.1w Conan package."""

import os

from conan import ConanFile


class OpensslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["openssl"]
        cpp = dep.cpp_info
        include_flags = " ".join(f'-I"{path}"' for path in cpp.includedirs)
        library_flags = " ".join(f'-L"{path}"' for path in cpp.libdirs)
        link_flags = " ".join(f"-l{lib}" for lib in cpp.libs)
        system_flags = " ".join(f"-l{lib}" for lib in cpp.system_libs)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        self.run(
            f'"{cc}" test_openssl.c -o test_openssl '
            f"{include_flags} {library_flags} {link_flags} {system_flags}"
        )

    def test(self):
        # /system/bin/sh on OHOS cannot execute a user ELF directly.
        shell = os.environ.get("CONFIG_SHELL", "")
        if not shell or not os.path.exists(shell):
            for candidate in (
                "/data/service/hnp/bin/bash",
                "/storage/Users/currentUser/usr/local/bin/bash",
                "/usr/bin/bash",
                "/bin/bash",
            ):
                if os.path.exists(candidate):
                    shell = candidate
                    break
        if shell:
            self.run(f'{shell} -c "./test_openssl"', env="conanrun")
        else:
            self.run("./test_openssl", env="conanrun")

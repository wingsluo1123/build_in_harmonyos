"""Conan test_package for percona-server 8.0.36 - Conan L1 official test.

Uses CMake to build the test binary that links against libperconaserverclient.
CI runs this automatically via `conan create` (which invokes test_package).

OHOS: /system/bin/sh (mksh) cannot execute ELF binaries on some devices, so use
the configured shell when available and fall back to zsh.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PerconaServerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries on some devices.
        # Prefer the configured shell, but do not assume bash is installed.
        configured_shell = os.environ.get("CONFIG_SHELL")
        shell_candidates = [
            configured_shell if configured_shell != "/bin/sh" else None,
            "/data/service/hnp/bin/bash",
            "/usr/bin/zsh",
            configured_shell,
            "/bin/sh",
        ]
        shell = next(
            (candidate for candidate in shell_candidates
             if candidate and os.path.exists(candidate) and os.access(candidate, os.X_OK)),
            None,
        )
        if shell:
            self.run(f"{shell} -c './test_client'", env="conanrun")
        else:
            self.run("./test_client", env="conanrun")


#!/usr/bin/env python3
"""Conan test_package for ws 11.4.6 (IXWebSocket + ws CLI).

Consumer-level validation:
  1. cmake.test()        — test_ws: WebSocket echo round-trip over 127.0.0.1
                           through the packaged library's public API.
  2. self.run(bin/ws ...) — the packaged `ws` command line tool (located via
                           the tested package folder, conanrun env so the
                           shared spdlog/fmt runtime deps resolve). Its
                           version banner is asserted; the upstream exit code
                           for `--version` is 1 (upstream `ret` is initialised
                           to 1 and the version branch does not reset it), so
                           only the printed banner is asserted.
"""

import io
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class WsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # CLI smoke: run the packaged ws binary (repo convention: locate it
        # via the tested package's folder).
        pkg_dir = self.dependencies["ws"].package_folder
        ws_bin = os.path.join(pkg_dir, "bin", "ws")
        buf = io.StringIO()
        try:
            self.run(f'"{ws_bin}" --version', env="conanrun", stdout=buf)
        except ConanException:
            # Upstream exits 1 for --version (ret init); tolerated — the
            # printed banner below is the real assertion.
            pass
        output = buf.getvalue()
        if "ixwebsocket/11.4.6" not in output:
            raise ConanException(
                f"ws --version did not print the expected banner, got: {output!r}"
            )

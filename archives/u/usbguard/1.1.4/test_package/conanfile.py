#!/usr/bin/env python3
"""Consumer test for usbguard/1.1.4 (Conan L1).

Two independent angles on the delivered artifact:

1. test_usbguard.cpp — a real C++ consumer binary that links libusbguard
   through the generated CMake package and drives the public Rule API
   (parseRuleFromString / Rule::fromString / RuleParserError).
2. the packaged command-line tools — `usbguard --version` (asserted against
   the exact version string) and `usbguard-rule-parser` on a valid and on a
   malformed rule (asserted rc 0 / non-zero).

Both run under the package's runtime environment (env="conanrun").
"""
import io
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class UsbguardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        # protobuf/3.17.3 sets cmake_find_mode=none (it ships its own CMake
        # package config), so CMakeDeps does not generate a protobuf-config
        # in the generator folder and the find_dependency(protobuf) emitted
        # by usbguard-config.cmake fails unless we point at the package's own
        # config directory (grpc/1.70 recipe precedent).
        protobuf = self.dependencies.get("protobuf")
        if protobuf is not None:
            protobuf_dir = os.path.join(
                protobuf.package_folder, "lib", "cmake", "protobuf")
            # CMakeDeps emits find_dependency(protobuf) (lower case), while
            # CMakeLists.txt looks it up as `Protobuf`; provide both spellings.
            toolchain.cache_variables["protobuf_DIR"] = protobuf_dir
            toolchain.cache_variables["Protobuf_DIR"] = protobuf_dir
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        # Neutralize an ambient LD_LIBRARY_PATH (some CI workers point it at a
        # /usr/local/lib whose incompatible libxml2.so.16 breaks the SDK's lld
        # on every link — libabw / zvbi precedent).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")

        # 1) Library consumer binary: prints every check and fails non-zero if
        #    any assertion fails.
        consumer = os.path.join(self.cpp.build.bindirs[0], "test_usbguard")
        if not os.path.isfile(consumer):
            raise ConanException(f"consumer test binary not built: {consumer}")
        self.output.info("running libusbguard API consumer: " + consumer)
        self.run(f'"{consumer}"', env="conanrun")

        # 2) usbguard CLI must report the exact version.
        usbguard_bin = os.path.join(bindir, "usbguard")
        if not os.path.isfile(usbguard_bin):
            raise ConanException(f"usbguard CLI not installed: {usbguard_bin}")
        captured = io.StringIO()
        self.run(f'"{usbguard_bin}" --version', env="conanrun", stdout=captured)
        version_output = captured.getvalue()
        if "usbguard 1.1.4" not in version_output:
            raise ConanException(
                f"'usbguard --version' did not report 1.1.4: {version_output!r}")
        self.output.info("usbguard --version: " + version_output.strip().splitlines()[0])

        # 3) Rule parser accepts a valid rule (rc 0) ...
        parser = os.path.join(bindir, "usbguard-rule-parser")
        if not os.path.isfile(parser):
            raise ConanException(f"usbguard-rule-parser not installed: {parser}")
        self.run(f'"{parser}" "allow id 1d6b:0002"', env="conanrun")

        # 4) ... and rejects a malformed rule (non-zero exit status).  The
        #    rejection is the expected outcome, so a non-zero rc must not be
        #    turned into a hard error by conan's default handling.
        rc = self.run(f'"{parser}" "asdf"', env="conanrun", ignore_errors=True)
        if rc == 0:
            raise ConanException("usbguard-rule-parser accepted a malformed rule")
        self.output.info(
            f"usbguard-rule-parser correctly rejected a malformed rule (rc={rc})")

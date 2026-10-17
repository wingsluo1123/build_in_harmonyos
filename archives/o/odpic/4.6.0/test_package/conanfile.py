#!/usr/bin/env python3
"""test_package for odpic 4.6.0 -- consumer verification on HarmonyOS PC.

Two independent layers, both run by `conan create` in the test phase:

  * test.c / ctest -- a real consumer that includes the packaged <dpi.h>,
    links dpi::odpic and calls the packaged API.  It passes either way the
    HarmonyOS runtime resolves the Oracle Client: with the client present the
    full context-creation path succeeds, with the client absent the library
    answers with its own DPI- diagnostic.
  * test_ohos.py -- pure-Python (stdlib struct only) OpenHarmony ELF checks
    on the packaged lib/libodpic.so.4.6.0: AArch64 ET_DYN, .note.ohos.ident,
    .codesign, musl libc binding, SONAME libodpic.so.4, no RPATH leakage.

No can_run() gate on purpose: the OHOS worker builds and runs natively, so the
consumer binary must really execute (an early skip would silently weaken the
gate).

Falsifiability gate: the two layers above only prove "it works on this host".
`_assert_ohos_platform()` additionally pins the target platform itself, so the
case fails loudly (instead of passing by accident) when the same recipe is
driven with a linux/gcc profile -- repository convention, 1000+ packages.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


def _assert_ohos_platform(conanfile):
    """Fail fast unless this consumer case really targets HarmonyOS PC."""
    actual = str(conanfile.settings.os)
    if actual != "OHOS":
        raise ConanException(
            "[ohos-platform-gate] expected settings.os == 'OHOS' (HarmonyOS PC), "
            f"got '{actual}'. This consumer case exists to certify the OHOS/aarch64 "
            "adaptation; running it under a non-OHOS profile would make it pass "
            "vacuously, so it must fail here instead."
        )


class OdpicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
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
        # Layer 0: platform gate -- certifies the target, not just the host.
        _assert_ohos_platform(self)

        cmake = CMake(self)
        build_type = str(self.settings.build_type)
        self.run(
            f"ctest --output-on-failure --build-config {build_type}",
            env="conanrun",
        )

        odpic_pkg = self.dependencies["odpic"].package_folder
        library_path = os.path.join(odpic_pkg, "lib", "libodpic.so.4.6.0")
        test_script = os.path.join(self.source_folder, "test_ohos.py")
        self.run(f'python3 "{test_script}" "{library_path}"')

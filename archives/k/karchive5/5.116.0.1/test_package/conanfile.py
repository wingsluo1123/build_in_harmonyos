#!/usr/bin/env python3
"""Conan test_package for karchive5 5.116.0.1.

L1 conformance test (R34, real API usage — no empty shell):
  1. compiles test.cpp against the installed KF5::Archive;
  2. runs the consumer binary under QT_QPA_PLATFORM=offscreen; it exercises:
       - KTar write + read round trip (KArchiveDirectory::file lookup);
       - KZip write + read round trip with DeflateCompression (zlib deflate);
       - KCompressionDevice GZip write + read round trip (zlib deflate/inflate
         through the shared library). This is the runtime proof that the
         non-PIC zlib/1.3.1 libz.a got linked correctly with
         -Wl,--exclude-libs,ALL and that the compression backends work.

qt5-qtbase uses cmake_find_mode=none, so CMakeDeps does not generate an
Qt5Config.cmake; we add qtbase + karchive5's lib/cmake to CMAKE_PREFIX_PATH
the same way the main recipe does via conan_cmakedeps_paths.cmake.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import save


class Karchive5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain is instantiated manually in generate() (it must run after
    # conan_cmakedeps_paths.cmake is written), so it must NOT also be listed
    # here — Conan 2 rejects a generator declared in both places.
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        pkg = self.dependencies.get("karchive5")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg and pkg.package_folder:
            pkg_pkg = pkg.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_pkg}/lib/cmake")')
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        save(
            self,
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"),
            "\n".join(lines) + "\n",
        )
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link
        # (kservice5 5.116.0 test_package precedent).
        env = Environment()
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    env.append("LD_LIBRARY_PATH", [libdir])
                plugins = os.path.join(dep.package_folder, "plugins")
                if os.path.isdir(plugins):
                    env.prepend_path("QT_PLUGIN_PATH", plugins)
                    platforms = os.path.join(plugins, "platforms")
                    if os.path.isdir(platforms):
                        env.prepend_path("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)
        env.define("QT_QPA_PLATFORM", "offscreen")
        if self.settings.os == "OHOS":
            # CI workers run inside the OHOS sandbox whose LD_LIBRARY_PATH
            # contains an incompatible libc++_shared.so (under
            # /data/storage/el1/bundle/libs/arm64) shadowing the compatible
            # one; prepend /system/lib64 so the executables resolve the
            # compatible libc++ first (kservice5 5.116.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            sdk_llvm_lib = (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                "/ohos/native/llvm/lib"
            )
            if os.path.isdir(sdk_llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return env

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_karchive5")
        if not os.path.isfile(bin_path):
            raise ConanException(f"test binary not found: {bin_path}")
        self.output.info("running consumer: " + bin_path)
        env = self._runtime_env()
        with env.vars(self).apply():
            self.run(f'"{bin_path}"', env="conanrun")

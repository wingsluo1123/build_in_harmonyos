#!/usr/bin/env python3
"""Conan recipe — memory-allocators 3.5 (C++11 header + static library).

mtrebi/memory-allocators: custom memory allocators (Linear / Stack / Pool /
FreeList / CAllocator). Upstream CMakeLists only builds a benchmark
executable; patch 0001 adds a static library target and install rules.

R32 note: no settings.os branch needed — the OHOS-adapted conan maps
os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS via CMakeToolchain.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MemoryAllocatorsConan(ConanFile):
    name = "memory-allocators"
    version = "3.5"
    description = "mtrebi/memory-allocators - custom memory allocators (Linear, Stack, Pool, FreeList, CAllocator)"
    license = "MIT"
    homepage = "https://github.com/mtrebi/memory-allocators"
    url = "https://github.com/mtrebi/memory-allocators"  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无第三方运行时依赖
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R03: 并行度收敛为 -j1。目标文件系统(HMDFS/FUSE 族)拒绝 mkfifo，
        # GNU make jobserver(-jN) 依赖命名管道 → 报 Operation not permitted，
        # 并发 fork 在 CI worker 上还会触发 `can't fork`（CI 10-15 重跑首错）。
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["memory-allocators"]
        self.cpp_info.set_property("cmake_file_name", "memory-allocators")
        self.cpp_info.set_property("cmake_target_name", "memory-allocators::memory-allocators")

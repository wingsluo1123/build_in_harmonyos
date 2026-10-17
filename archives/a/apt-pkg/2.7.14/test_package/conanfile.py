#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/apt-pkg/{version}/test_package/conanfile.py
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


def _find_ohos_native_sdk():
    """Locate the OHOS native SDK root that ships the libc++ headers/libs.

    Same convention as the apt-pkg recipe and libffado: the OHOS clang sysroot
    has no C++ standard library headers, so CXXFLAGS need
      -isystem <sdk>/include/libcxx-ohos/include/c++/v1
    and the linker needs -L<sdk>/lib/aarch64-linux-ohos for the libc++ runtime.
    """
    candidates = []
    for var in ("OHOS_NATIVE_SDK", "OHOS_SDK_ROOT", "OHOS_NDK_HOME", "OHOS_SDK"):
        if os.environ.get(var):
            candidates.append(os.path.join(os.environ[var], "native"))
    candidates.append("/storage/Users/currentUser/ohos-sdk")
    candidates.extend(sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native")))
    for c in candidates:
        # 兼容两种 SDK 布局：扁平（<sdk>/include/libcxx-ohos/...，本地）与
        # CI worker 的 llvm 嵌套（<sdk>/llvm/include/libcxx-ohos/...）。
        for sdk in (c, os.path.join(c, "llvm")):
            if os.path.isdir(os.path.join(sdk, "include", "libcxx-ohos", "include", "c++", "v1")):
                return sdk
    return None


class AptpkgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        sdk = _find_ohos_native_sdk()
        if not sdk:
            raise ConanInvalidConfiguration(
                "OHOS native SDK (libcxx-ohos headers) not found; set "
                "OHOS_NATIVE_SDK/OHOS_SDK_ROOT or install the SDK (see notes.md)")
        cxx_inc = os.path.join(sdk, "include", "libcxx-ohos", "include", "c++", "v1")
        sdk_lib = os.path.join(sdk, "lib", "aarch64-linux-ohos")
        tc.extra_cxxflags.append(f"-isystem {cxx_inc}")
        tc.extra_sharedlinkflags.append(f"-L{sdk_lib}")
        tc.extra_exelinkflags.append(f"-L{sdk_lib}")
        tc.generate()

    def _runtime_lib_dirs(self):
        """收集 test 二进制运行时需要的全部 .so 目录。

        conanrun（VirtualRunEnv）只会收录配方里声明为 shared 的依赖 lib 目录，
        而 gnutls/3.8.10 在 ohpcd 制品仓里的配方把 LIBRARY_TYPE 标成 STATIC
        （但包内实际只发 .so，无 .a），导致 conanrun 的 LD_LIBRARY_PATH 漏掉
        libgnutls.so.30 所在目录，直接运行报
        "Error loading shared library libgnutls.so.30"。故这里显式遍历全部依赖
        （含传递依赖）的 libdirs，再补上 OHOS SDK 的 libc++_shared.so 目录。
        """
        dirs = []
        sdk = _find_ohos_native_sdk()
        if sdk:
            dirs.append(os.path.join(sdk, "lib", "aarch64-linux-ohos"))
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for d in dep.cpp_info.libdirs:
                p = os.path.join(base, d)
                if os.path.isdir(p):
                    dirs.append(p)
        # 去重保序
        seen = set()
        return [d for d in dirs if not (d in seen or seen.add(d))]

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # G2 修复：不用 cmake.test()（CTest 不携带 conan 运行时 env，导致
        # "Error loading shared library libgnutls.so.30"）。改为直接运行二进制，
        # 并把全部依赖 lib 目录 + OHOS SDK libc++ 目录注入 LD_LIBRARY_PATH
        # （见 _runtime_lib_dirs，覆盖 gnutls 声明 STATIC 但只发 .so 的情况）。
        executable = os.path.join(self.cpp.build.bindirs[0], "test_apt-pkg")
        ld_library_path = ":".join(self._runtime_lib_dirs())
        self.run(f'LD_LIBRARY_PATH="{ld_library_path}" "{executable}"',
                 cwd=self.build_folder)

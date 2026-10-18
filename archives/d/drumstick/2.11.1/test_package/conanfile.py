#!/usr/bin/env python3
"""Conan test_package for drumstick — links the four Drumstick::* libraries
and runs a functional SMF file round-trip plus data-class checks.

Consumer perspective mirrors the libdrumstick/2.10.0 test package: the
installed upstream drumstick-config.cmake (cmake_find_mode=none) is reached via
explicit drumstick_DIR / CMAKE_PREFIX_PATH, QT_VERSION_MAJOR is set by hand
(upstream config checks that plain variable), and the runtime LD_LIBRARY_PATH
covers the drumstick/qtbase libraries plus the OHOS SDK libc++_shared.so."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

_OHOS_SDK_LLVM_LIB = os.environ.get(
    "OHOS_SDK_LLVM_LIB",
    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
)


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # CMakeToolchain / CMakeDeps are instantiated explicitly in generate()
    # (they need the dependency package folders); only VirtualRunEnv is
    # declared here to avoid double registration.
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        pkg = self.dependencies[self.tested_reference_str].package_folder
        qtbase = self.dependencies["qtbase"].package_folder
        qt5compat = self.dependencies["qt5compat"].package_folder
        alsa = self.dependencies["alsa-lib"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": ";".join(
                    str(p).replace("\\", "/")
                    for p in (qtbase, qt5compat, alsa, pkg)
                ),
                "Qt6_DIR": os.path.join(
                    qtbase, "lib", "cmake", "Qt6"
                ).replace("\\", "/"),
                "Qt6Core5Compat_DIR": os.path.join(
                    qt5compat, "lib", "cmake", "Qt6Core5Compat"
                ).replace("\\", "/"),
                "drumstick_DIR": os.path.join(
                    pkg, "lib", "cmake", "drumstick"
                ).replace("\\", "/"),
            }
        )
        tc.generate()
        # CMakeDeps still emits an ALSA config (alsa-lib is not cmake_find_mode
        # none) so find_dependency(ALSA) inside drumstick-alsa-config.cmake and
        # the explicit find_package(ALSA) below resolve.
        CMakeDeps(self).generate()
        # pkg_check_modules(ALSA ...) in the test CMakeLists needs
        # PKG_CONFIG_PATH pointing at the alsa-lib pkgconfig dir (its
        # CMakeDeps config carries no include dirs) — same as the main recipe.
        alsa_pc = os.path.join(alsa, "lib", "pkgconfig")
        if os.path.isdir(alsa_pc):
            self.buildenv_info.prepend_path("PKG_CONFIG_PATH", alsa_pc)
        # Runtime search paths for the test executable.
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH",
            os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos"),
        )
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH",
            os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos", "c++"),
        )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_ld_library_path(self):
        """test() 运行期完整 LD_LIBRARY_PATH：
        conanrun 自动聚合的依赖 lib 目录 + OHOS SDK libc++_shared.so 目录
        （E298: 显式注入，避免聚合环境缺路径导致库加载失败）。"""
        paths = []
        for dep_name in ("drumstick", "qtbase", "qt5compat", "alsa-lib"):
            dep_node = self.dependencies.get(dep_name)
            if dep_node is not None:
                paths.append(os.path.join(dep_node.package_folder, "lib"))
        paths.append(os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos"))
        paths.append(os.path.join(_OHOS_SDK_LLVM_LIB, "aarch64-linux-ohos", "c++"))
        uniq = list(dict.fromkeys(paths))
        return ":".join(uniq)

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError(
                "test_drumstick executable directory was not produced"
            )
        cmd = os.path.join(bindirs[0], "test_drumstick")
        if not os.path.isfile(cmd):
            raise RuntimeError(
                "test_drumstick executable was not produced: {}".format(cmd)
            )
        # E298: 显式注入完整 LD_LIBRARY_PATH（含 SDK libc++），避免
        # conanrun 聚合环境缺路径导致 libdrumstick/Qt6 库加载失败。
        # DRUMSTICKRT：BackendManager 的默认插件搜索路径基于可执行文件
        # 相对路径推导，test_package 中不命中；显式指向被测包插件目录，
        # 使 defaultPaths() 能枚举到安装的 RT 后端插件。
        pkg = self.dependencies[self.tested_reference_str].package_folder
        plugins = os.path.join(pkg, "lib", "drumstick2")
        self.run(
            'env LD_LIBRARY_PATH="{}" DRUMSTICKRT="{}" {}'.format(
                self._run_ld_library_path(), plugins, cmd
            ),
            env="conanrun",
        )

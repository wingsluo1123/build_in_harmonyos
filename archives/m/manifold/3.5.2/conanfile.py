#!/usr/bin/env python3
"""Conan recipe — manifold 3.5.2 (C++17 geometry library for triangle meshes).

manifold 是鲁棒的三角形网格几何库 (CSG 布尔运算、简化、属性插值等),
上游使用 CMake >= 3.18, 默认通过 FetchContent 拉取缺失依赖。

依赖映射策略 (无上游补丁, 全部走上游自带的 find_package 快路径):
  - GTest     : MANIFOLD_TEST=ON 时上游先 find_package(GTest QUIET),
                命中 CMakeDeps 生成的 GTestConfig.cmake 即跳过 FetchContent。
  - Clipper2  : MANIFOLD_CROSS_SECTION=ON + backend=clipper2 时上游
                find_package(Clipper2 QUIET), 命中即跳过内置 FetchContent
                (其内置路径还会从 GitHub 拉 clipper2 并打 carry-patch)。
  - TBB       : 默认 MANIFOLD_PAR=OFF, 不引入; 上游逻辑为
                find_package(TBB) 失败且未强制 builtin 时直接 FATAL_ERROR,
                因此提供 with_tbb 选项映射, 默认关闭。
  - tracy / nanobind / fuzztest / assimp: 默认全关, 不涉及。

构建布局 (设备上原生构建, 非交叉):
  MANIFOLD_TEST=ON 构建 manifold_test (gtest_discover_tests 注册到 CTest)
  + samples 静态库 + extras 性能小程序。test() 通过 ctest 真实执行上游
  测试套件 (约 300+ 用例), 不以 test_package 替代。

R26/R27: BUILD_SHARED_LIBS 默认 OFF; 依赖引用 @ohpcd/stable。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, save


class ManifoldConan(ConanFile):
    name = "manifold"
    version = "3.5.2"
    description = "Geometry library for triangle meshes with robust boolean and Minkowski operations"
    license = "Apache-2.0"
    homepage = "https://github.com/elalish/manifold"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("geometry", "mesh", "csg", "boolean", "3d")

    package_type = "library"
    languages = "C++"
    implements = ["auto_shared_fpic"]

    # 表示编译产物架构与宿主机一致 (设备上原生构建)
    no_copy_source = False

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cross_section": [True, False],
        "with_tbb": [True, False],
        "cbind": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cross_section": True,
        "with_tbb": False,
        "cbind": True,
    }

    # CMakeDeps 生成 <pkg>-config.cmake 的文件名由 cmake_file_name 决定,
    # 上游 find_package(Clipper2) / find_package(GTest) 需要这两个名字
    # (而不是 conan 包名 clipper2/gtest)。
    # clipper2 包名的 cmake_file_name 是 "Clipper2", 其 CMakeDeps 会生成
    # Clipper2-config.cmake, 但目标名是全小写 clipper2 (由包名推导),
    # 与上游期望的 "Clipper2::Clipper2" 不一致 → 需要 alias 补丁。
    # gtest 包 cmake_file_name="GTest", 目标 GTest::gtest_main 直接匹配。

    def export_sources(self):
        # 本配方对上游零补丁: 依赖全走 find_package 快路径
        pass

    def requirements(self):
        if self.options.cross_section:
            # R27: 依赖制品仓中的 clipper2 (ohpcd 远端为无 channel 引用)
            self.requires("clipper2/2.0.1")
        if self.options.with_tbb:
            self.requires("tbb/2023.0.0")
        # GTest 以普通 requires 提供: CMakeDeps 会生成 GTestConfig.cmake,
        # 命中上游 find_package(GTest QUIET) 快路径 (而非 tool_requires,
        # 后者只注入 PATH 不生成 CMake config, 无法被 find_package 找到)。
        # 静态库不会进 DT_NEEDED, 无运行时污染。
        # visible=False: gtest 仅是构建期测试依赖, 不是消费者接口依赖,
        # 避免 Conan "unused dependency" 校验失败。
        self.requires("gtest/1.17.0", visible=False)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # 上游 cmake/manifoldDeps.cmake 对依赖目标名有两处硬编码期望:
        #   (a) src/CMakeLists.txt 链接 "Clipper2::Clipper2" (大写),
        #       而 CMakeDeps 生成 "Clipper2::clipper2" (小写组件名);
        #   (b) manifoldDeps.cmake:269 期望 find_package(GTest) 提供
        #       全局目标 "gtest_main" (再 alias 成 GTest::gtest_main),
        #       而 CMakeDeps 生成 "gtest::gtest_main" (若提供)。
        # CMAKE_PROJECT_INCLUDE 在 project() 后、manifoldDeps.cmake 之前
        # 注入, 此处 CMakeDeps 的 config 文件尚未被 find_package 加载,
        # 因此 shim 里主动 find_package 并建好上游期望的全部别名。
        shim = os.path.join(self.generators_folder, "manifold-deps-alias.cmake")
        save(self, shim, (
            "# Conan-generated shim: bridge CMakeDeps target names to the\n"
            "# names upstream manifoldDeps.cmake hardcodes.\n"
            "find_package(Clipper2 CONFIG QUIET)\n"
            "if(TARGET Clipper2::clipper2 AND NOT TARGET Clipper2::Clipper2)\n"
            "  add_library(Clipper2::Clipper2 ALIAS Clipper2::clipper2)\n"
            "endif()\n"
            "# ohpcd gtest 是单组件包: 只有 gtest::gtest 目标 (只链 libgtest),\n"
            "# 无 gtest_main 组件。上游 manifold_test 需要带 main() 的\n"
            "# GTest::gtest_main。此处从 gtest 包目录直接创建 IMPORTED 目标:\n"
            "# libgtest_main.a + libgtest.a (它依赖 gtest)。\n"
            "find_package(GTest CONFIG QUIET)\n"
            "# 上游 test/CMakeLists.txt 使用 gtest_discover_tests 但未 include\n"
            "# GoogleTest 模块 (上游自带的 FetchContent gtest 会顺带提供?)\n"
            "# 显式补上, 使命令在 Conan 依赖路径下可用。\n"
            "include(GoogleTest)\n"
            "if(NOT TARGET GTest::gtest_main)\n"
            "  get_target_property(_gtest_inc gtest::gtest INTERFACE_INCLUDE_DIRECTORIES)\n"
            "  add_library(GTest_gtest_main STATIC IMPORTED)\n"
            "  set_target_properties(GTest_gtest_main PROPERTIES\n"
            "    IMPORTED_LOCATION \"${gtest_PACKAGE_FOLDER_RELEASE}/lib/libgtest_main.a\"\n"
            "    IMPORTED_LINK_INTERFACE_LIBRARIES \"gtest::gtest\"\n"
            "    INTERFACE_INCLUDE_DIRECTORIES \"${_gtest_inc}\")\n"
            "  add_library(GTest::gtest_main ALIAS GTest_gtest_main)\n"
            "endif()\n"
        ))
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = shim
        # E092: CMake 无 HarmonyOS 平台模块; 本机为设备上原生构建,
        # 直接用 Linux 平台模型 (与 clipper2 2.0.1 先例一致)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # R26: 系统库默认静态
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 禁止上游构建期下载 (依赖已由 Conan 提供)
        tc.variables["MANIFOLD_DOWNLOADS"] = "OFF"

        # OHOS musl 完整性保护 (hmdfs hmmac=use_task): .so 一经写入,
        # 任何字节级改写都会被动态链接器拒绝加载 ("Error loading …
        # Permission denied")。cmake install 的 file(RPATH_CHANGE) 属于
        # 典型的字节级改写; 其根源是 CMakeDeps 给依赖 (即使全是静态库)
        # 注入 INTERFACE_LINK_DIRECTORIES, 使链接命令携带 build rpath
        # (指向 Conan cache 的绝对路径), install 时又被改写。
        # 本包的运行期依赖 (clipper2/gtest) 全部静态链接, 运行期 RUNPATH
        # 没有存在价值 — 直接禁用 RPATH 生成:
        #   链接输出即最终字节, install 为纯复制, 无 build-host 路径泄漏。
        if self.settings.os == "OHOS" and self.options.shared:
            tc.variables["CMAKE_SKIP_RPATH"] = "ON"

        # CMAKE_SKIP_RPATH 去掉 build 树 rpath 后, 上游 gtest_discover_tests
        # 的 POST_BUILD 探测与 ctest 运行需要 LD_LIBRARY_PATH 才能找到
        # build 树的 libmanifold.so.3 等。conan 2 中 build() 里修改
        # os.environ 或 generate() 里 append buildenv_info 都无法传导到
        # cmake 子进程 (run() 仅叠加 generators/ 下的 env 文件) — 因此
        # 这里写一个自定义 env 文件, build()/test() 以 env=[...] 方式
        # 与 conanbuildenv 一起 source (后者是前置追加, 不会覆盖)。
        self._conf_env = None
        if self.settings.os == "OHOS" and self.options.shared:
            base = os.path.join(self.folders.base_build, "build",
                                str(self.settings.build_type))
            env = Environment()
            for sub in ("src", "bindings/c", "samples"):
                env.append_path("LD_LIBRARY_PATH", os.path.join(base, sub))
            vars_ = env.vars(self, "build")
            lines = ["export %s=\"%s${%s:+:$%s}\"" % (k, v, k, k)
                     for k, v in vars_.items()]
            save(self, os.path.join(self.generators_folder,
                                    "ohos_buildpath_env.sh"),
                 "\n".join(lines) + "\n")
            self._conf_env = "ohos_buildpath_env"

        # 功能映射
        tc.variables["MANIFOLD_CROSS_SECTION"] = "ON" if self.options.cross_section else "OFF"
        tc.variables["MANIFOLD_PAR"] = "ON" if self.options.with_tbb else "OFF"
        # C 绑定 (manifoldc) 依赖 cross_section
        if not self.options.cross_section:
            tc.variables["MANIFOLD_CBIND"] = "OFF"
        else:
            tc.variables["MANIFOLD_CBIND"] = "ON" if self.options.cbind else "OFF"
        # 构建上游测试 (test() 用 ctest 真实执行)
        tc.variables["MANIFOLD_TEST"] = "ON"
        # 关闭无关功能
        tc.variables["MANIFOLD_PYBIND"] = "OFF"
        tc.variables["MANIFOLD_JSBIND"] = "OFF"
        tc.variables["MANIFOLD_FUZZ"] = "OFF"
        tc.variables["TRACY_ENABLE"] = "OFF"
        tc.variables["ASSIMP_ENABLE"] = "OFF"
        # 上游在非 top-level 下不走 -Werror, 这里保持默认
        tc.variables["MANIFOLD_STRICT"] = "OFF"
        tc.generate()

        # OHOS SDK 的 lld 依赖 llvm/lib 下 libxml2.so.16 (无 RUNPATH,
        # 纯靠加载器搜索), worker 上缺失会导致所有链接步骤失败。
        if self.settings.os == "OHOS":
            cc_conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc_path = cc_conf.get("cpp", "") or cc_conf.get("c", "")
            if cc_path and os.path.exists(cc_path):
                llvm_bin = os.path.dirname(os.path.realpath(cc_path))
                llvm_lib = os.path.normpath(os.path.join(llvm_bin, "..", "lib"))
                if os.path.isdir(llvm_lib):
                    current_ld = os.environ.get("LD_LIBRARY_PATH", "")
                    if llvm_lib not in current_ld:
                        os.environ["LD_LIBRARY_PATH"] = llvm_lib + (":" + current_ld if current_ld else "")

    def build(self):
        # LD_LIBRARY_PATH (build 树 .so 目录) 通过自定义 env 文件
        # ohos_buildpath_env.sh (见 generate) 与 conanbuild 一起激活。
        cmake = CMake(self)
        cmake.configure()
        env = ["conanbuild", self._conf_env] if self._conf_env else "conanbuild"
        cmake._build(env=env)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def test(self):
        # 真实执行上游测试套件 (gtest_discover_tests 注册进 CTest, 427 个用例),
        # 不用 test_package 替代。交叉构建到 OHOS 时本机即目标机 (设备上构建),
        # ctest 可直接执行。
        # CMAKE_SKIP_RPATH=ON (见 generate) 使 build 树产物不带 rpath —
        # manifold_test 运行时需通过 LD_LIBRARY_PATH 找到 build 树的
        # libmanifold.so.3 / libmanifoldc.so.3 (musl 按序搜索 env)。
        # LD_LIBRARY_PATH 已通过 CMake.test(env=...) 传入 (见 generate)。
        if not can_run(self):
            self.output.warning(
                "cannot run on this host: upstream ctest suite skipped")
            return
        cmake = CMake(self)
        env = ["conanbuild", "conanrun", self._conf_env] if self._conf_env \
            else ["conanbuild", "conanrun"]
        cmake.test(output_on_failure=True, env=env)

    def package_info(self):
        if self.options.cross_section:
            self.cpp_info.requires = ["clipper2::clipper2"]
        self.cpp_info.libs = ["manifold"]
        if self.options.with_tbb:
            self.cpp_info.requires.append("tbb::tbb")
        if self.options.cbind and self.options.cross_section:
            self.cpp_info.libs.append("manifoldc")
        # GTest 只是构建期测试依赖: 上游把它链进 manifold_test (不打包),
        # 但 Conan 校验要求 requires 里声明的依赖必须出现在
        # (cpp_info/components).requires 中。clipper2 是真实链接依赖;
        # gtest 不出现在 cpp_info.requires 会触发 unused-dependency 校验,
        # 因此用 visible_user_build 之外最直接的办法: 声明到 requires。
        # 注意: 静态 gtest 不进 libmanifold 的 DT_NEEDED (M7 会验证)。
        self.cpp_info.set_property("cmake_file_name", "manifold")
        self.cpp_info.set_property("pkg_config_name", "manifold")
        self.cpp_info.set_property(
            "cmake_target_name", "manifold::manifold"
        )
        # 上游公共头按 -I<include> + #include "manifold/xxx.h" 组织
        self.cpp_info.includedirs = ["include"]
        # C++17 是公共接口要求 (公共头使用 if constexpr / 结构化绑定等)
        self.cpp_info.cxxflags.append("-std=c++17")

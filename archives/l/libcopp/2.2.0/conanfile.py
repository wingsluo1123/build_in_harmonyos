#!/usr/bin/env python3
"""Conan recipe — libcopp 2.2.0 (CMake).

libcopp 是 C++ 协程库（协程上下文切换 + 协程任务调度器），支持 C++20
coroutine 与手写汇编双实现。上下文切换核心是 `src/libcopp/fcontext/asm/`
下的 **per-ABI 手写汇编**（jump/make/ontop × 各架构 ABI，共 72 个文件），
其中 aarch64 用 `*_arm64_aapcs_elf_gas.S`。

OHOS 适配要点（均为本仓实测，读数见 notes.md）：

1. **★ fcontext 平台探测必须显式指定**：CMake 在 HarmonyOS 上把处理器识别
   为 `unknown`（`CMAKE_HOST_SYSTEM_PROCESSOR=unknown` / `CMAKE_SYSTEM_NAME=HarmonyOS`），
   而上游 `src/libcopp/fcontext/detect/fcontext.detect.cmake` 的分支

       if(LIBCOPP_FCONTEXT_OS_PLATFORM MATCHES "unknown|i386|i686|x86_64|amd64")
         if(CMAKE_SIZEOF_VOID_P MATCHES 8)
           set(LIBCOPP_FCONTEXT_OS_PLATFORM "x86_64")

   会把 `unknown` 按指针宽度**硬回退成 x86_64** ⇒ aarch64 设备去编 x86_64
   上下文切换汇编，首错：

       src/libcopp/fcontext/asm/jump_x86_64_sysv_elf_gas.S:138:9:
         error: invalid operand / jmp *%r8

   修法 = 显式 `LIBCOPP_FCONTEXT_OS_PLATFORM=arm64`（armv8 ⇒ arm64），
   探测输出随即恢复 `arm64/aapcs/elf/gas`。
2. **子模块不在 tag 归档里**：`atframework/cmake-toolset` 是空目录且该 tag
   无 release 资产 ⇒ conandata 里按钉住 commit c911fe34 单独取一份。
3. **上游测试在构建期真实执行**：`PROJECT_ENABLE_UNITTEST=ON`，build() 里跑
   ctest（上游自带 test_manager，不需要外部测试框架；CI profile 下 64/64 全过，
   C++20 coroutine 路径启用时 144/144）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir


class LibcoppConan(ConanFile):
    name = "libcopp"
    version = "2.2.0"
    description = "C++ coroutine library with hand-written per-ABI fcontext assembly and coroutine scheduler"
    license = "MIT"
    homepage = "https://github.com/owent/libcopp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    # ★ 不需要任何外部测试框架：上游 test/ 用的是**自带的 test_manager**
    #   （test/frame/test_manager.cpp）。test/CMakeLists.txt 里的
    #   `find_package(GTest)` 是**非 REQUIRED** 的可选门，且真正被代码检查的宏是
    #   `UTILS_TEST_MACRO_TEST_ENABLE_GTEST`（test/frame/test_macros.h:26），
    #   而 CMake 定义的是 `COPP_MACRO_TEST_ENABLE_GTEST`（test/CMakeLists.txt:9）
    #   ⇒ gtest 分支在上游就是死代码，缺 gtest 测试照跑（W4 审计 P1 实证：
    #   link.txt 无 gtest 库、`nm -C libcopp_unit_test | grep -c "testing::"` = 0）。

    def layout(self):
        cmake_layout(self)

    def source(self):
        # ① 主源：上游 tag 归档
        get(self, **self.conan_data["sources"]["libcopp"], strip_root=True)
        # ② 子模块：tag 归档里是空目录（.gitmodules 钉在 c911fe34），
        #    且 v2.2.0 无 release 资产 ⇒ 按钉住 commit 单独取，铺进原路径。
        get(
            self,
            **self.conan_data["sources"]["cmake_toolset"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "atframework", "cmake-toolset"),
        )

    def generate(self):
        tc = CMakeToolchain(self)

        # ★ 核心适配：显式指定 fcontext 平台，避开上游 `unknown` ⇒ x86_64 硬回退。
        arch = str(self.settings.arch)
        fcontext_platform = "arm64" if arch in ("armv8", "armv8.3") else (
            "arm" if arch.startswith("arm") else arch
        )
        tc.cache_variables["LIBCOPP_FCONTEXT_OS_PLATFORM"] = fcontext_platform

        # 上游单元测试（构建期真实执行）
        tc.variables["PROJECT_ENABLE_UNITTEST"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        # 示例与基准程序不进交付包（R36 面最小化）
        tc.variables["PROJECT_ENABLE_SAMPLE"] = "OFF"

        if self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = "ON"

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # 上游测试套件真实执行（CI profile cppstd=17 下实测 64/64 全过；
        # 同源码在 C++20 coroutine 路径启用的原生配置下为 144/144，见 notes.md）。
        # --no-tests=error：注册为 0 个用例即判失败，防"空跑假绿"。
        self.run(
            'ctest --output-on-failure --no-tests=error --timeout 600',
            cwd=self.build_folder,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 install 会带一份自己的 libcopp-config.cmake（内含 include
        # libcopp-targets.cmake，而那是 conan 不生成的文件）。删掉它，让
        # CMakeDeps 生成的 config 成为唯一权威，避免消费者 find_package
        # 命中上游那份后报缺 libcopp-targets.cmake。
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libcopp")
        self.cpp_info.set_property("cmake_target_name", "libcopp::copp")
        # 上游 install 同时交付两个静态库：libcopp.a（上下文切换/栈/工具）
        # 与 libcotask.a（协程任务调度器，**依赖 copp**）。
        # 顺序必须 cotask 在前（静态库按命令行顺序解析符号）。
        self.cpp_info.libs = ["cotask", "copp"]
        # 上下文切换汇编只用 callee-saved 寄存器，无额外系统库依赖；
        # 协程调度器用到 pthread ⇒ 传 Threads。
        self.cpp_info.system_libs = ["pthread"]

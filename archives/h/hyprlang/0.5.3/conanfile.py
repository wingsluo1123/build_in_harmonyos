#!/usr/bin/env python3
"""Conan recipe for hyprlang 0.5.3 — CMake (C++23, SHARED libhyprlang.so).

The official implementation library for the hypr config language
(hyprcursor/hyprpicker 前置依赖). 唯一依赖 hyprutils（pkg_check_modules
hyprutils>=0.1.1）；upstream 提供 2 个 ctest 用例（Parsing/Fuzz）。
"""
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class HyprlangConan(ConanFile):
    name = "hyprlang"
    version = "0.5.3"
    description = "The official implementation library for the hypr config language"
    license = "LGPL-3.0"
    homepage = "https://github.com/hyprwm/hyprlang"
    url = "https://github.com/hyprwm/hyprlang"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # 导出 patches/ 目录（apply_conandata_patches 需要）
    exports_sources = "patches/*"

    def requirements(self):
        # CMakeLists: pkg_check_modules(deps REQUIRED IMPORTED_TARGET hyprutils>=0.1.1)
        self.requires("hyprutils/0.3.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 的 CMAKE_SYSTEM_NAME=HarmonyOS 平台模块未定义
        # CMAKE_SHARED_LIBRARY_SONAME_*_FLAG，CMake 因此既不传 -Wl,-soname
        # 也不生成版本化文件名，libhyprlang.so 缺 DT_SONAME（CI L5a 门禁，
        # attica/adwaita-qt 同款修法）：补回 soname 能力，让上游
        # set_target_properties(VERSION/SOVERSION 2) 重新生效
        for language in ("C", "CXX"):
            tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = (
                "-Wl,-soname,"
            )
        # CMakeLists pkg_check_modules(deps hyprutils>=0.1.1)：pkg-config 读的是
        # 环境变量 PKG_CONFIG_PATH（tc.variables 是 CMake 缓存变量，无效），
        # 用 Environment 脚本注入依赖 pkgconfig 路径
        env = Environment()
        pc_paths = []
        for dep in self.dependencies.values():
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                pc_paths.append(pc)
        if pc_paths:
            env.append_path("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        # 制品仓 hyprutils 包的 hyprutils.pc 里 prefix/includedir/libdir 是打包机
        # conan 临时缓存目录（.cache/conan2/p/b/<hash>/p，本机不存在）。CMake
        # pkg_check_modules 生成的 Imported target 在 generate 阶段校验 include
        # 路径存在性，坏路径直接报 "includes non-existent path"。复制 .pc 到
        # 生成目录并把失效的绝对路径改写为包真实路径，让 PKG_CONFIG_PATH 优先
        # 命中修正版（pixman prefix=/ 同类问题）。
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        for dep in self.dependencies.values():
            if dep.ref.name != "hyprutils":
                continue
            base = dep.package_folder
            pc_src = os.path.join(base, "lib", "pkgconfig", "hyprutils.pc")
            if os.path.isfile(pc_src):
                os.makedirs(fixed_pc_dir, exist_ok=True)
                with open(pc_src, "r", encoding="utf-8") as f:
                    content = f.read()
                content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
                content = re.sub(r"(?m)^includedir=.*$", f"includedir={base}/include", content)
                content = re.sub(r"(?m)^libdir=.*$", f"libdir={base}/lib", content)
                with open(os.path.join(fixed_pc_dir, "hyprutils.pc"), "w",
                          encoding="utf-8", newline="\n") as f:
                    f.write(content)
                env.prepend_path("PKG_CONFIG_PATH", fixed_pc_dir)
                self.output.info(
                    f"hyprlang: fixed hyprutils.pc prefix -> {base}"
                )
        # OHOS SDK 的 lld 运行时依赖 libxml2.so.16（llvm/lib 目录），
        # CI Worker 上 LD_LIBRARY_PATH 未含该目录导致 clang 调用 lld 时
        # 编译器检测/链接失败，注入即可（hyprutils 配方同款兜底）
        llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib"
        )
        if os.path.isdir(llvm_lib):
            env.append_path("LD_LIBRARY_PATH", llvm_lib)
        env.vars(self).save_script("conanbuild_env")
        # 依赖头目录以 -isystem 注入兜底：即使 .pc Cflags 异常，
        # <hyprutils/string/VarList.hpp> 等也能解析（hyprutils 配方同款）
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                tc.extra_cxxflags.append(f"-isystem{inc}")
                tc.extra_cflags.append(f"-isystem{inc}")
        # 生成 conanrun.sh：注入依赖（hyprutils）共享库路径，test_package
        # 运行时需要 libhyprutils.so
        VirtualRunEnv(self).generate()
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 应用 conandata.yml 注册的补丁（0001: std::expected → 本地等价结构；
        # 0002: std::format → 字符串拼接。OHOS libc++ 15 缺 <expected>/<format>）
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试：ctest 2 例（Parsing/Fuzz，WORKING_DIRECTORY=源码 tests/，
        # 相对读取 ./config/*.conf，无网络/主题依赖）。显式注入
        # LD_LIBRARY_PATH：build 目录（libhyprlang.so）+ 依赖 lib 目录
        # （libhyprutils.so），否则测试二进制加载共享库失败
        lib_dirs = [self.build_folder]
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                lib_dirs.append(libdir)
        ld_path = ":".join(lib_dirs)
        self.run(
            f"export LD_LIBRARY_PATH=\"{ld_path}:$LD_LIBRARY_PATH\"; "
            "ctest --output-on-failure",
            env=["conanbuild", "conanbuild_env"],
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hyprlang"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "hyprlang")

#!/usr/bin/env python3
"""Conan recipe — otpclient 5.1.5

上游: https://github.com/paolostivanin/OTPClient
语言/构建: C / CMake >= 3.25（GTK4 + libadwaita 桌面应用 + CLI + D-Bus search provider）

配方要点
- 上游全部依赖通过 pkg-config 探测（CMakeLists.txt:101-117 的 pkg_check_modules）
  与 CMakeLists.txt:183 的 pkg_get_variable，因此必须用 PkgConfigDeps 生成 .pc
  文件供 PKG_CONFIG_PATH 使用（与仓库 glib/libsecret 配方同策）。
- 上游不产出任何库目标（全树无 add_library），产物是 3 个可执行程序，
  故 package_type = "application"，并在软件级目录声明 commands.json（R38）。
- 上游测试（tests/CMakeLists.txt 注册 16 个 CTest）由标准 BUILD_TESTING 开关控制；
  本配方默认开启，build() 内由 ctest 实际执行（R51：上游用例跑全）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class OtpclientConan(ConanFile):
    name = "otpclient"
    version = "5.1.5"
    description = "Highly secure OTP (TOTP/HOTP) client for the desktop — GTK4 GUI + CLI + D-Bus search provider"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/paolostivanin/OTPClient"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "gui": [True, False],
        "cli": [True, False],
        "search_provider": [True, False],
        "tests": [True, False],
    }
    default_options = {
        # 上游默认 GUI=ON，但 GUI 构建期必须执行宿主工具 glib-compile-resources
        # （src/gui/CMakeLists.txt:5 裸名调用，靠 PATH 解析）。本环境 PATH 上是 HNP
        # 系统版（glib 2.38.2），其 RUNPATH 指向构建机路径 → 找不到 libffi.so.8，
        # exit 127；而依赖链 8 个 libdir 里没有 libffi.so.8，无法在不写死本地路径的
        # 前提下补齐。故默认交付 CLI + search provider，GUI 留 -o gui=True 开关
        # 供宿主工具可用时启用（证据见 notes.md「GUI 未构建的实测证据」）。
        "gui": False,
        "cli": True,
        "search_provider": True,
        "tests": True,
    }

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # 核心依赖 —— 上游 CMakeLists.txt:102-108 全为 pkg_check_modules(... REQUIRED ...)
        self.requires("glib/2.84.0.1")       # glib-2.0 >= 2.74.0 与 gio-2.0 >= 2.74.0
        self.requires("libgcrypt/1.11.0")    # libgcrypt >= 1.10.1（与 libsecret 同版对齐）
        self.requires("libcotp/4.2.1")       # cotp >= 4.0.0
        self.requires("jansson/2.15.1.1")    # jansson >= 2.13
        self.requires("libuuid/2.42.2")      # uuid >= 2.30.0
        self.requires("libsecret/0.21.7")    # libsecret-1 >= 0.20.0
        # GUI 依赖 —— 上游 CMakeLists.txt:111-116，受 BUILD_GUI（:110）约束
        if self.options.gui:
            self.requires("gtk4/4.22.4")            # gtk4 >= 4.10.0
            self.requires("libadwaita/1.8.8")       # libadwaita-1 >= 1.5.0
            self.requires("gdk-pixbuf/2.44.6")      # gdk-pixbuf-2.0（与 gtk4 同版对齐）
            self.requires("zbar/0.23.93")           # zbar >= 0.20
            self.requires("protobuf-c/1.5.1")       # libprotobuf-c >= 1.3.0
            self.requires("qrencode/4.1.1.1")       # libqrencode >= 4.0.0

    def export_sources(self):
        export_conandata_patches(self)
        # compat/explicit-bzero.h 是适配产物，随配方导出（见 source() 的说明）。
        copy(self, "compat/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # compat/explicit-bzero.h 以"配方导出源文件"（exports_sources）方式随包发布，
        # 而不是用"新建文件"型补丁：conan 2.x 用 patch_ng 应用补丁，创建型补丁
        # （--- a/新文件 @@ -0,0）在目标父目录不存在时 apply() 返回 False →
        # ConanException: Failed to apply patch。
        # 导出源会被 conan 直接落到源码目录（.../s/），故此处无需再拷贝。
        # CMakeLists.txt 补丁里的 -include .../compat/explicit-bzero.h 因此必然可解析。

    def _normalize_glib_component_refs(self):
        """把依赖包 cpp_info 里的 glib 短组件名归一为 ohpc glib 配方声明的名字。

        背景：ohpc 的 glib 配方声明的是 glib-2.0 / gobject-2.0 / gio-2.0 / gmodule-2.0 /
        gthread-2.0，而相当多已发布依赖包的 cpp_info 仍写旧短名（glib::glib /
        glib::gobject / glib::gio …）。PkgConfigDeps 生成 .pc 时解析不到组件会直接中止：
            ConanException: Component 'glib::gobject' not found in 'glib' package requirement
        这里做消费者侧归一（不修改任何依赖包），与本仓库 libedataserverui4/3.60.2 的
        既有处理同构。
        """
        alias = {
            "glib": "glib-2.0",
            "gobject": "gobject-2.0",
            "gmodule": "gmodule-2.0",
            "gthread": "gthread-2.0",
            "gio": "gio-2.0",
        }

        def fix(refs):
            out = []
            for ref in refs:
                pkg, sep, comp = ref.partition("::")
                if sep and pkg == "glib" and comp in alias:
                    ref = f"glib::{alias[comp]}"
                out.append(ref)
            return out

        for dep in self.dependencies.values():
            if dep.cpp_info.requires:
                dep.cpp_info.requires = fix(dep.cpp_info.requires)
            for comp in dep.cpp_info.components.values():
                if comp.requires:
                    comp.requires = fix(comp.requires)

    def _align_pkg_config_names(self):
        """把依赖包产出的 .pc 名对齐到上游 pkg_check_modules 探测的模块名。

        上游 CMakeLists.txt:103/116 探测的是 `cotp` 与 `libqrencode`，而对应依赖包默认
        产出 `libcotp.pc` / `qrencode.pc`（配方未声明 pkg_config_name）→ pkg_check_modules
        REQUIRED 直接 Configure 失败。这里在消费者侧补属性，不改依赖包。
        """
        self.dependencies["libcotp"].cpp_info.set_property("pkg_config_name", "cotp")
        if self.options.gui:
            self.dependencies["qrencode"].cpp_info.set_property("pkg_config_name", "libqrencode")

    def _append_intl_to_glib_pc(self):
        """给 glib 系 .pc 的 Libs 补上 glib 自带的 gettext 代理库（知识 E142）。

        背景：glib 包的 include/libintl.h 是它自带的 gettext 代理，把
        gettext/dgettext/ngettext 重定向到 g_libintl_* 符号；这些符号只由该包
        lib/libintl.so(.8) 导出（制品仓独立的 libintl/0.26.1 没有 gnulib 改名后的
        g_libintl_* 符号），而 glib 系 .pc 的 Libs 里没有 -lintl → 上游所有用 _()
        的目标链接期都报 undefined symbol: g_libintl_gettext。

        在消费者侧补进 .pc：不修改依赖包，也不用全局链接标志——全局标志会落到
        CMake 编译器自检的链接行上（那时还没有 -L 指向 glib 的 lib 目录）。
        -L 本就由 glib 自身 .pc 提供，故只补库名。
        """
        for name in ("glib-2.0", "gio-2.0"):
            pc = os.path.join(self.generators_folder, f"{name}.pc")
            if not os.path.exists(pc):
                continue
            with open(pc, encoding="utf-8") as fh:
                lines = fh.readlines()
            changed = False
            for idx, line in enumerate(lines):
                if line.startswith("Libs:") and "-lintl" not in line:
                    lines[idx] = line.rstrip("\n") + " -lintl\n"
                    changed = True
            if changed:
                with open(pc, "w", encoding="utf-8") as fh:
                    fh.writelines(lines)

    def generate(self):
        # 依赖包 cpp_info 里残留的 glib 短组件名会中止 PkgConfigDeps，先归一
        self._normalize_glib_component_refs()
        # 上游探测的模块名与依赖包产出名不一致的对齐
        self._align_pkg_config_names()
        # 上游靠 pkg-config 找依赖，必须生成 .pc 文件并让 PKG_CONFIG_PATH 指过去
        PkgConfigDeps(self).generate()
        # glib 系 .pc 缺 gettext 代理库（见 _append_intl_to_glib_pc）
        self._append_intl_to_glib_pc()

        tc = CMakeToolchain(self)
        # 平台类修复（消费者侧，不改依赖包；两条都有知识库对应条目）
        # ① OHOS/musl 在 -std=c11（上游 CMAKE_C_EXTENSIONS OFF）下不暴露 POSIX 声明：
        #    struct sigaction 成不完整类型、sigemptyset/sigaction 未声明，被上游
        #    -Werror=implicit-function-declaration 直接判死 → 打开 _GNU_SOURCE（知识 E032）
        tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.variables["BUILD_GUI"] = self.options.gui
        tc.variables["BUILD_CLI"] = self.options.cli
        tc.variables["BUILD_SEARCH_PROVIDER"] = self.options.search_provider
        tc.variables["BUILD_TESTING"] = self.options.tests
        # 上游默认项：非 flatpak 打包、不启用托盘最小化（OHOS 无此桌面环境语义）
        tc.variables["IS_FLATPAK"] = False
        tc.variables["ENABLE_MINIMIZE_TO_TRAY"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.tests:
            # R51：上游用例跑全（tests/CMakeLists.txt 注册 16 项）。
            # 注意 cmake.test(cli_args=...) 的参数是交给构建工具而非 ctest 的，
            # 故这里直接调 ctest；--no-tests=error 保证"零用例"不会被当成通过。
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure --no-tests=error',
                env="conanrun",
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

#!/usr/bin/env python3
"""Conan recipe — fcitx5 5.1.14.

fcitx5 是输入法框架核心库（Fcitx5Core/Fcitx5Config/Fcitx5Utils 组件 + addon
模块 + test 可执行）。上游 CMake 顶层直接构建（非 staging wrapper），
与 fcitx5-utils 5.1.13（仅 Fcitx5Utils 组件）同源不同边界：本包构建并导出
libFcitx5Utils.so / libFcitx5Config.so / libFcitx5Core.so / Fcitx5::Utils /
Fcitx5::Config / Fcitx5::Core 及 addon 模块，供 libime / libime-jyutping /
其他输入法组件消费。

OHOS 平台裁剪：
- 禁用 X11/Wayland/DBus/Enchant/Emoji/Keyboard 子系统（OHOS PC 无对应
  系统服务，源码内未实现 OHOS 后端，禁用以获得可运行的最小核心闭包）。
- EVENT_LOOP_BACKEND=libuv：sysroot 自带 libuv（uv.h + libuv.so），
  event_none 后端 createDefaultEventLoop 返回 nullptr 会导致核心测试
  （testevent/testinputcontext/testinstance/testunicode/testquickphrase 等）
  抛 "No available event loop implementation"；本配方以 libuv 后端修复。
- ENABLE_SERVER=Off：以嵌入式库形态交付（上游文档注释明示
  "disable this option if you want to use fcitx as an embedded library"）。
- 上游测试（test/ 目录 38 个注册可执行）已在 Step2 实机全部编译并实际
  运行通过（38/38，完整台账与日志见 notes.md）；配方构建取最小闭包
  （ENABLE_TEST=Off，仅库+模块），避免 CI 全量测试目标拖长构建。测试
  统计以 notes.md 双口径台账为准，不以配方构建目标数替代。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Fcitx5Conan(ConanFile):
    name = "fcitx5"
    version = "5.1.14"
    description = "Fcitx5 input method framework core library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/fcitx/fcitx5"
    url = "https://github.com/fcitx/fcitx5"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # CMakeToolchain 在 generate() 中手动实例化（需设置 OHOS CMAKE_SYSROOT），
    # 故此处只声明 CMakeDeps。
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ECM：ecm_setup_version / ECMUninstallTarget（顶层 CMakeLists 直接
        # include(ECMUninstallTarget)，6.19.0 包缺 ecm_uninstall.cmake.in，
        # 必须用 6.29.0+；fctix5-utils 5.1.13 因 wrapper 不含该 include 才可用
        # 6.19.0）。
        self.tool_requires("extra-cmake-modules/6.29.0")
        # libuv：EVENT_LOOP_BACKEND=libuv 需要 uv.h + libuv.so（ohpcd 已发布）
        self.requires("libuv/1.52.1")
        # gettext：libintl（OHOS libc 无 dgettext，sysroot libintl.h 空壳无声明）
        self.requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 加载器实测拒绝加载 RUNPATH 指向 conan 缓存目录的库
        # （dlopen 报 "Permission denied"）。conan 的 SkipRPath block 默认
        # skip_rpath=False（不设置 CMAKE_SKIP_RPATH），CMake 会在 install
        # 时给库写 RUNPATH 指向包缓存路径 → 本机实测被拒。必须显式
        # CMAKE_SKIP_RPATH=ON，使库不带 RUNPATH；运行库定位交给消费者
        # conanrun 环境（LD_LIBRARY_PATH，与 fcitx5-utils 5.1.13 同先例，
        # 本机实测可正常加载）。
        tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
        # OHOS：显式声明系统名。CMake 不认识 HarmonyOS 平台（无 platform
        # module），不设 CMAKE_SYSTEM_NAME 时 ecm_setup_version 生成的
        # SOVERSION 不会应用于库输出（无 -Wl,-soname、输出不带版本后缀），
        # 消费者运行时报 "Error loading shared library ../../../bin/..."。
        # Step2 手动构建即设 -DCMAKE_SYSTEM_NAME=OHOS 验证通过。
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # Fcitx5CompilerSettings 要求 C++20；CI profile 可能是 cppstd=17，
        # 直接覆盖 cppstd 块（普通变量遮蔽 CACHE 变量，见 fcitx5-utils 先例）
        if self.settings.compiler.cppstd != "20":
            tc.blocks["cppstd"].values = {"cppstd": "20", "cppstd_extensions": "OFF"}
        # OHOS：CMAKE_SYSROOT 必须显式设置，否则 find_path/find_library
        # 搜不到 sysroot 下的头文件/库（编译器默认 sysroot 不影响 find_*）
        if self.settings.os == "OHOS":
            import glob as _glob
            sdk_native = sorted(
                _glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native"))
            if sdk_native:
                sysroot = os.path.join(sdk_native[-1], "sysroot")
                tc.variables["CMAKE_SYSROOT"] = sysroot
                self.output.info("OHOS CMAKE_SYSROOT = %s" % sysroot)
                # CMake 不认识 HarmonyOS 平台，交叉模式下 find_* 不自动搜
                # sysroot，显式加入 include 搜索路径
                tc.cache_variables["CMAKE_INCLUDE_PATH"] = os.path.join(
                    sysroot, "usr", "include")
        # OHOS sysroot 的 libintl.h 是空壳（无 gettext/bindtextdomain 声明），
        # 强制 LibIntl_INCLUDE_DIR/LIBRARY 指向 gettext 包真实 libintl
        gettext_pkg = self.dependencies.get("gettext")
        if gettext_pkg and gettext_pkg.package_folder:
            tc.cache_variables["LibIntl_INCLUDE_DIR"] = os.path.join(
                gettext_pkg.package_folder, "include")
            tc.cache_variables["LibIntl_LIBRARY"] = os.path.join(
                gettext_pkg.package_folder, "lib", "libintl.a")
        # po/ 翻译 .mo 生成使用 GETTEXT_MSGFMT_EXECUTABLE（Fcitx5Macros
        # fcitx5_install_translation 宏），conan create 环境 find_program
        # 找不到 msgfmt 会得到空命令。显式指向系统 gettext 工具
        # （/data/service/hnp/bin/msgfmt 0.26 实测可运行；gettext 包仅提供
        # libintl，其 bin/msgfmt 依赖未 relocated 的共享库不可直接运行）。
        tc.cache_variables["GETTEXT_MSGFMT_EXECUTABLE"] = "/data/service/hnp/bin/msgfmt"
        tc.cache_variables["GETTEXT_MSGMERGE_EXECUTABLE"] = "/data/service/hnp/bin/msgmerge"
        # msgfmt --xml（data/ 的 metainfo.xml 生成）需要 ITS 规则，
        # 通过 GETTEXTDATADIR 指向 hnp 系统 gettext 的 its 目录
        # （Step2 实测：不设此变量报 "cannot locate ITS rules"）
        import glob as _g
        _its = sorted(_g.glob("/data/service/hnp/gettext.org/gettext_*/share/gettext-*/its"))
        if _its:
            self.buildenv.append("GETTEXTDATADIR", _its[-1].replace("/its", ""))
        # libuv 由 pkg_check_modules(LibUV IMPORTED_TARGET "libuv") 探测。
        # libuv 包自带的 libuv.pc 的 prefix=/usr/local（conan 包未 relocated），
        # pkg-config 会解析出错误的 -L/usr/local/lib；且 cache_variables 中的
        # PKG_CONFIG_PATH 不会作为环境变量传给 pkg-config。这里在生成目录写出
        # 修正 prefix 的 libuv.pc 并通过 toolchain 环境变量注入 PKG_CONFIG_PATH。
        libuv_pkg = self.dependencies.get("libuv")
        if libuv_pkg and libuv_pkg.package_folder:
            pc_dir = os.path.join(self.generators_folder, "pkgconfig")
            os.makedirs(pc_dir, exist_ok=True)
            import textwrap as _tw
            with open(os.path.join(pc_dir, "libuv.pc"), "w") as _f:
                _f.write(_tw.dedent("""\
                    prefix=%s
                    exec_prefix=${prefix}
                    libdir=${prefix}/lib
                    includedir=${prefix}/include

                    Name: libuv
                    Version: 1.52.1
                    Description: libuv pkg-config for fcitx5 build (relocated)
                    Libs: -L${libdir} -luv -lpthread -ldl -lrt -lm
                    Cflags: -I${includedir}
                    """ % libuv_pkg.package_folder))
            self.buildenv.append("PKG_CONFIG_PATH", pc_dir)
        tc.generate()

    def source(self):
        # strip_root=True：tarball 顶层目录 fcitx5-5.1.14 被剥掉，
        # 源码直接落在 source 根，patch (a/ 前缀 -p1) 路径正确
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(cli_args=[
            "-DENABLE_X11=Off",
            "-DENABLE_WAYLAND=Off",
            "-DENABLE_DBUS=Off",
            "-DENABLE_ENCHANT=Off",
            "-DENABLE_EMOJI=Off",
            "-DENABLE_KEYBOARD=Off",
            "-DENABLE_LIBUUID=Off",
            "-DENABLE_SERVER=Off",
            "-DUSE_SYSTEMD=Off",
            "-DEVENT_LOOP_BACKEND=libuv",
            "-DBUILD_SPELL_DICT=Off",
            "-DENABLE_TEST=Off",
            "-DENABLE_TESTING_ADDONS=Off",
        ])
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（仓库先例）
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游 install 产出独立的 CMake 包配置：Fcitx5UtilsConfig.cmake /
        # Fcitx5ConfigConfig.cmake / Fcitx5CoreConfig.cmake，目标名
        # Fcitx5::Utils / Fcitx5::Config / Fcitx5::Core。用 components 映射，
        # 使 CMakeDeps 为消费者生成同名 find_package 包
        self.cpp_info.components["utils"].libs = ["Fcitx5Utils"]
        self.cpp_info.components["utils"].includedirs = ["include/Fcitx5/Utils"]
        self.cpp_info.components["utils"].set_property(
            "cmake_file_name", "Fcitx5Utils")
        self.cpp_info.components["utils"].set_property(
            "cmake_target_name", "Fcitx5::Utils")
        self.cpp_info.components["config"].libs = ["Fcitx5Config"]
        self.cpp_info.components["config"].includedirs = ["include/Fcitx5/Config"]
        self.cpp_info.components["config"].set_property(
            "cmake_file_name", "Fcitx5Config")
        self.cpp_info.components["config"].set_property(
            "cmake_target_name", "Fcitx5::Config")
        self.cpp_info.components["core"].libs = ["Fcitx5Core"]
        self.cpp_info.components["core"].includedirs = ["include/Fcitx5/Core"]
        self.cpp_info.components["core"].set_property(
            "cmake_file_name", "Fcitx5Core")
        self.cpp_info.components["core"].set_property(
            "cmake_target_name", "Fcitx5::Core")
        # 组件依赖关系（上游 Core 链接 Config/Utils）
        self.cpp_info.components["config"].requires = ["utils"]
        self.cpp_info.components["core"].requires = ["config", "utils"]
        self.cpp_info.components["core"].requires.append("libuv::libuv")
        self.cpp_info.components["core"].requires.append("gettext::gettext")

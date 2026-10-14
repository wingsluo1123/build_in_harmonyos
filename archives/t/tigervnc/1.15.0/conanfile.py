#!/usr/bin/env python3
"""Conan recipe — tigervnc 1.15.0 (CMake)

上游 TigerVNC 是「VNC 客户端 + X 服务器 + 工具」的整套发行版。核心 RFB 协议层
（common/os、common/rdr、common/network、common/rfb）与 X11/FLTK 无关，可以在
OpenHarmony PC（aarch64, musl）上编译并运行；依赖 X11 + FLTK 的 vncviewer、
依赖 Xorg 源码树的 Xvnc、依赖 PAM 的 vncsession 在 OHOS 上不可构建（原因见
notes.md 与 reports/adaptation-analysis.md）。

因此本配方 **只提供 RFB 协议核心库**（静态库 os/rdr/network/rfb），把
BUILD_VIEWER/BUILD_SERVER 默认置 OFF，并按需关闭 GnuTLS/Nettle/PAM：

- OHOS 无 X11（无 libX11/Xext/Xdamage/Xfixes/Xrandr/Xtst，也无 X server），
  上游顶层 CMakeLists 的 `find_package(X11 REQUIRED)` 在 OHOS 上必然失败；
- 上游 `find_package(FLTK REQUIRED)` 要求 FLTK 1.3.x，OHOS 侧无 FLTK；
- 上游对 UNIX 无条件 `FATAL_ERROR "Could not find PAM development files"`，
  OHOS 无 security/pam_appl.h 与 libpam。

前两条用 0001 补丁把 X11 的 REQUIRED 探测限定为「非 OHOS」，第三条把 PAM 探测
改为受 ENABLE_PAM 控制。补丁只放宽真的无法满足的硬门禁，不改动任何算法代码。

关闭 GnuTLS/Nettle 后，common/rfb 不会编译 SSecurityPlain.cxx /
SSecurityRSAAES.cxx，因此 `rfb/UnixPasswordValidator.cxx` 与 `rfb/pam.c` 不再被
任何目标引用，无需 PAM 即可完整构建核心库；认证侧仍保留 VNC 内置的 VncAuth
（DES 挑战响应）与 SSecurityStack 框架。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps

# 上游 tests/unit 的全部 8 个可执行文件。gesturehandler 与 emulatemb 需额外源码
# （vncviewer/GestureHandler.cxx、vncviewer/EmulateMB.cxx + i18n.h），上游在非
# WIN32/APPLE 平台上会一并构建，实测在 OHOS 上同样可以构建并运行，故全部纳入。
UNIT_TESTS = [
    "configargs",
    "conv",
    "convertlf",
    "gesturehandler",
    "hostport",
    "pixelformat",
    "unicode",
    "emulatemb",
]


def resolve_lib(libdir, stem):
    """Resolve a Conan library stem to a linkable file path inside libdir.

    Upstream FindPixman passes PIXMAN_LIBRARIES straight to
    target_link_libraries, so the value must be an existing path. Conan records
    only the bare stem ("pixman-1"), so probe the extensions actually present
    instead of assuming one.
    """
    for name in ("lib%s.so", "%s.lib", "lib%s.a", "lib%s.dylib"):
        candidate = os.path.join(libdir, name % stem)
        if os.path.exists(candidate):
            return candidate
    # Versioned-only shared object (libfoo.so.1) as a last resort.
    prefix = "lib%s.so." % stem
    try:
        for entry in sorted(os.listdir(libdir)):
            if entry.startswith(prefix):
                return os.path.join(libdir, entry)
    except OSError:
        pass
    return None


class TigerVNCConan(ConanFile):
    name = "tigervnc"
    version = "1.15.0"
    description = "High performance, multi-platform VNC client and server (RFB protocol core for OpenHarmony PC)"
    license = "GPL-2.0-or-later"
    homepage = "https://tigervnc.org/"
    url = "https://github.com/TigerVNC/tigervnc"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "pam": [True, False],
        "gnutls": [True, False],
        "nettle": [True, False],
        "viewer": [True, False],
        "server": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "pam": False,
        "gnutls": False,
        "nettle": False,
        "viewer": False,
        "server": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 上游 find_package(ZLIB REQUIRED) / (JPEG REQUIRED) / (Pixman REQUIRED)：
        # zlib 与 libjpeg-turbo 的 recipe 分别导出 ZLIB::ZLIB 与
        # libjpeg-turbo::libjpeg-turbo（FindJPEG 兜底可直接解析出 libjpeg.so）。
        # pixman 的 recipe 导出的 CMake 包名是 pixman（小写），而上游调用的是
        # find_package(Pixman)，两者对不上，故在 generate() 中补一个 Pixman 别名。
        self.requires("zlib/1.3.2.1")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("pixman/0.46.4.3")

        if self.options.gnutls:
            self.requires("gnutls/3.8.10")
        if self.options.nettle:
            self.requires("nettle/3.10.2.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 补丁在 source() 阶段打，而不是 build()：
        # 1) conan 2 的 source() 每个源码目录只执行一次，build() 在重跑/重试时可能
        #    二次进入（真机实测：上一次 create 仍在运行时再次 create，会复用同一个
        #    build 目录，补丁被二次应用而报
        #    "hunk no.1 doesn't match source file ... source file is different"）；
        # 2) 源码一旦解包就处于最终形态，与 conan-* 命令的 expectation 一致。
        apply_conandata_patches(self)

    def generate(self):
        # OHOS 适配版 conan 把 settings.os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，
        # 而随设备分发的 CMake 只带 Modules/Platform/OHOS.cmake，会报
        # "System is unknown to cmake, create: Platform/HarmonyOS"。显式钉住 OHOS
        # 使两种映射结果一致（CMake >= 3.28 官方支持 OHOS 平台模块）。
        if self.settings.os == "OHOS":
            self.conf_info.define("tools.cmake.cmaketoolchain:system_name", "OHOS")

        deps = CMakeDeps(self)
        # pixman 的 Conan CMake 包名是 pixman，上游找的是 Pixman。
        deps.set_property("pixman", "cmake_file_name", "Pixman")
        deps.set_property("pixman", "cmake_target_name", "Pixman::Pixman")
        deps.generate()
        PkgConfigDeps(self).generate()

        # 上游 cmake/Modules/FindPixman.cmake 优先走 pkg_check_modules(PIXMAN
        # pixman-1)。本仓 pixman 配方不安装 .pc 文件，OHOS 侧也不保证有
        # pkg-config，于是模块退化为 find_path/find_library，解析不出 pixman.h
        # （真机实测 common/rfb/Region.cxx: fatal error: 'pixman.h' file not
        # found）。PIXMAN_INCLUDE_DIRS / PIXMAN_LIBRARIES 是
        # find_package_handle_standard_args 直接读取的缓存变量，预先给定即可让
        # Pixman_FOUND 成立，不必改动上游或他人的 pixman 配方。
        pixman = self.dependencies["pixman"].cpp_info
        pixman_inc = [d for d in pixman.includedirs if os.path.isdir(d)]
        pixman_lib = [d for d in pixman.libdirs if os.path.isdir(d)]

        tc = CMakeToolchain(self)
        if pixman_inc:
            tc.variables["PIXMAN_INCLUDE_DIRS"] = ";".join(pixman_inc)
        if pixman_lib and pixman.libs:
            resolved = [
                path
                for d in pixman_lib
                for stem in pixman.libs
                for path in [resolve_lib(d, stem)]
                if path
            ]
            if resolved:
                tc.variables["PIXMAN_LIBRARIES"] = ";".join(resolved)
        tc.variables["ENABLE_NLS"] = False
        tc.variables["ENABLE_PAM"] = bool(self.options.pam)
        tc.variables["ENABLE_GNUTLS"] = bool(self.options.gnutls)
        tc.variables["ENABLE_NETTLE"] = bool(self.options.nettle)
        tc.variables["ENABLE_H264"] = False
        tc.variables["ENABLE_PWQUALITY"] = False
        # 补丁新增的开关：控制 X11 专用 unix/ 工具子树（tx/vncconfig/
        # vncpasswd/vncserver/x0vncserver）。由 viewer 选项驱动，因为该子树
        # 与 vncviewer 同属「需要 X11 的交互式工具」层。
        tc.variables["ENABLE_X11_TOOLS"] = bool(self.options.viewer)
        # tests/perf 是基准测试（未注册 ctest），链接它们需要
        # rfb::PasswordValidator 的 vtable，而该类无 key function、vtable 不被发出
        # （上游潜在缺陷）。库本体与 tests/unit 不受影响，故关闭基准测试。
        tc.variables["ENABLE_PERF_TESTS"] = False
        tc.variables["BUILD_JAVA"] = False
        tc.variables["BUILD_VIEWER"] = bool(self.options.viewer)
        tc.variables["BUILD_SERVER"] = bool(self.options.server)
        tc.variables["INSTALL_SYSTEMD_UNITS"] = False
        tc.generate()
        # 依赖是共享库（libjpeg/libpixman），上游单测可执行文件运行时需要
        # 找到它们；否则报 "Error loading shared library libjpeg.so.62"。
        VirtualRunEnv(self).generate()

    def _cmake(self):
        cmake = CMake(self)
        cmake.configure(variables={"BUILD_TIMESTAMP": "2026-01-01 00:00"})
        return cmake

    def build(self):
        # 补丁已在 source() 阶段应用，这里不再重复调用（见 source() 注释）。
        cmake = self._cmake()
        cmake.build()
        if can_run(self):
            self._run_upstream_unit_tests()

    def _run_upstream_unit_tests(self):
        """在 build 阶段执行上游 tests/unit 的可执行文件（L1c）。

        上游只 add_executable，没有 add_test，因此 ctest 里 0 个用例——用 ctest
        会「跑 0 个测试然后成功」。这里直接找到并运行二进制，失败即抛错。
        """
        tests_dir = os.path.join(self.build_folder, "tests", "unit")
        if not os.path.isdir(tests_dir):
            tests_dir = os.path.join(self.build_folder, "Release", "tests", "unit")
        if not os.path.isdir(tests_dir):
            raise ConanException("unit test dir not found under %s"
                                 % self.build_folder)

        missing = [t for t in UNIT_TESTS
                   if not os.path.isfile(os.path.join(tests_dir, t))]
        if missing:
            raise ConanException("expected unit tests were not built: %s"
                                 % ", ".join(missing))

        self.output.info("running %d upstream unit tests" % len(UNIT_TESTS))
        for name in UNIT_TESTS:
            self.run('"%s"' % os.path.join(tests_dir, name), env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 本包是自包含的核心库：删掉由依赖注入的 CMake/pkg-config 文件，
        # 避免把依赖路径写死进本包，也避免污染下游的 find_package 结果。
        # 核心库是静态库：鸿蒙 PC 上 .so 需要 ELF 代码签名，静态链接既规避
        # 签名问题，也避免与系统同名库冲突。
        for stale in ("lib/cmake", "lib/pkgconfig", "share/pkgconfig",
                      "lib/systemd", "etc/pam.d"):
            stale_path = os.path.join(self.package_folder, stale)
            if os.path.isdir(stale_path):
                shutil.rmtree(stale_path, ignore_errors=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tigervnc")
        self.cpp_info.set_property("cmake_target_name", "tigervnc::rfb")
        self.cpp_info.set_property("pkg_config_name", "tigervnc")

        # 补丁把 common/{os,rdr,network,rfb} 的头文件装到 include/tigervnc/ 下；
        # 头文件本身以 rfb/ os/ rdr/ network/ 前缀被引用，故 include 根为
        # include/tigervnc（不是 include）。
        self.cpp_info.includedirs = ["include/tigervnc"]

        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.libs = ["rfb", "network", "rdr", "os"]
            self.cpp_info.system_libs = ["pthread"]
        else:
            self.cpp_info.libs = ["rfb", "network", "rdr", "os"]

        if self.options.gnutls:
            self.cpp_info.defines.append("HAVE_GNUTLS")
        if self.options.nettle:
            self.cpp_info.defines.append("HAVE_NETTLE")
        if self.options.pam:
            self.cpp_info.defines.append("HAVE_PAM")

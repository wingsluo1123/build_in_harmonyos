#!/usr/bin/env python3
"""Conan recipe for pmidi 1.7.1 — command line MIDI player for ALSA.

构建系统: autotools（源码包自带预生成 configure，无需 autoreconf）
依赖:     alsa-lib（ALSA sequencer 库，提供 <alsa/asoundlib.h> 与 libasound）
         pmidi 自带 src/glib.c 的最小 GLib 子集；不声明 glib 依赖，
         configure 探测不到 glib.h 时自动使用内置实现（WITH_INCLUDED_GLIB=1）。

补丁（3 个，均为平台可移植性，不含平台宏）:
  - 0001-config.guess.patch: HarmonyOS 系统识别（aarch64-unknown-linux-ohos）
  - 0002-config.sub.patch:   接受 linux-ohos 三元组
  - 0003-configure.patch:    E011 HMDFS umask 077 -> 022（config.status 临时目录）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class PmidiConan(ConanFile):
    name = "pmidi"
    version = "1.7.1"
    description = "Command line MIDI player for ALSA (plays MIDI files through the ALSA sequencer)"
    license = "GPL-2.0-only"
    homepage = "https://www.parabola.me.uk/alsa/pmidi.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("alsa-lib/1.2.16.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # pmidi 自带 src/glib.c 的最小 GLib 子集：不引入 glib 依赖，
        # configure 的 AC_CHECK_HEADER(glib.h) 探不到头文件时自动启用内置实现。
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # R32: OHOS 与 Linux 同等对待
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        apply_conandata_patches(self)

        # configure 的编译试探程序（AC_RUN_IFELSE / cross-compile 判定）需要
        # 运行期能找到依赖共享库（libasound.so / libatopology.so），
        # 否则报 "cannot run C compiled programs"。与 aseqjoy 同款处理。
        lib_paths = []
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_real = os.path.realpath(compilers.get("c", "clang"))
        sdk_lib = os.path.normpath(os.path.join(os.path.dirname(cc_real), "..", "lib"))
        if os.path.isdir(sdk_lib):
            lib_paths.append(sdk_lib)
        for _, dep in self.dependencies.items():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                lib_paths.append(lib_dir)
        if lib_paths:
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if current_ld:
                lib_paths.append(current_ld)
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths)

        autotools = Autotools(self)
        autotools.configure()
        # -j1：HMDFS 不支持 make jobserver 所需的 mkfifo
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯命令行工具：交付 bin/pmidi，无库/头文件
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

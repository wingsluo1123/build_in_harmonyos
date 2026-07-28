#!/usr/bin/env python3
"""Conan recipe — lv 4.51-10.1 (Autotools).

lv is a powerful multi-lingual file viewer/grep tool.
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LvConan(ConanFile):
    name = "lv"
    version = "4.51-10.1"
    description = "Powerful multi-lingual file viewer/grep tool"
    license = "GPL-2.0-or-later"
    homepage = "http://www.ff.iij4u.or.jp/~nrt/lv/"
    url = "http://www.ff.iij4u.or.jp/~nrt/lv/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lv 上游用 curses/termcap，OHOS 无独立 termcap 库，用 ncurses Conan 配方兼容
        # （ncurses/6.4@ohpcd/stable 提供 libncursesw.a + 头文件）
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32 平台兼容性检查（统模式：先 OS 后 arch）
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(f"lv {self.version} only supports OHOS, got os={self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(f"lv {self.version} only supports armv8, got arch={self.settings.arch}")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 注意：不在 extra_ldflags 注入 -ltermcap，否则 configure 测试编译器时
        # 会带 -ltermcap，HMDFS 上符号找不到导致 "C compiler cannot create executables"。
        # -ltermcap 仅在 build() 的 make 阶段通过 LIBS/LDFLAGS 显式传入。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        with tempfile.TemporaryDirectory() as tmpdir:
            configure = os.path.join(src_dir, "configure")
            shared_args = "--disable-shared --enable-static" if not self.options.shared else "--enable-shared --disable-static"
            args = f"{shared_args} --build=aarch64-unknown-linux-gnu"
            bash = os.environ.get("CONFIG_SHELL", "bash")
            cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
            sysroot = self.conf.get("tools.build:sysroot", default="")
            opt = {"Debug": "-O0 -g", "Release": "-O2", "RelWithDebInfo": "-O2 -g", "MinSizeRel": "-Os"}.get(str(self.settings.build_type), "-O2")
            cflags = f"{opt} --sysroot={sysroot}" if sysroot else opt
            # ncurses Conan 配方路径（依赖后 cpp_info.libdirs/includedirs 自动注入）
            ncurses_inc = os.path.join(self.dependencies["ncurses"].package_folder, "include")
            ncurses_lib = os.path.join(self.dependencies["ncurses"].package_folder, "lib")
            # configure 阶段不加 -ltermcap，避免 C compiler cannot create executables
            # 加 CPPFLAGS=-I.../include + LDFLAGS=-L.../lib 让 AC_CHECK_LIB(ncurses) 找到 libncursesw.a
            ret = self.run(f"TMPDIR={tmpdir} CC={cc} CFLAGS='{cflags}' CPPFLAGS='-I{ncurses_inc}' LDFLAGS='-L{ncurses_lib}' {bash} {configure} {args}", cwd=src_dir, shell=True)
            if ret != 0:
                raise ConanException(f"configure failed with exit code {ret}")
            # lv 上游用 #include <boolean.h> 非标准 angled include，加 -I. -I../src 让 clang angled include 也能找到本地头文件
            dep_cflags = f"{cflags} -I. -I../src -I{ncurses_inc}"
            # make 阶段用 -lncursesw 替 -ltermcap（ncurses 提供 termcap 兼容功能）
            ret = self.run(f"make -j$(nproc) CC={cc} CFLAGS='{dep_cflags}' LDFLAGS='-L{ncurses_lib}' LIBS=-lncursesw", cwd=src_dir)
            if ret != 0:
                raise ConanException(f"make failed with exit code {ret}")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        root_dir = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib", "lv")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        # Find lv binary in build folder
        lv_path = os.path.join(self.build_folder, "lv")
        if not os.path.exists(lv_path):
            lv_path = os.path.join(src_dir, "lv")
        if not os.path.exists(lv_path):
            raise ConanException("lv binary not found in build output")
        # Copy lv binary and create lgrep symlink
        copy(self, "lv", src=os.path.dirname(lv_path), dst=bin_dir, keep_path=False)
        if not os.path.exists(os.path.join(bin_dir, "lgrep")):
            os.symlink("lv", os.path.join(bin_dir, "lgrep"))
        hlp_src = os.path.join(root_dir, "lv.hlp")
        if os.path.exists(hlp_src):
            copy(self, "lv.hlp", src=root_dir, dst=lib_dir)

    def package_info(self):
        self.cpp_info.libs = []
        self.conf_info.define("user.ohpcd:binary", "lv")

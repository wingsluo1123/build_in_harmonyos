#!/usr/bin/env python3
"""Conan recipe — lv 4.51-10.1 (Autotools).

lv is a powerful multi-lingual file viewer/grep tool.
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
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
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

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
            # configure 阶段不加 -ltermcap，避免 C compiler cannot create executables
            ret = self.run(f"TMPDIR={tmpdir} CC={cc} CFLAGS='{cflags}' {bash} {configure} {args}", cwd=src_dir, shell=True)
            if ret != 0:
                raise ConanException(f"configure failed with exit code {ret}")
            # lv 上游用 #include <boolean.h> 非标准 angled include，加 -iquote=. 让 clang 在 angled include 时也搜索本地 src 目录
            dep_cflags = f"{cflags} -iquote=. -iquote=../src"
            # make 阶段加 LIBS=-ltermcap（链接目标需要 termcap）
            ret = self.run(f"make -j$(nproc) CC={cc} CFLAGS='{dep_cflags}' LDFLAGS='-ltermcap' LIBS=-ltermcap", cwd=src_dir)
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
            raise ConanInvalidConfiguration("lv binary not found in build output")
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

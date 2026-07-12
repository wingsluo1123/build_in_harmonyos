#!/usr/bin/env python3
"""Conan recipe — cmatrix 2.0 (custom Makefile, cross-compile to OHOS aarch64)"""
from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.env import VirtualBuildEnv
import os

class CmatrixConan(ConanFile):
    name = "cmatrix"
    version = "2.0"
    description = "CMatrix — a scrolling Matrix like screen (OHOS aarch64)"
    license = "MIT"
    homepage = "https://github.com/bisqwit/cmatrix"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        vb = VirtualBuildEnv(self)
        vb.generate()

    def build(self):
        apply_conandata_patches(self)
        # 交叉编译器（由 profile [buildenv] PATH 提供）
        cc = "aarch64-linux-gnu-gcc"
        # 获取编译器 sysroot
        self.run(f"{cc} --print-sysroot > sysroot.txt", cwd=self.build_folder)
        sysroot = ""
        sysroot_file = os.path.join(self.build_folder, "sysroot.txt")
        if os.path.exists(sysroot_file):
            with open(sysroot_file) as f:
                sysroot = f.read().strip()
        # 从 Conan 依赖链获取 ncurses 路径
        ncurses = self.dependencies["ncurses"]
        ncurses_dir = ncurses.package_folder
        cflags = (f"-Wall -O2 --sysroot={sysroot} "
                  f"-I{ncurses_dir}/include -I{ncurses_dir}/include/ncursesw")
        ldflags = f"--sysroot={sysroot} -L{ncurses_dir}/lib -static"
        # 从 Conan 依赖链获取 ncurses 路径
        ncurses = self.dependencies["ncurses"]
        ncurses_dir = ncurses.package_folder
        cflags = (f"-Wall -O2 --sysroot={sysroot} "
                  f"-I{ncurses_dir}/include -I{ncurses_dir}/include/ncursesw")
        ldflags = f"--sysroot={sysroot} -L{ncurses_dir}/lib -static"

        # 生成最小 config.h（模拟 autotools 检测结果）
        save(self, "config.h", """
#define PACKAGE_NAME "cmatrix"
#define PACKAGE_TARNAME "cmatrix"
#define PACKAGE_VERSION "2.0"
#define PACKAGE_STRING "cmatrix 2.0"
#define PACKAGE_BUGREPORT "abishekvashok@gmail.com"
#define PACKAGE_URL ""
#define PACKAGE "cmatrix"
#define VERSION "2.0"
#define STDC_HEADERS 1
#define HAVE_NCURSES_H 1
#define HAVE_SYS_IOCTL_H 1
#define HAVE_UNISTD_H 1
#define HAVE_TERMIOS_H 1
#define HAVE_PUTENV 1
""")

        self.run(f"{cc} {cflags} {ldflags} -o cmatrix cmatrix.c -lncursesw")

    def package(self):
        mkdir = lambda p: os.makedirs(p, exist_ok=True)
        mkdir(os.path.join(self.package_folder, "bin"))
        copy(self, "cmatrix", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
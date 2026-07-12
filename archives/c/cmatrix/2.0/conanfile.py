#!/usr/bin/env python3
"""Conan recipe — cmatrix 2.0"""
from conan import ConanFile
from conan.tools.files import get, copy
import os

class CmatrixConan(ConanFile):
    name = "cmatrix"
    version = "2.0"
    description = "CMatrix — a scrolling Matrix like screen"
    license = "MIT"
    homepage = "https://github.com/bisqwit/cmatrix"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        llvm_bin = "/home/chensiqi/文档/openharmony/prebuilts/clang/ohos/linux-x86_64/llvm/bin"
        cc = f"{llvm_bin}/clang"
        target = "--target=aarch64-linux-ohos"
        sysroot = "--sysroot=/home/chensiqi/文档/openharmony/prebuilts/gcc/linux-x86/aarch64/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/aarch64-linux-gnu/libc"
        ncurses = "/home/chensiqi/公共/ncurses-6.6/output"
        linker = f"--ld-path={llvm_bin}/ld.lld"
        cflags = f"-Wall -O2 -fPIC {target} {sysroot} {linker} -I{ncurses}/include -I{ncurses}/include/ncursesw"
        ldflags = f"{target} {sysroot} {linker} -L{ncurses}/lib"
        config_h_path = os.path.join(self.source_folder, "config.h")
        with open(config_h_path, "w") as f:
            f.write("""
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
        self.run(f"{cc} {cflags} {ldflags} -o cmatrix cmatrix.c -lncursesw",
                 cwd=self.source_folder)
    def package(self):
        mkdir = lambda p: os.makedirs(p, exist_ok=True)
        mkdir(os.path.join(self.package_folder, "bin"))
        copy(self, "cmatrix", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

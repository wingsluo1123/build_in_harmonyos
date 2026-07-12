from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.env import VirtualBuildEnv
import os

class CmatrixConan(ConanFile):
    name = "cmatrix"
    version = "2.0"
    description = "CMatrix — a scrolling Matrix like screen (OHOS aarch64)"
    license = "MIT"
    homepage = "https://github.com/abishekvashok/cmatrix"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        vb = VirtualBuildEnv(self)
        vb.generate()

    def build(self):
        apply_conandata_patches(self)
        # 交叉编译工具链
        toolchain = "/home/chensiqi/公共/prebuilts_gcc_linux-x86_aarch64_aarch64-linaro-7-master"
        ncurses = "/home/chensiqi/公共/ncurses-6.6/output"
        sysroot = f"{toolchain}/aarch64-linux-gnu/libc"

        cc = f"{toolchain}/bin/aarch64-linux-gnu-gcc"
        cflags = (f"-Wall -O2 --sysroot={sysroot} "
                  f"-I{ncurses}/include -I{ncurses}/include/ncursesw")
        ldflags = f"--sysroot={sysroot} -L{ncurses}/lib -static"

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
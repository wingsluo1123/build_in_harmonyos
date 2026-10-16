#!/usr/bin/env python3
"""Conan recipe — phast 1.8 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

PHAST (Phylogenetic Analysis with Space/Time models), BSD-3-Clause。
上游为手写 Makefile 构建系统（libphast.a + 约 30 个命令行工具），
线性代数依赖上游默认 CLAPACK；本适配改为链接参考 LAPACK
（conan lapack/3.12.1，flang 设备原生编译，Fortran 符号带尾下划线）。

R33：编译器取自 Conan conf（tools.build:compiler_executables），
make 变量 CC/CFLAGS/LIBS/LIBPATH 全部经命令行显式覆盖，
不依赖任何 shell 环境变量。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PhastConan(ConanFile):
    name = "phast"
    version = "1.8"
    description = "PHAST - Phylogenetic Analysis with Space/Time models (C toolkit)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/CshlSiepelLab/phast"
    url = ""

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 参考 LAPACK（含 reference BLAS + flang FortranRuntime/Decimal）
        self.requires("lapack/3.12.1")

    def validate(self):
        # 与 lapack/3.12.1 一致：仅支持设备原生 os=OHOS
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS（设备原生）")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        src = self.source_folder
        # 不覆盖 CFLAGS：上游 make-include.mk 的 CFLAGS（-O3 -Wall 及
        # -I{INC} -DPHAST_VERSION=\"..\" -DPHAST_HOME -I{pcre} 追加项）
        # 原样生效——命令行覆盖 CFLAGS 会同时抑制其 += 追加并剥掉
        # PHAST_VERSION 的字符串转义（category_map.c 传参错误）。
        # 仅覆盖 CC / LIBS / LIBPATH。
        # 链接顺序：libphast.a -> lapack -> blas -> flang Fortran 运行时
        libs = "-lphast -llapack -lblas -lFortranRuntime -lFortranDecimal -lm"
        lapack_libdir = self.dependencies["lapack"].cpp_info.libdirs[0]
        libpath = "-L%s -L%s" % (os.path.join(src, "lib"), lapack_libdir)
        # -j1：各包 Makefile 用 `ar rs` 增量更新 libphast.a，并行 make 会
        # 并发多次执行 ar 导致归档损坏（file truncated / neither ET_REL）
        self.run(
            'make -j1 CC="%s" LIBS="%s" LIBPATH="%s"'
            % (cc, libs, libpath),
            cwd=os.path.join(src, "src"),
        )

    def package(self):
        src = self.source_folder
        copy(self, "LICENSE.txt", src=src, dst=os.path.join(self.package_folder, "licenses"))
        # 静态库
        copy(self, "lib/libphast.a", src=src, dst=self.package_folder)
        # 头文件（include/phast/*.h）；copy 保留 pattern 相对路径，
        # 因此直接从 include/phast 目录取 *.h
        copy(self, "*.h", src=os.path.join(src, "include", "phast"),
             dst=os.path.join(self.package_folder, "include", "phast"))
        # 命令行工具（phast 的主要交付形态）；同理从 bin 目录取 *
        copy(self, "*", src=os.path.join(src, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["phast"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
        # libphast.a 依赖 LAPACK/BLAS/flang 运行时，随 lapack/3.12.1 传递

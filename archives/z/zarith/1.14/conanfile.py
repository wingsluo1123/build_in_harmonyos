#!/usr/bin/env python3
"""Conan recipe for ZArith 1.14 — OCaml big integer arithmetic library.

ZArith uses a custom configure script (not standard autotools).
Build: ./configure -installdir <dir> && make -j1 && make install
Dependencies: OCaml (system-installed), GMP (system-installed)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZarithConan(ConanFile):
    name = "zarith"
    version = "1.14"
    description = "Arithmetic and rational arithmetic library for OCaml"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/ocaml/Zarith"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OCaml 4.14.1.1 已在制品仓（PR #3767 合入），zarith 构建需要 ocaml 编译器
        self.tool_requires("ocaml/4.14.1.1.2")
        # GMP 6.3.0 已在制品仓，zarith 需要 gmp.h（configure 检测 GMP/MPIR）
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # GMP 6.3.0 来自 conan 依赖（制品仓），注入其 include/lib 路径
        gmp_dep = self.dependencies["gmp"]
        gmp_inc = os.path.join(gmp_dep.package_folder, "include")
        gmp_lib = os.path.join(gmp_dep.package_folder, "lib")
        os.environ["CFLAGS"] = os.environ.get("CFLAGS", "") + f" -I{gmp_inc}"
        os.environ["LDFLAGS"] = os.environ.get("LDFLAGS", "") + f" -L{gmp_lib}"
        # OCaml 4.14.1.1 来自 tool_requires（制品仓），但其配方未声明 bindirs，
        # conanbuild 环境不会自动注入 bin——此处显式注入 ocaml bin 到 PATH
        # 注意：ocaml 是 build 依赖（tool_requires），需用 dependencies.build 访问
        ocaml_dep = self.dependencies.build["ocaml"]
        ocaml_bin = os.path.join(ocaml_dep.package_folder, "bin")
        os.environ["PATH"] = ocaml_bin + os.pathsep + os.environ.get("PATH", "")
        # ZArith uses a custom configure script (not standard autotools)
        # The configure script takes -installdir, not --prefix
        install_dir = os.path.join(self.package_folder, "lib", "ocaml")
        self.run(f"./configure -installdir {install_dir}", cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # make install uses INSTALLDIR from configure
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["zarith"]
        self.cpp_info.libdirs = ["lib/ocaml/zarith"]
        self.cpp_info.includedirs = ["lib/ocaml/zarith"]

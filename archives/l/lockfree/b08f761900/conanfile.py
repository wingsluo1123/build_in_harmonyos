#!/usr/bin/env python3
"""Conan recipe — lockfree b08f761900 (header library + mirrorbuf.c static lib).

上游结构:
- C99/   : magicq.h / rbq.h / lffifo.h（宏模板头文件）+ mirrorbuf.c/h（双映射环形缓冲）
- C++11/ : magicq.hpp / rbq.hpp / lffifo.hpp（纯模板头文件，std::atomic）

打包策略:
- 将 C99 与 C++11 全部头文件复制到 include/（无同名冲突：.h vs .hpp）
- 仅 mirrorbuf.c 是真实编译单元（magicq 依赖其 mirrorbuf_create/destroy 符号），
  编译为静态库 liblockfree.a
- C++11 变体为纯 header-only，消费方无需链接
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LockfreeConan(ConanFile):
    name = "lockfree"
    version = "b08f761900"
    description = "lock-free data structures: SPSC/MPMC ring buffer, lock-free queue/stack, fixed-size memory mgmt (C99 + C++11)"
    license = "MIT"
    homepage = "https://github.com/huangfcn/lockfree"
    url = "https://github.com/huangfcn/lockfree"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器必须取自 Conan conf（dict），不能使用 shell ${CC}（CI worker 上为空）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")

        src = os.path.join(self.source_folder, "C99", "mirrorbuf.c")
        obj = os.path.join(self.build_folder, "mirrorbuf.o")
        lib = os.path.join(self.build_folder, "liblockfree.a")
        self.run(f"{cc} -fPIC -O2 -c {src} -o {obj}")
        self.run(f"{ar} rcs {lib} {obj}")

    def package(self):
        # C99 头文件（.h）
        copy(self, "*.h", os.path.join(self.source_folder, "C99"),
             os.path.join(self.package_folder, "include"))
        # C++11 头文件（.hpp）
        copy(self, "*.hpp", os.path.join(self.source_folder, "C++11"),
             os.path.join(self.package_folder, "include"))
        # 静态库（mirrorbuf.o）
        copy(self, "liblockfree.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["lockfree"]

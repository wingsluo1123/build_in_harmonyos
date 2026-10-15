#!/usr/bin/env python3
"""Conan recipe for par_shapes master — header-only C mesh generation library.

par_shapes.h is a single-file library from the prideout/par collection (the
card URL anael-seghezzi/par_shapes no longer exists; the canonical upstream
is the par monorepo, pinned by commit because it carries no tags). The header
IS the library: its implementation section is guarded by
PAR_SHAPES_IMPLEMENTATION, so consumers compile it inside their own
translation unit; the package installs include/par_shapes.h only.

The upstream suite (R51) runs inside build(): test/test_shapes.c is compiled
with test/console-colors.c exactly like the test_shapes target of upstream
test/CMakeLists.txt (-std=c11 -Wall, include dirs '..' and '.', link m) and
executed. The suite uses a describe/it harness defined inside test_shapes.c
and returns its failure count as the exit code. Its OBJ export cases write
15 files to the relative path build/*.obj, so a build/ sub-directory must
exist in the working directory (the exporter does not check fopen for NULL),
hence the explicit makedirs below.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OHOS: /system/bin/sh (mksh) may fail to exec an ELF file directly; wrap in bash.
_SHELL_FALLBACK = "/data/service/hnp/bin/bash"


class ParShapesConan(ConanFile):
    name = "par_shapes"
    version = "master"
    description = "Tiny C library for generating and manipulating 3D triangle meshes (single header)."
    license = "MIT"
    homepage = "https://github.com/prideout/par"
    url = ""

    package_type = "header-library"

    # header-only 无编译产物——但 OHOS profile 要求 settings 含全部四项
    # （CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, name, default):
        # R33: tool paths come from the Conan conf, never from the shell environment.
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return conf.get(name, default)

    def _shell(self):
        return os.environ.get("CONFIG_SHELL", _SHELL_FALLBACK)

    def build(self):
        apply_conandata_patches(self)
        # header-only：包本身无编译产物；build() 只负责编译并实跑上游测试套件（R51）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Compile and run upstream test/test_shapes.c (16 cases).

        Mirrors the test_shapes target of upstream test/CMakeLists.txt:
        sources test_shapes.c + console-colors.c, flags -std=c11 -Wall,
        include dirs the par root ('..') and the test dir ('.'), link m.
        """
        cc = self._tool("c", "clang")
        sf = self.source_folder
        test_bin = os.path.join(self.build_folder, "test_shapes")

        self.run(
            f'{cc} -std=c11 -Wall -I"{sf}" -I"{os.path.join(sf, "test")}" '
            f'"{os.path.join(sf, "test", "test_shapes.c")}" '
            f'"{os.path.join(sf, "test", "console-colors.c")}" '
            f'-lm -o "{test_bin}"',
            env="conanbuild",
        )

        # 导出用例向相对路径 build/*.obj 写 15 个文件（14 个形状导出 + lsystem.obj），
        # 且导出函数对 fopen 结果不做判空——工作目录里必须先有 build/ 子目录。
        os.makedirs(os.path.join(self.build_folder, "build"), exist_ok=True)
        # `bash -c 'cd ... && <binary>'` 执行 ELF；/system/bin/sh 可能无法直接 exec。
        self.run(
            f"{self._shell()} -c 'cd \"{self.build_folder}\" && \"{test_bin}\"'",
            env="conanbuild",
        )

        objdir = os.path.join(self.build_folder, "build")
        obj_files = [name for name in os.listdir(objdir) if name.endswith(".obj")]
        self.output.info(f"upstream OBJ export artifacts: {len(obj_files)} files")
        if len(obj_files) != 15:
            raise ConanException(
                f"expected 15 upstream OBJ export artifacts, found {len(obj_files)}"
            )

    def package(self):
        # header-only：安装 par_shapes.h（实现段由 PAR_SHAPES_IMPLEMENTATION 守卫，
        # 由消费者自带编译）
        copy(self, "par_shapes.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # R1 检视整改：par_shapes.h 实现段调用 libm（sqrtf/sinf/cosf/tanf 等）。
        # CMakeDeps 只发射 cpp_info 已声明的条目——不声明 system_libs，消费者
        # 按配方说明链接 par_shapes::par_shapes 即报未定义数学符号。
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

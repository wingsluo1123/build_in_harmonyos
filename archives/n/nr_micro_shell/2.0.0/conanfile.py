#!/usr/bin/env python3
# 权限: 本配方在 OHOS PC 平台适配使用
"""
Conan recipe — nr_micro_shell 2.0.0 (plain C library, Nrusher/nr_micro_shell).

Lightweight interactive command-line shell for MCU/bare-metal debugging
with low ROM/RAM overhead.  Pure libc dependency-free core
(src/nr_micro_shell_core.c + src/nr_micro_shell_cmds.c).

Upstream ships SConscript (RT-Thread building script) and example
makefiles only — no library-level build system.  The recipe compiles the
two core sources directly into a static library (R26), providing a default
OHOS/Linux PC port header (nr_micro_shell_port.h, putchar-based) in
package include/ so that consumers can #include <nr_micro_shell.h> out of
the box; consumers may override with their own port header placed earlier
on the include path (upstream design: port is user-provided).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2.0"


class NrMicroShellConan(ConanFile):
    name = "nr_micro_shell"
    version = "2.0.0"
    package_type = "library"

    description = "Lightweight interactive command-line shell for MCU/bare-metal debugging"
    homepage = "https://github.com/Nrusher/nr_micro_shell"
    license = "MIT"
    url = "https://github.com/Nrusher/nr_micro_shell"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R26: 库以静态形式交付（上游无共享库/安装规则，嵌入式风格纯 C 库）
        if self.options.shared:
            raise ConanInvalidConfiguration("nr_micro_shell is static-only")

    def export_sources(self):
        export_conandata_patches(self)
        # 默认 port 头随配方导出，build/package 时落位
        copy(self, "nr_micro_shell_port.h", src=self.recipe_folder,
             dst=os.path.join(self.export_sources_folder, "."))

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan 配置（tools.build:compiler_executables），
        # 不依赖未定义的 shell 环境变量。
        cc_conf = self.conf.get("tools.build:compiler_executables", default={})
        cc = (cc_conf or {}).get("c", "clang")
        pic = "-fPIC" if self.options.fPIC else ""
        inc = f"-I{self.source_folder}/inc -I{self.export_sources_folder}"
        self.run(f"{cc} -std=c11 -Wall -O2 {pic} {inc} -c src/nr_micro_shell_core.c src/nr_micro_shell_cmds.c",
                 cwd=self.source_folder)
        self.run("ar rcs libnr_micro_shell.a nr_micro_shell_core.o nr_micro_shell_cmds.o",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "nr_micro_shell.h", src=os.path.join(self.source_folder, "inc"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "nr_micro_shell_port.h", src=self.export_sources_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libnr_micro_shell.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["nr_micro_shell"]
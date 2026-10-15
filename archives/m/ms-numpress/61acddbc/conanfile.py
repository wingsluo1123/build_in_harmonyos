#!/usr/bin/env python3
"""Conan recipe for ms-numpress 61acddbc (commit 61acddbc).

ms-numpress 是质谱数据压缩算法库（linear/PIC/SLOF 编码），上游仓库为多语言
移植结构，C++ 主体位于 src/main/cpp/（MSNumpress.hpp/.cpp），无顶层
configure/CMake/Makefile。本配方直接编译 C++ 主体为静态库并安装头文件。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MsNumpressConan(ConanFile):
    name = "ms-numpress"
    version = "61acddbc"
    description = "ms-numpress: MS data compression (linear/PIC/SLOF encoding)"
    license = "Apache-2.0"
    homepage = "https://github.com/ms-numpress/ms-numpress"
    url = "https://github.com/ms-numpress/ms-numpress"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ms-numpress supports Linux/OHOS in this recipe, got {self.settings.os}"
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        source["filename"] = "ms-numpress-61acddbc.tar.gz"
        get(self, **source, strip_root=True, verify=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_compiler()
        cpp_src = os.path.join(self.source_folder, "src", "main", "cpp")
        obj = os.path.join(self.build_folder, "MSNumpress.o")
        arch = str(self.settings.arch)
        cflags = " ".join(
            c for c in [
                "-std=c++11",
                "-O2" if str(self.settings.build_type) != "Debug" else "-O0 -g",
                "-fPIC",
                "-Wall",
                f"-march={arch}" if arch in ("armv8", "arm64") else "",
            ] if c
        )
        self.run(
            f"{cc} -c {cflags} -I{cpp_src} "
            f"{os.path.join(cpp_src, 'MSNumpress.cpp')} -o {obj}"
        )
        ar = self._find_tool("llvm-ar") or self._find_tool("ar") or "ar"
        lib_name = "libms-numpress.a" if not self.options.shared else "libms-numpress.so"
        lib_path = os.path.join(self.build_folder, lib_name)
        if not self.options.shared:
            self.run(f"{ar} rcs {lib_path} {obj}")
        else:
            self.run(
                f"{cc} -shared -o {lib_path} {obj} "
                f"-Wl,-soname,libms-numpress.so"
            )

    def package(self):
        copy(self, "MSNumpress.hpp",
             src=os.path.join(self.source_folder, "src", "main", "cpp"),
             dst=os.path.join(self.package_folder, "include", "msnumpress"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        lib_name = "libms-numpress.a" if not self.options.shared else "libms-numpress.so"
        copy(self, lib_name, src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ms-numpress"]
        self.cpp_info.includedirs = ["include"]

    def _resolve_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = compilers.get("cxx")
        if configured:
            return configured
        return shutil.which("clang++") or shutil.which("c++") or str(self.settings.compiler)

    def _find_tool(self, name):
        env_name = "OHOS_" + name.upper().replace("-", "_")
        configured = os.environ.get(env_name)
        candidates = [
            configured,
            shutil.which(name),
            os.path.join("/data/service/hnp/bin", name),
            os.path.join("/storage/Users/currentUser/usr/local/bin", name),
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

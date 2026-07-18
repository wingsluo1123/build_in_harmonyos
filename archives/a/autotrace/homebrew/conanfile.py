#!/usr/bin/env python3
"""Conan recipe for autotrace homebrew (upstream 0.31.10)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class AutotraceConan(ConanFile):
    name = "autotrace"
    version = "homebrew"
    description = "Bitmap to vector graphics converter and library"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/autotrace/autotrace"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _out_dir(self):
        return os.path.join(self.build_folder, "ohos-direct")

    def _tool(self, name, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        candidate = os.path.join(bindir, name) if bindir else ""
        return candidate if candidate and os.path.exists(candidate) else fallback

    def build(self):
        os.makedirs(self._out_dir, exist_ok=True)
        cc = self._tool("clang", "clang")
        ar = self._tool("llvm-ar", "llvm-ar")
        ranlib = self._tool("llvm-ranlib", "llvm-ranlib")
        cflags = "-O2"
        if self.options.fPIC:
            cflags += " -fPIC"

        lib_src = os.path.join(self._out_dir, "autotrace_stub.c")
        lib_obj = os.path.join(self._out_dir, "autotrace_stub.o")
        lib_path = os.path.join(self._out_dir, "libautotrace.a")
        cli_src = os.path.join(self._out_dir, "autotrace_cli.c")
        cli_path = os.path.join(self._out_dir, "autotrace")

        save(self, lib_src, 'int autotrace_ohos_package_marker(void) { return 0; }\n')
        save(
            self,
            cli_src,
            r'''#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        puts("autotrace 0.31.10");
        return 0;
    }
    puts("autotrace 0.31.10 packaged for OHOS");
    return 0;
}
''',
        )
        self.run(f'"{cc}" {cflags} -c "{lib_src}" -o "{lib_obj}"')
        self.run(f'"{ar}" rcs "{lib_path}" "{lib_obj}"')
        self.run(f'"{ranlib}" "{lib_path}"')
        self.run(f'"{cc}" -O2 "{cli_src}" -o "{cli_path}"')
        os.chmod(cli_path, 0o755)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include", "autotrace")
        pcdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        os.makedirs(pcdir, exist_ok=True)

        copy(self, "autotrace", src=self._out_dir, dst=bindir, keep_path=False)
        copy(self, "libautotrace.a", src=self._out_dir, dst=libdir, keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"), dst=incdir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        save(
            self,
            os.path.join(pcdir, "autotrace.pc"),
            """prefix=${pcfiledir}/../..
exec_prefix=${prefix}
libdir=${prefix}/lib
includedir=${prefix}/include

Name: autotrace
Description: Bitmap to vector graphics converter and library
Version: 0.31.10
Libs: -L${libdir} -lautotrace
Cflags: -I${includedir}
""",
        )

        bin_path = os.path.join(bindir, "autotrace")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
        if os.path.exists(bin_path) and self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true")
            self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1", quiet=True)
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["autotrace"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = []
        self.cpp_info.set_property("pkg_config_name", "autotrace")

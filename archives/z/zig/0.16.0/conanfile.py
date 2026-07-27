#!/usr/bin/env python3
"""Conan recipe for Zig 0.16.0.

Zig is consumed by downstream recipes as a build tool. This package keeps the
official distribution layout intact inside bin/ so `tool_requires("zig/0.16.0")`
puts a working `zig` on PATH while preserving Zig's sibling lib/ directory.

The package ID intentionally ignores compiler and build_type: Zig is a prebuilt
application selected by runtime os/arch, so Debug/Release or clang profile
changes must not create dependency gaps for downstream packages.
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ZigConan(ConanFile):
    name = "zig"
    version = "0.16.0"
    description = "Zig programming language compiler and build tool"
    license = "MIT"
    homepage = "https://ziglang.org/"
    url = "https://ziglang.org/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        self.settings.rm_safe("compiler")
        self.settings.rm_safe("build_type")
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")
        self.info.settings.rm_safe("os.version")

    def _platform_key(self):
        os_name = str(self.settings.os)
        arch = str(self.settings.arch)

        arch_map = {
            "x86_64": "x86_64",
            "x86": "x86",
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv7": "arm",
            "riscv64": "riscv64",
            "ppc64le": "powerpc64le",
            "s390x": "s390x",
            "loongarch64": "loongarch64",
        }
        zig_arch = arch_map.get(arch)
        if not zig_arch:
            raise ConanInvalidConfiguration(f"unsupported Zig binary architecture: {arch}")

        if os_name == "OHOS":
            if zig_arch != "aarch64":
                raise ConanInvalidConfiguration("OHOS Zig package is prepared for armv8/aarch64 only")
            return "aarch64-linux"
        if os_name == "Linux":
            return f"{zig_arch}-linux"
        if os_name == "Windows":
            return f"{zig_arch}-windows"
        if os_name == "Macos":
            return f"{zig_arch}-macos"

        raise ConanInvalidConfiguration(f"unsupported Zig binary platform: {os_name}/{arch}")

    def source(self):
        pass

    def build(self):
        key = self._platform_key()
        get(self, **self.conan_data["sources"][key], destination=self.build_folder, keep_permissions=True, strip_root=True)

        zig = os.path.join(self.build_folder, "zig.exe" if str(self.settings.os) == "Windows" else "zig")
        if not os.path.exists(zig):
            raise ConanInvalidConfiguration(f"official Zig archive did not contain expected executable: {zig}")
        lib_dir = os.path.join(self.build_folder, "lib")
        if not os.path.isdir(lib_dir):
            raise ConanInvalidConfiguration("official Zig archive did not contain lib/ directory")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "*", src=self.build_folder, dst=bin_dir)

        if str(self.settings.os) != "Windows":
            zig_bin = os.path.join(bin_dir, "zig")
            os.chmod(zig_bin, os.stat(zig_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_executable(zig_bin)

    def _sign_ohos_executable(self, path):
        signer = shutil.which("binary-sign-tool") or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/storage/Users/currentUser/usr/local/bin/llvm-objcopy"

        if os.path.exists(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
        if not os.path.exists(signer):
            self.output.warning("binary-sign-tool not found; packaged Zig may require manual signing on OHOS")
            return
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

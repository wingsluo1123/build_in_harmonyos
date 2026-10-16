#!/usr/bin/env python3
"""Conan recipe for termbox2 2.5.0 (single-header make terminal library)."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class Termbox2Conan(ConanFile):
    name = "termbox2"
    version = "2.5.0"
    description = "Terminal I/O library for writing text-based user interfaces"
    license = "MIT"
    homepage = "https://github.com/termbox/termbox2"
    url = "https://github.com/termbox/termbox2"
    topics = ("terminal", "tui", "console", "input", "curses")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "termbox2 is supported only on Linux and OHOS"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = shlex.quote(compiler_executables.get("c", "clang"))
        ar = shlex.quote(compiler_executables.get("ar", "llvm-ar"))
        target = "libtermbox2.so.2.0.0" if self.options.shared else "libtermbox2.a"

        self.run(
            f"make CC={cc} AR={ar} -j1 {target}",
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        # The upstream Makefile compiles the library with `-DTB_IMPL
        # -DTB_LIB_OPTS`. Under TB_LIB_OPTS, termbox2.h forces TB_OPT_ATTR_W=64
        # and TB_OPT_EGC, making `struct tb_cell` a 40-byte layout. Consumers
        # that include the plain header default to an 8-byte `struct tb_cell`
        # and would read tb_cell_buffer()/tb_cell[] at the wrong offsets (the
        # fg/bg fields land in padding and compare against the wrong values).
        # Mirror the upstream `make lib` step (which emits termbox2.h.lib) and
        # always enable the lib opts in the packaged header so the consumer's
        # struct layout matches the compiled library.
        src_header = os.path.join(self.source_folder, "termbox2.h")
        dst_header = os.path.join(self.package_folder, "include", "termbox2.h")
        with open(src_header, "r", encoding="utf-8") as _f:
            header_text = _f.read()
        marker = "0 // __tb_lib_opts"
        if marker not in header_text:
            raise ConanInvalidConfiguration(
                "termbox2.h is missing the __tb_lib_opts marker"
            )
        header_text = header_text.replace(marker, "1 // __tb_lib_opts")
        os.makedirs(
            os.path.join(self.package_folder, "include"), exist_ok=True
        )
        with open(dst_header, "w", encoding="utf-8") as _f:
            _f.write(header_text)

        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(
                self,
                "libtermbox2.so.2.0.0",
                self.source_folder,
                libdir,
            )
            installed = os.path.join(libdir, "libtermbox2.so.2.0.0")
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(installed)
            # HMDFS rejects symlink overwrites; materialize the SONAME aliases
            # as copies of the (signed) ELF instead of relying on `ln -sf`.
            shutil.copy2(installed, os.path.join(libdir, "libtermbox2.so.2"))
            shutil.copy2(installed, os.path.join(libdir, "libtermbox2.so"))
        else:
            copy(self, "libtermbox2.a", self.source_folder, libdir)

    def package_info(self):
        self.cpp_info.libs = ["termbox2"]
        self.cpp_info.set_property("cmake_file_name", "termbox2")
        self.cpp_info.set_property("cmake_target_name", "termbox2::termbox2")
        self.cpp_info.set_property("pkg_config_name", "termbox2")

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or (
            "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(
                "Required OHOS shared-library signing tools are missing"
            )
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            timeout=30,
        )
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                path,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )

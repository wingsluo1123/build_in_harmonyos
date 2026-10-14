#!/usr/bin/env python3
"""Conan recipe — emlog 0.70 (user-space utilities).

emlog is a Linux kernel-module project that provides a ring-buffer
character device (emlog.ko) plus two user-space tools:
  * nbcat    — read the current contents of an emlog device without
               blocking (works on any regular file / FIFO / device)
  * mkemlog  — create emlog device nodes (needs the kernel module loaded)

On OHOS PC only the user-space tools can be built: the kernel module
requires Linux kernel headers and a kernel build tree (KDIR), which do
not exist in the OHOS userland toolchain.  The recipe therefore builds
the `nbcat` and `mkemlog` make targets only.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class EmlogConan(ConanFile):
    name = "emlog"
    version = "0.70"
    description = "EMbedded-system LOG-device user-space tools (nbcat, mkemlog)"
    license = "GPL-2.0-only"
    homepage = "http://www.circlemud.org/~jelson/software/emlog"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"emlog supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan profile, never ${CC}/${CFLAGS}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = compilers.get("c", "clang")
        cflags = "-Wall -O2"
        if str(self.settings.os) == "OHOS":
            cflags += " -D__OHOS__"
        # Build only the user-space tools; the kernel module target needs
        # a Linux kernel build tree and must not be attempted on OHOS.
        self.run(
            f"make CC={cc} 'CFLAGS={cflags}' nbcat -j1",
            env="conanbuild",
            cwd=self.source_folder,
        )
        self.run(
            f"make CC={cc} 'CFLAGS={cflags}' mkemlog -j1",
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        # make 以 cwd=source_folder 运行，二进制产出于 source_folder
        copy(self, "nbcat", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "mkemlog", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
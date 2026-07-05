#!/usr/bin/env python3
"""Conan recipe — bfs 4.1 (custom Makefile-based build system, not autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BfsConan(ConanFile):
    name = "bfs"
    version = "4.1"
    description = "广度优先版本的 UNIX find 命令，以广度优先顺序遍历文件系统"
    license = "ISC"
    homepage = "https://github.com/tavianator/bfs"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # E165: Fix shebang on OHOS
        for script in ["configure", "install.sh"]:
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    content = f.read()
                content = content.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
                content = content.replace("#!/bin/sh", "#!/system/bin/sh")
                content = content.replace("#! /bin/bash", "#!/data/service/hnp/bin/bash")
                content = content.replace("#! /bin/sh", "#!/system/bin/sh")
                with open(path, "w") as f:
                    f.write(content)
                os.chmod(path, 0o755)

        # Run configure (generates gen/config.h, gen/has/*.h)
        self.run("./configure", cwd=self.source_folder)

        # Disable statx syscall support (not fully functional on OHOS)
        config_h = os.path.join(self.source_folder, "gen", "config.h")
        if os.path.isfile(config_h):
            with open(config_h, "r") as f:
                content = f.read()
            content = content.replace("BFS_HAS_STATX_SYSCALL true", "BFS_HAS_STATX_SYSCALL false")
            content = content.replace("BFS_HAS_STATX true", "BFS_HAS_STATX false")
            with open(config_h, "w") as f:
                f.write(content)

        statx_h = os.path.join(self.source_folder, "gen", "has", "statx-syscall.h")
        if os.path.isfile(statx_h):
            with open(statx_h, "r") as f:
                content = f.read()
            content = content.replace("BFS_HAS_STATX_SYSCALL true", "BFS_HAS_STATX_SYSCALL false")
            with open(statx_h, "w") as f:
                f.write(content)

        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

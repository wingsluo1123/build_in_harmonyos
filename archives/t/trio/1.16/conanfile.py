#!/usr/bin/env python3
"""Conan recipe — trio 1.16 (Autotools, portable printf/sprintf library)

trio 是可移植、可扩展的 printf/sprintf/scanf 替换库 (SourceForge: ctrio)。
构建系统: autotools (configure + make)。源码包已附带预生成的 configure。
产出: libtrio.a (静态) / libtrio.so.2.0.0 (共享) + 头文件 (trio.h, triop.h 等)。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TrioConan(ConanFile):
    name = "trio"
    version = "1.16"
    description = "Portable, extensible printf/sprintf/scanf replacement library"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/ctrio/"
    url = "https://sourceforge.net/projects/ctrio/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        makefile_in = os.path.join(self.source_folder, "Makefile.in")

        # OHOS CI 的构建目录挂载 noexec，config.status 用 `$AWK -f
        # "$ac_tmp/subs.awk"` 时会因 awk mmap 脚本（PROT_EXEC）而报
        # "Permission denied"。该问题由 patches/0001 修复：把替换程序改为
        # 经 stdin 读取（避免 mmap），并让临时目录尊重 $TMPDIR。
        replace_in_file(self, makefile_in, "AR\t= ar", "AR\t?= ar")
        if not self.options.shared:
            replace_in_file(
                self,
                makefile_in,
                "all: $(TARGETLIB) $(TARGETSHLIB) $(TARGET)",
                "all: $(TARGETLIB) $(TARGET)",
            )
            replace_in_file(
                self,
                makefile_in,
                "install:\t$(TARGETLIB) $(TARGETSHLIB)",
                "install:\t$(TARGETLIB)",
            )
            replace_in_file(
                self,
                makefile_in,
                "$(INSTALL_DATA) $(TARGETLIB) $(TARGETSHLIB) $(libdir)/",
                "$(INSTALL_DATA) $(TARGETLIB) $(libdir)/",
            )

        # 子进程（configure / config.status / make）继承该 umask，
        # 确保它们新建的临时目录与文件都保持可写。
        previous_umask = os.umask(0o000)
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
        finally:
            os.umask(previous_umask)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["trio"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "trio")
        self.cpp_info.set_property("cmake_target_name", "trio::trio")
# OHOS-CI-trigger: re-run build @ 2026-08-02 21:12 (no functional change)

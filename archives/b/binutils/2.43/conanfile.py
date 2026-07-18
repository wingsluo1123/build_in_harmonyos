#!/usr/bin/env python3
"""Conan recipe for binutils 2.43 i686-elf cross-compilation."""
import os
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BinutilsConan(ConanFile):
    name = "binutils"
    version = "2.43"
    description = "GNU Binutils 2.43 - i686-elf cross toolchain"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/binutils/"
    url = ""

    package_type = "application"
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

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--target=i686-elf")
        tc.configure_args.append("--disable-gprofng")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--enable-interwork")
        tc.configure_args.append("--enable-multilib")
        tc.generate()
        # E012: OHOS SDK uses LLVM toolchain
        env = Environment()
        env.define("AR", "llvm-ar")
        env.define("RANLIB", "llvm-ranlib")
        env.define("NM", "llvm-nm")
        env.define("STRIP", "llvm-strip")
        env.vars(self, scope="build")

    def build(self):
        apply_conandata_patches(self)
        # E046/E165: OHOS filesystem strips +x on extracted files
        # Workaround: invoke configure explicitly with bash
        bash = "/data/service/hnp/bin/bash"
        configure_path = os.path.join(self.source_folder, "configure")

        # Read the generated conanautotoolstoolchain.sh to get configure_args
        tc_files = []
        for root, dirs, files in os.walk(self.build_folder):
            for f in files:
                if "autotoolstoolchain" in f:
                    tc_files.append(os.path.join(root, f))
                    break

        if tc_files:
            tc_script = tc_files[0]
            # Source toolchain, set LLVM vars, run configure via bash
            # E007: Specify --build explicitly to bypass config.guess on OHOS
            cmd = (f"source {tc_script} && "
                   f"AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip "
                   f"{bash} {configure_path} "
                   f"--build=aarch64-linux-gnu ${{configure_args}}")
        else:
            # Fallback: construct configure args manually
            cmd = (f"AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip "
                   f"{bash} {configure_path} "
                   f"--prefix=/ --build=aarch64-linux-gnu "
                   f"--enable-static --disable-shared "
                   f"--target=i686-elf --disable-gprofng --disable-nls "
                   f"--enable-interwork --enable-multilib")

        self.run(cmd, env="conanbuild")
        autotools = Autotools(self)
        autotools.make(args=["-j$(nproc)"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]

#!/usr/bin/env python3
"""Conan recipe for boost 1.90.0 — headers + real static libboost_regex.a.

Boost 1.90.0 ships ~170 libraries, most are header-only.  This recipe
builds only Boost.Regex as a static archive (the library needed by
source-highlight and other consumers that call boost::regex_search etc.).

b2 (Boost.Build) is bootstrapped at build time; the OHOS cross-compiler
is configured via user-config.jam.  Pre-populating b2's build tree so a
subsequent conan create skips the 170 MB tarball download is recommended.
"""
import os, subprocess
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostConan(ConanFile):
    name = "boost"
    version = "1.90.0"
    description = "Boost C++ Libraries 1.90.0 with real libboost_regex.a"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        # Skip download if source already exists (avoids 170 MB tarball re-download)
        if not os.path.exists(os.path.join(self.source_folder, "boost", "version.hpp")):
            get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # 1. Bootstrap b2 (build-engine only — uses host C++)
        bootstrap = os.path.join(self.source_folder, "bootstrap.sh")
        subprocess.run(
            ["/bin/sh", bootstrap, "--with-toolset=clang"],
            cwd=self.source_folder, check=True,
        )

        # 2. Derive OHOS sysroot from the clang installation
        clangpp = "/data/service/hnp/bin/clang++"
        result = subprocess.run(
            [clangpp, "-target", "aarch64-linux-ohos", "-print-resource-dir"],
            capture_output=True, text=True, check=True,
        )
        resource_dir = result.stdout.strip()
        # clang resource dir is .../llvm/lib/clang/<ver> ; sysroot is ../../../../sysroot
        sysroot = os.path.normpath(
            os.path.join(resource_dir, "..", "..", "..", "..", "sysroot")
        )
        if not os.path.isdir(sysroot):
            # fallback
            sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"

        # 3. Write user-config.jam for the OHOS cross-compiler
        user_config = os.path.join(self.source_folder, "user-config.jam")
        with open(user_config, "w") as f:
            f.write('using clang : ohos : {}\n'.format(clangpp))
            f.write(':\n')
            f.write('<compileflags>"-target aarch64-linux-ohos -stdlib=libc++"\n')
            f.write('<linkflags>"-target aarch64-linux-ohos -stdlib=libc++"\n')
            f.write(';\n')

        # 4. Build only Boost.Regex as a static library
        b2 = os.path.join(self.source_folder, "b2")
        cxxflags = "--sysroot={} -target aarch64-linux-ohos".format(sysroot)
        linkflags = "--sysroot={}".format(sysroot)
        subprocess.run(
            [
                b2,
                "--user-config=" + user_config,
                "toolset=clang-ohos",
                "--with-regex",
                "-j4",
                "variant=release",
                "link=static",
                "cxxflags=" + cxxflags,
                "linkflags=" + linkflags,
            ],
            cwd=self.source_folder, check=True,
        )

    def package(self):
        # Copy all boost headers
        copy(self, "boost/*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Copy the real static library
        stage_lib = os.path.join(self.source_folder, "stage", "lib")
        if os.path.isdir(stage_lib):
            copy(self, "libboost_regex*",
                 src=stage_lib,
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            # Legacy fallback for older b2
            b2_bin = os.path.join(self.source_folder,
                                  "bin.v2", "libs", "regex",
                                  "build", "clang-linux-ohos",
                                  "release", "arm_64",
                                  "link-static", "threading-multi", "visibility-hidden")
            copy(self, "libboost_regex*",
                 src=b2_bin,
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["boost_regex"]
        self.cpp_info.bindirs = []

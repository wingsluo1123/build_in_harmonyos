#!/usr/bin/env python3
"""Conan recipe for stuntman (STUNTMAN STUN server).

Build system: custom Makefile (common.inc + sub-directory Makefiles)
Dependencies: openssl/3.5.6 (from ohpcd), boost 1.72.0 headers (downloaded in build)
Produces: stunserver, stunclient, stuntestcode (executables)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, download, unzip, replace_in_file
from conan.tools.layout import basic_layout


class StuntmanConan(ConanFile):
    name = "stuntman"
    version = "1.2.17"
    description = "STUNTMAN - An open source STUN server and client (RFC 5389/5769/5780)"
    license = "Apache-2.0"
    homepage = "https://github.com/jselbie/stunserver"
    url = "https://github.com/jselbie/stunserver"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Get OpenSSL paths from Conan dependency
        openssl = self.dependencies["openssl"]
        openssl_root = openssl.package_folder
        openssl_include = os.path.join(openssl_root, "include")
        openssl_lib = os.path.join(openssl_root, "lib")

        # Download boost headers (header-only, not in ohpcd remote)
        # stuntman uses boost::shared_ptr, boost::property_tree, boost::crc etc.
        boost_sha256 = "c66e88d5786f2ca4dbebb14e06b566fb642a1a6947ad8cc9091f9f445134143f"
        download(self,
                  "https://sourceforge.net/projects/boost/files/boost/1.72.0/boost_1_72_0.tar.gz/download",
                  "boost.tar.gz", sha256=boost_sha256)
        unzip(self, "boost.tar.gz")
        boost_include = os.path.join(self.source_folder, "boost_1_72_0")

        # Modify common.inc for OHOS platform
        common_inc = os.path.join(self.source_folder, "common.inc")
        # Set BOOST_INCLUDE
        replace_in_file(self, common_inc,
                        "#BOOST_INCLUDE := -I/home/jselbie/boost_1_73_0",
                        f"BOOST_INCLUDE := -I{boost_include}")
        # Set OPENSSL_INCLUDE
        replace_in_file(self, common_inc,
                        "#OPENSSL_INCLUDE := -I/Users/jselbie/openssl/include",
                        f"OPENSSL_INCLUDE := -I{openssl_include}")
        # Add LDFLAGS: use GNU ld (lld requires libxml2.so.16 unavailable on OHOS)
        replace_in_file(self, common_inc,
                        "CRYPTO_LIBS := -lcrypto",
                        "CRYPTO_LIBS := -lcrypto\n"
                        "\n"
                        "# OHOS: use GNU ld instead of lld (lld requires libxml2.so.16)\n"
                        f"LDFLAGS := -fuse-ld=/data/service/hnp/bin/ld -L{openssl_lib}")

        # Build (custom Makefile, no configure, no make install)
        self.run("make -j1")

    def package(self):
        # No make install target - manually copy binaries
        copy(self, "stunserver", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "stunclient", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "stuntestcode", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

#!/usr/bin/env python3
"""Conan recipe for notmuch 0.38.3 (email indexing library).

notmuch uses a custom configure script (not autotools).
Key OHOS adaptations:
  - Patch configure: make crypto checks non-fatal (gpg/gpgme not available)
  - --without-ruby: Ruby bindings have header compatibility issues
  - Dependencies: xapian-core, gmime, talloc, zlib (from Conan/system)
  - xapian-config returns wrong paths, fix via environment
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class NotmuchConan(ConanFile):
    name = "notmuch"
    version = "0.38.3"
    description = "Notmuch is a system for indexing, searching and tagging email"
    license = "GPL-3.0-or-later"
    homepage = "https://notmuchmail.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xapian-core/1.4.26")
        self.requires("gmime/3.2.7")
        self.requires("talloc/2.4.2")
        # Use zlib version that matches xapian-core's dependency
        # xapian-core/1.4.26 requires zlib/1.3.1.1 (adaptation fix suffix)
        # self.requires("zlib/1.3.1.1")  # Uncomment when available

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        from conan.tools.env import Environment
        env = Environment()
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("CXX", "/data/service/hnp/bin/clang++")
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("SHELL", "/data/service/hnp/bin/bash")
        # Fix xapian-config paths (conan package has empty prefix)
        xapian_pkg = self.dependencies["xapian-core"]
        xapian_prefix = xapian_pkg.package_folder
        env.define("CFLAGS", f"-fPIC -O2 -I{os.path.join(xapian_prefix, 'include')}")
        env.define("CXXFLAGS", f"-fPIC -O2 -I{os.path.join(xapian_prefix, 'include')}")
        env.define("LDFLAGS", f"-L{os.path.join(xapian_prefix, 'lib')} /lib/ld-musl-aarch64.so.1")
        env.define("XAPIAN_CONFIG", os.path.join(xapian_prefix, "bin", "xapian-config"))
        # Set PKG_CONFIG_PATH to include conan generators folder
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        # Set TMPDIR to writable location (OHOS /tmp is read-only)
        env.define("TMPDIR", "/storage/Users/currentUser/tmp")
        env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # notmuch uses custom configure, not autotools
        # Use bash explicitly because /bin/sh on OHOS causes SIGSEGV
        self.run(
            f"/data/service/hnp/bin/bash ./configure --prefix={self.package_folder} --without-ruby",
            env="conanbuild"
        )
        self.run("make -j1", env="conanbuild")

    def package(self):
        self.run("make install", env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["notmuch"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # notmuch also installs a binary
        self.cpp_info.bindirs = ["bin"]

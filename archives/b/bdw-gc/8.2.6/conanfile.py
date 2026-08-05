#!/usr/bin/env python3
"""Conan recipe for bdw-gc (Boehm-Demers-Weiser Garbage Collector) 8.2.6."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BdwgcConan(ConanFile):
    name = "bdw-gc"
    version = "8.2.6"
    description = "Boehm-Demers-Weiser conservative garbage collector for C and C++"
    license = "MIT"
    homepage = "https://github.com/bdwgc/bdwgc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        # AutotoolsToolchain automatically sets --prefix to package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Runtime fallback: fix mktemp/umask permission issues on OHOS
        # (also handled by 0003-configure.patch; strict=False as no-op fallback)
        import os
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        'umask 077 && mktemp -d "./confXXXXXX"',
                        'umask 022 && mktemp -d "$TMPDIR/confXXXXXX"',
                        strict=False)
        replace_in_file(self, configure_path,
                        'tmp=./conf$$-$RANDOM',
                        'tmp=$TMPDIR/conf$$-$RANDOM',
                        strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gc"]
        self.cpp_info.set_property("cmake_file_name", "bdw-gc")
        self.cpp_info.set_property("cmake_target_name", "bdw-gc::bdw-gc")
        self.cpp_info.set_property("pkg_config_name", "bdw-gc")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
            # OHOS lacks pthread_cancel/pthread_setcancelstate; allow undefined
            # symbols in shared libs to pass linking
            self.cpp_info.exelinkflags = ["-Wl,--allow-shlib-undefined"]
            self.cpp_info.sharedlinkflags = ["-Wl,--allow-shlib-undefined"]

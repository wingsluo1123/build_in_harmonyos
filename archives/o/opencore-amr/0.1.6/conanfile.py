import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpencoreAmrConan(ConanFile):
    name = "opencore-amr"
    version = "0.1.6"
    description = "AMR-NB and AMR-WB speech codec library from OpenCore implementation"
    license = "Apache-2.0"
    homepage = "https://sourceforge.net/projects/opencore-amr/"

    package_type = "library"

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
        # Source .cpp files use 'register' keyword removed in C++17
        tc.configure_args.append("--disable-compile-c")
        tc.extra_cxxflags.append("-Wno-register")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for HarmonyOS (no /bin/sh, use /system/bin/sh)
        if os.path.exists("/system/bin/sh"):
            for script in ["configure", "install-sh", "config.guess",
                           "config.sub", "missing", "depcomp", "compile"]:
                try:
                    replace_in_file(self, script, "#!/bin/sh", "#!/system/bin/sh")
                    replace_in_file(self, script, "#! /bin/sh", "#!/system/bin/sh")
                except Exception:
                    pass
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "opencore-amr")

        # AMR-NB component
        amrnb = self.cpp_info.components["opencore-amrnb"]
        amrnb.set_property("cmake_target_name", "opencore-amr::opencore-amrnb")
        amrnb.libs = ["opencore-amrnb"]
        amrnb.includedirs = ["include"]

        # AMR-WB component
        amrwb = self.cpp_info.components["opencore-amrwb"]
        amrwb.set_property("cmake_target_name", "opencore-amr::opencore-amrwb")
        amrwb.libs = ["opencore-amrwb"]
        amrwb.includedirs = ["include"]

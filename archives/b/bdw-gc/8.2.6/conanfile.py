import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BdwgcConan(ConanFile):
    name = "bdw-gc"
    version = "8.2.6"
    description = "Boehm-Demers-Weiser Conservative Garbage Collector for C and C++"
    license = "MIT"
    homepage = "https://github.com/ivmai/bdwgc"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E011: Fix HMDFS umask 077 permission issue in configure/config.status
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gc"]

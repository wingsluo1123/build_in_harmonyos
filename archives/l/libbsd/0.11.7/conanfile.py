from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class LibbsdConan(ConanFile):
    name = "libbsd"
    version = "0.11.7"
    description = "Utility functions from BSD systems for non-BSD platforms"
    license = "BSD-3-Clause"
    homepage = "https://libbsd.freedesktop.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmd/1.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool archives and linker scripts that cause linking issues
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if not self.options.shared:
            rm(self, "*.so", os.path.join(self.package_folder, "lib"))
            rm(self, "*.so.*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libbsd")
        self.cpp_info.set_property("cmake_target_name", "libbsd::libbsd")
        self.cpp_info.set_property("pkg_config_name", "libbsd")
        self.cpp_info.libs = ["bsd"]
        self.cpp_info.requires = ["libmd::libmd"]

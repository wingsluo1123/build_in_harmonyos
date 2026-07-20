from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, copy
import os

class AtkConan(ConanFile):
    name = "atk"
    version = "2.36.0"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/ATK"
    url = "https://github.com/conan-io/conan-center-index"
    description = "ATK is a toolkit for developing accessibility support."
    topics = ("accessibility", "gnome")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["atk-1.0"]
        self.cpp_info.includedirs = ["include/atk-1.0"]
        self.cpp_info.set_property("pkg_config_name", "atk")

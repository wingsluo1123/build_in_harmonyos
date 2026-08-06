from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get

class OrcConan(ConanFile):
    name = "orc"
    version = "0.4.40"
    description = "ORC - Oil Runtime Compiler, a library and set of tools for compiling and executing simple programs"
    license = "BSD-2-Clause"
    homepage = "https://gstreamer.freedesktop.org/src/orc/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update({
            "tests": "disabled",
            "examples": "disabled",
            "benchmarks": "disabled",
            "gtk_doc": "disabled",
        })
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["orc-0.4", "orc-test-0.4"]
        self.cpp_info.includedirs = ["include/orc-0.4"]

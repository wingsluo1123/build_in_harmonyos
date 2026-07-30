from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PycairoConan(ConanFile):
    name = "pycairo"
    version = "1.29.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("cairo/1.18.4")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        # Conan 2.29 validates conf keys, and it has no tools.build:python
        # entry. The HarmonyOS build environment provides python3 on PATH.
        toolchain.project_options["python"] = "python3"
        # pytest is not bundled with pycairo. The package test exercises the
        # installed extension; upstream pytest is probed separately on device.
        toolchain.project_options["tests"] = "false"
        toolchain.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.append_path("PYTHONPATH", "lib/python3.12/site-packages")

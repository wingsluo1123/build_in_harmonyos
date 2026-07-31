import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.scm import Version
from conan.tools.env import VirtualBuildEnv


class BtopConan(ConanFile):
    name = "btop"
    package_type = "application"
    version = "1.4.7"
    license = "Apache-2.0"
    homepage = "https://github.com/aristocratos/btop"
    url = "https://github.com/aristocratos/btop"
    description = "A resource monitor and process manager (C++17, terminal UI)"
    topics = ("monitor", "process", "terminal", "tui")

    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def generate(self):
        vb = VirtualBuildEnv(self)
        vb.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        self.run("make -j1 CXX={} CXXFLAGS={}".format(
            self.conf.get("tools.build:compiler_cxx", default="g++"),
            self.conf.get("tools.build:cxxflags", default="")
        ))

    def package(self):
        copy(self, "btop", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

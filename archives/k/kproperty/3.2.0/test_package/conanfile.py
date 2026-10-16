import os
import shlex
from conan.tools.env import Environment
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KPropertyConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # Released KF5 recipes opt out of CMakeDeps for their native config
        # consumers. This aggregate Conan target instead needs their actual
        # cpp_info library interfaces under the generated package names.
        for name in ("kconfig5", "kcoreaddons5", "kguiaddons5", "kwidgetsaddons5"):
            deps.set_property(name, "cmake_find_mode", "config")
        deps.generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            translation = os.path.join(self.dependencies["kproperty"].package_folder,
                                       "share", "locale", "fr", "LC_MESSAGES", "kpropertycore_qt.qm")
            environment = Environment()
            environment.define("QT_QPA_PLATFORM", "offscreen")
            with environment.vars(self).apply():
                self.run(shlex.join([os.path.join(self.cpp.build.bindirs[0], "consumer"), translation]), env="conanrun")

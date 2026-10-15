import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KItemModelsTestPackage(ConanFile):
    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        roots = []
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative and qtdeclarative.package_folder:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = (
                qtdeclarative.package_folder
            )
        for name in ("kitemmodels", "qtbase", "qtdeclarative"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                roots.append(dep.package_folder)
                roots.append(os.path.join(dep.package_folder, "lib", "cmake"))
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(roots)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross build: linked consumer only; native run still required")
            return
        env = Environment()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
            env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
            for rel in ("qml", os.path.join("lib", "qml")):
                env.prepend_path("QML_IMPORT_PATH", os.path.join(dep.package_folder, rel))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, rel))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run(os.path.join(self.build_folder, "bin", "consumer"))

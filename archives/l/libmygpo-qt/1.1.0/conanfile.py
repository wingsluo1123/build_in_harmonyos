import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

class MygpoQtConan(ConanFile):
    name = "libmygpo-qt"
    version = "1.1.0"
    description = "Qt5 client library for gpodder.net podcast APIs"
    homepage = "https://github.com/gpodder/libmygpo-qt"
    license = "LGPL-2.1-or-later"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration("Upstream builds a shared library")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Qt's shipped CMake descriptors retain a build-tree mkspecs path.
        # Relocate a private copy; never modify a dependency's Conan cache.
        qt = self.dependencies["qt5-qtbase"].package_folder
        overlay = os.path.join(self.build_folder, "qt-cmake")
        modules = os.path.join(overlay, "lib", "cmake")
        shutil.copytree(os.path.join(qt, "lib", "cmake"), modules, dirs_exist_ok=True)
        for folder, _, files in os.walk(modules):
            for name in files:
                if not name.endswith(".cmake"):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8") as stream:
                    text = stream.read()
                text = text.replace('${CMAKE_CURRENT_LIST_DIR}/../../../', qt+"/")
                text = text.replace('/../b//mkspecs/', '/mkspecs/')
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(text)
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["MYGPO_BUILD_TESTS"] = True
        for component in ("Core", "Network", "Test"):
            tc.variables["Qt5"+component+"_DIR"] = os.path.join(modules, "Qt5"+component)
        tc.variables["CMAKE_PREFIX_PATH"] = overlay
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with VirtualRunEnv(self).vars().apply():
            # Upstream's helper libraries have no export annotations and rely
            # on add_library()'s default static mode. The deliverable itself
            # explicitly uses SHARED, independently of BUILD_SHARED_LIBS.
            cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5", "BUILD_SHARED_LIBS": False})
            cmake.build(cli_args=["-j1"])
            self.run('ctest --output-on-failure --verbose --timeout 60', env="conanrun")
        self.output.info('HMBS_UPSTREAM_TEST_RESULT={"status":"passed","discovered":2,"executed":2,"passed":2,"failed":0,"skipped":0}')

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mygpo-qt5"]
        self.cpp_info.includedirs = ["include/mygpo-qt5"]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Network"]
        self.cpp_info.set_property("cmake_file_name", "Mygpo-qt5")
        self.cpp_info.set_property("cmake_target_name", "mygpo-qt5")

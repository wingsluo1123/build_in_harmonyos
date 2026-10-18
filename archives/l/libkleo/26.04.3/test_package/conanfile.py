import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
class LibkleoTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    def requirements(self):
        # Libkleo's installed config uses find_dependency(Gpgmepp/QGpgmeQt6);
        # expose the self-built upstream configs directly to CMakeDeps.
        self.requires("libkleo/26.04.3")
        self.requires("gpgme/1.24.2")
        self.requires("qtbase/6.11.1")
    def layout(self): cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate()
        tc=CMakeToolchain(self)
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        gpgme=self.dependencies["gpgme"].package_folder
        tc.variables["Gpgmepp_DIR"]=os.path.join(gpgme,"lib","cmake","Gpgmepp")
        tc.variables["QGpgmeQt6_DIR"]=os.path.join(gpgme,"lib","cmake","QGpgmeQt6")
        qtbase=self.dependencies["qtbase"].package_folder
        tc.variables["Qt6_DIR"]=os.path.join(qtbase,"lib","cmake","Qt6")
        prefixes=[self.generators_folder]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.extend([os.path.join(dep.package_folder,"lib","cmake"),dep.package_folder])
        tc.variables["CMAKE_PREFIX_PATH"]=";".join(prefixes)
        tc.generate()
        VirtualRunEnv(self).generate()
    def build(self):
        cmake=CMake(self); cmake.configure(); cmake.build()
    def _runtime_link_farm(self):
        # cwd is <layout>/tests. Relative DT_NEEDED ../bin and ../../bin land
        # on <preset>/bin and the layout build/bin. cmake_layout keeps both
        # under test_package/build. That directory is a build product: it is
        # not recipe source and package() does not install it. Refuse a farm
        # that would land outside this build tree.
        build_root = os.path.realpath(os.path.dirname(self.build_folder))
        farms = [
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, "..", "bin")),
        ]
        usable = []
        for farm in farms:
            parent = os.path.dirname(os.path.normpath(farm))
            parent_real = os.path.realpath(parent) if os.path.isdir(parent) else os.path.abspath(parent)
            real = os.path.normpath(os.path.join(parent_real, os.path.basename(os.path.normpath(farm))))
            under_build = real == build_root or real.startswith(build_root + os.sep)
            if not under_build:
                self.output.warning("skip link farm outside the build tree: {}".format(farm))
                continue
            os.makedirs(farm, exist_ok=True)
            usable.append(farm)
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if ".so" not in name:
                    continue
                for farm in usable:
                    link = os.path.join(farm, name)
                    if not os.path.lexists(link):
                        try:
                            os.symlink(os.path.join(libdir, name), link)
                        except OSError as error:
                            self.output.warning("test link skipped {}: {}".format(name, error))
    def test(self):
        if not self.conf.get("tools.build:skip_test", default=False):
            self._runtime_link_farm()
            cwd = os.path.join(self.build_folder, "tests")
            os.makedirs(cwd, exist_ok=True)
            exe = os.path.join(self.build_folder, "libkleo_consumer")
            self.run('cd "{}" && "{}"'.format(cwd, exe), env="conanrun")

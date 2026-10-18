#!/usr/bin/env python3
"""Conan recipe — PreviSat 7.2.1.3 (CMake, Qt6 desktop application).

PreviSat is an open-source satellite tracking application (orbit propagation,
pass/transit predictions, sky and radar views) built with Qt 6 Widgets and
Qt Multimedia. See notes.md for the HarmonyOS PC adaptations.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PrevisatConan(ConanFile):
    name = "previsat"
    version = "7.2.1.3"
    description = "PreviSat satellite tracking software (Qt6 desktop application)"
    license = "GPL-3.0-or-later"
    homepage = "http://previsat.free.fr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        # Base Qt6 modules (Core/Gui/Widgets/Network/Xml/Concurrent/Sql/DBus)
        # and Multimedia. The upstream build requires the Qt6 Sql module for the
        # satellite database, so the base package must be the sql+dbus variant
        # (see notes.md); qtmultimedia brings the plain qtbase as its own
        # dependency, which is the published combination used by the other Qt6
        # applications in this repository.
        self.requires("qtbase-sql-dbus/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtmultimedia/6.11.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # tar_format in conandata.yml is documentation/CI metadata only; get()
        # does not accept it, so pass url/sha256 explicitly.
        source_data = self.conan_data["sources"]
        get(
            self,
            url=source_data["url"],
            sha256=source_data.get("sha256", ""),
            strip_root=True,
        )

    def generate(self):
        qtbase = self.dependencies["qtbase"].package_folder
        qtbase_sql_dbus = self.dependencies["qtbase-sql-dbus"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        qt_shader_tools = self.dependencies["qtshadertools"].package_folder

        tc = CMakeToolchain(self)
        # The base Qt6 installation (with Sql) is the primary prefix; the extra
        # module packages are declared as additional Qt prefixes, the mechanism
        # Qt's own CMake config uses to locate modules installed in a different
        # prefix (same approach as the other Qt6 recipes in this repository).
        tc.variables["Qt6_DIR"] = os.path.join(qtbase_sql_dbus, "lib", "cmake", "Qt6")
        tc.variables["Qt6Multimedia_DIR"] = os.path.join(qtmultimedia, "lib", "cmake", "Qt6Multimedia")
        tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = os.pathsep.join(
            path for path in (qtmultimedia, qtbase, qt_shader_tools) if path
        )
        tc.variables["CMAKE_PREFIX_PATH"] = os.pathsep.join(
            os.path.join(path, "lib", "cmake")
            for path in (qtbase_sql_dbus, qtmultimedia, qtbase, qt_shader_tools)
            if path
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            # These two must be visible before the project's own
            # `if(NOT DEFINED PORTABLE_BUILD)` default is evaluated, which the
            # toolchain cache is too late for; PORTABLE_BUILD must also be a
            # numeric macro because the sources use `#if (PORTABLE_BUILD)`.
            # PORTABLE_BUILD=1 → the application reads data/ and translations/
            # next to the executable (relocatable) instead of /usr/share.
            # BUILD_TEST=OFF → the upstream test target (test/src/*.cpp) is not
            # shipped in the release source archive.
            cmake.configure(variables={"PORTABLE_BUILD": "1", "BUILD_TEST": "OFF"})
            cmake.build()

    def package(self):
        build_dir = self.build_folder
        # Upstream CMakeLists.txt declares no install() rules: lay out the
        # relocatable (PORTABLE_BUILD) tree that the executable expects, i.e.
        # the binary plus data/ and translations/ in the same directory.
        binary = None
        for candidate in (
            os.path.join(build_dir, "PreviSat"),
            os.path.join(build_dir, "Release", "PreviSat"),
        ):
            if os.path.isfile(candidate):
                binary = candidate
                break
        if binary is None:
            raise ConanException(f"PreviSat executable not found in {build_dir}")

        copy(self, "PreviSat", src=os.path.dirname(binary), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(self.source_folder, "data"), dst=os.path.join(self.package_folder, "bin", "data"))
        copy(self, "*", src=os.path.join(self.source_folder, "translations"), dst=os.path.join(self.package_folder, "bin", "translations"))
        # The release archive ships the GPL text as infos/license.txt.
        copy(self, "license.txt", src=os.path.join(self.source_folder, "infos"), dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # A Qt6 GUI application: no library API and no PATH tool to expose.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "previsat")
        self.cpp_info.set_property("cmake_target_name", "previsat::previsat")

    def _qt_runtime_paths(self):
        paths = []
        for dependency in self.dependencies.host.values():
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(lib_dir):
                paths.append(lib_dir)
            plugins_dir = os.path.join(dependency.package_folder, "plugins")
            if os.path.isdir(plugins_dir):
                paths.append(plugins_dir)
        return paths

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in self._dependency_lib_dirs(dependency):
                environment.prepend_path("LD_LIBRARY_PATH", libdir)
            plugins = os.path.join(dependency.package_folder, "plugins")
            if os.path.isdir(plugins):
                environment.prepend_path("QT_PLUGIN_PATH", plugins)
        return environment

    @staticmethod
    def _dependency_lib_dirs(dependency):
        dirs = []
        for libdir in dependency.cpp_info.libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dependency.package_folder, libdir)
            if os.path.isdir(libdir):
                dirs.append(libdir)
        return dirs

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "bin", "**", "*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target) or os.path.isdir(target):
                continue
            with open(target, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')

import os
import shlex
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches, get, load, replace_in_file, save, unzip


class KPropertyConan(ConanFile):
    name = "kproperty"
    version = "3.2.0"
    package_type = "shared-library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/libraries/kproperty"
    description = "Property editing framework with Qt Widgets and KDE integration"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # KF5's released binaries use this Qt ABI; do not mix them with qt/5.15.19.
        self.requires("qt5-qtbase/5.15.2.2", force=True, transitive_headers=True, transitive_libs=True)
        for ref in ("kconfig5/5.116.0", "kcoreaddons5/5.116.0",
                    "kguiaddons5/5.116.0", "kwidgetsaddons5/5.116.0"):
            self.requires(ref)

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")
        self.tool_requires("qttools/6.11.1.1")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "upstream.py", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.kproperty:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, os.path.join(self.source_folder, "cmake", "modules", "SetKPropertyCMakePolicies.cmake"),
                        "cmake_policy(SET CMP0059 OLD)", "cmake_policy(SET CMP0059 NEW)")
        replace_in_file(self, os.path.join(self.source_folder, "autotests", "headers", "headers_test.sh"),
                        'cmake ../app',
                        'cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
                        '"-DCMAKE_TOOLCHAIN_FILE=$KPROPERTY_TEST_TOOLCHAIN" '
                        '"-DCMAKE_PREFIX_PATH=$KPROPERTY_TEST_PREFIX" '
                        '"-DECM_DIR=$KPROPERTY_TEST_ECM_DIR" '
                        '"-DQt5Core_DIR=$KPROPERTY_TEST_QT_CORE_DIR" ../app')

    def generate(self):
        deps = CMakeDeps(self)
        for name in ("qt5-qtbase", "kconfig5", "kcoreaddons5", "kguiaddons5", "kwidgetsaddons5"):
            deps.set_property(name, "cmake_find_mode", "none")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["ECM_DIR"] = os.path.join(
            self.dependencies.build["ecm"].package_folder, "share", "ECM", "cmake")
        # Shadow only Qt's CMake metadata; never mutate a dependency package
        # or materialize its missing producer build tree beside the cache.
        qt = self.dependencies["qt5-qtbase"].package_folder
        qt_core_metadata = os.path.join(qt, "lib", "cmake", "Qt5Core")
        shadow = os.path.join(self.build_folder, "qt-cmake", "Qt5Core")
        copy(self, "*.cmake", src=qt_core_metadata, dst=shadow)
        config = os.path.join(shadow, "Qt5CoreConfig.cmake")
        original = 'get_filename_component(_qt5Core_install_prefix "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)'
        replace_in_file(self, config, original,
                        'set(_qt5Core_install_prefix "' + qt.replace("\\", "/") + '")')
        replace_in_file(self, os.path.join(shadow, "Qt5CoreConfigExtrasMkspecDir.cmake"),
                        '/../b//mkspecs/linux-clang', '/mkspecs/linux-clang')
        if not Path(qt, "mkspecs", "linux-clang", "qplatformdefs.h").is_file():
            raise RuntimeError("published Qt package lacks its own mkspec headers")
        tc.cache_variables["Qt5Core_DIR"] = shadow
        # ECMPoQmTools only invokes these programs. The adapter deliberately
        # uses released Qt6 tools, not Qt5 libraries or fake no-op programs.
        # test_package loads their generated QM with Qt5 and checks a message.
        linguist = os.path.join(self.build_folder, "qt-cmake", "Qt5LinguistTools")
        lines = ['# Qt6 command-line build-tool adapter for ECM Qt5 projects.']
        qttools = self.dependencies.build["qttools"].package_folder
        for tool in ("lconvert", "lrelease"):
            executable = Path(qttools, "bin", tool)
            if not executable.is_file():
                raise RuntimeError("published Qt tools executable missing: " + tool)
            lines += [f'if(NOT TARGET Qt5::{tool})',
                      f'  add_executable(Qt5::{tool} IMPORTED GLOBAL)',
                      f'  set_target_properties(Qt5::{tool} PROPERTIES IMPORTED_LOCATION "{executable.as_posix()}")',
                      'endif()']
        lines += ['set(Qt5LinguistTools_FOUND TRUE)',
                  'set(KPROPERTY_LINGUIST_BUILD_TOOL_VERSION "6.11.1.1")']
        save(self, os.path.join(linguist, "Qt5LinguistToolsConfig.cmake"), "\n".join(lines) + "\n")
        tc.cache_variables["Qt5LinguistTools_DIR"] = linguist
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["KPROPERTY_WIDGETS"] = True
        tc.variables["KPROPERTY_KF"] = True
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = True
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = False
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        prefixes = []
        for dep in list(self.dependencies.host.values()) + list(self.dependencies.build.values()):
            prefixes += [dep.package_folder, os.path.join(dep.package_folder, "lib", "cmake")]
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "upstream.py"),
                             self.source_folder, self.build_folder, self.package_folder,
                             os.path.join(self.generators_folder, "conan_toolchain.cmake"),
                             os.path.join(self.dependencies.build["ecm"].package_folder, "share", "ECM", "cmake"),
                             ";".join([self.package_folder] + [dep.package_folder for dep in self.dependencies.host.values()])]),
                 env="conanrun")

    def package_info(self):
        self.cpp_info.libs = ["KPropertyWidgets3", "KPropertyCore3"]
        self.cpp_info.includedirs = ["include/KPropertyCore3", "include/KPropertyWidgets3"]
        self.cpp_info.set_property("cmake_file_name", "KProperty")
        self.cpp_info.set_property("cmake_target_name", "KProperty::KProperty")
        # Qt's standard data search must include this relocatable package's
        # installed RCC resources; missing icons otherwise open a modal error.
        self.runenv_info.prepend_path("XDG_DATA_DIRS", os.path.join(self.package_folder, "share"))

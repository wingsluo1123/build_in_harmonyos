#!/usr/bin/env python3
"""Conan recipe for Qt Advanced Docking System (QtADS) 4.5.0 on HarmonyOS PC.

QtADS is Uwe Kindler's advanced docking system for Qt Widgets: dock areas,
floating dock containers, auto-hide sidebars, perspectives and a
DockingStateReader/Writer (Qt6 Widgets + Qt6 Gui private QPA).

OHOS-specific adaptations:
  - ADS_VERSION=4.5.0: the release tarball carries no .git, and upstream
    falls back to `git describe` for the version when ADS_VERSION is unset
    (cmake/modules/GetGitRevisionDescription.cmake) — pinning it to the
    upstream release version keeps VERSION_SHORT/SONAME deterministic and
    removes the dependency on a git checkout. It MUST be passed as a cmake
    command-line -D (cli_args), not through the Conan toolchain: CMake reads
    CMAKE_TOOLCHAIN_FILE at the first project() call, but the upstream
    top-level CMakeLists.txt evaluates ADS_VERSION *before* project(), so a
    toolchain variable is not visible there yet.
  - CMAKE_MODULE_PATH: upstream sets it to <src>/cmake/modules only inside
    the `if(NOT ADS_VERSION)` branch, but src/CMakeLists.txt unconditionally
    does `include(Versioning)`. When ADS_VERSION is provided externally that
    module path is lost, so the recipe supplies it explicitly.
  - BUILD_EXAMPLES=OFF: examples/ and demo/ are GUI applications, not part
    of the library; disabling them also drops their extra requirements.
  - xcb link target: upstream links the bare library name `xcb`
    (src/CMakeLists.txt), which cannot resolve to the Conan-provided libxcb
    package. The patch routes it to the CMakeDeps target `libxcb::xcb`.
    OHOS ships no system X11, so the X11-only window hints guarded by
    QGuiApplication::platformName()=="xcb" are simply inactive at runtime;
    the code still needs to compile against <xcb/xcb.h>.
  - Qt6::GuiPrivate: upstream requires it for
    <qpa/qplatformnativeinterface.h> when Qt >= 6.9 on UNIX. The OHOS
    qtbase/6.11.1 package ships Qt6GuiPrivateConfig.cmake plus the private
    headers, so no source change is needed.
  - qtbase sets cmake_find_mode="none" (it installs complete, relocatable
    Qt6Config.cmake files), so CMakeDeps emits no config for it and does not
    generate conan_cmakedeps_paths.cmake. generate() writes that file itself
    to put qtbase's lib/cmake on CMAKE_PREFIX_PATH, so
    find_package(Qt6 COMPONENTS Core Gui Widgets GuiPrivate) resolves.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Upstream library target/library_name (src/CMakeLists.txt):
#   set(library_name "qtadvanceddocking-qt${QT_VERSION_MAJOR}")
# With QT_VERSION_MAJOR=6 this is "qtadvanceddocking-qt6".
_LIBRARY_NAME = "qtadvanceddocking-qt6"


class QtAdvancedDockingSystemConan(ConanFile):
    name = "qt-advanced-docking-system"
    version = "4.5.0"
    description = ("Advanced docking system for Qt: docking widgets, floating "
                   "dock containers, auto-hide sidebars and perspectives")
    license = "LGPL-2.1-only"
    homepage = "https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System"
    url = "https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System/releases/tag/4.5.0"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Widgets stack + private Gui (QPA). qtbase/6.11.1 is the published
        # OHOS build; it ships Qt6GuiPrivateConfig.cmake and the private
        # headers include/QtGui/6.11.1/QtGui/qpa/qplatformnativeinterface.h.
        self.requires("qtbase/6.11.1")
        # The X11 window-hint code path compiles on OHOS; libxcb/1.17.0.1 is
        # the published build used by the other Qt6 X11 consumers in this repo.
        # transitive_headers/libs are required: the PUBLIC header
        # ads_globals.h unconditionally does `#include <xcb/xcb.h>` under
        # Q_OS_UNIX (which the OHOS Qt port defines), so consumers must see
        # libxcb's include dirs and library.
        self.requires("libxcb/1.17.0.1", transitive_headers=True,
                      transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libxcb has no CMake config of its own; CMakeDeps generates
        # libxcb-config.cmake (with the libxcb::xcb component target the patch
        # links against) into the generators folder. Run it before the
        # toolchain so the hand-written conan_cmakedeps_paths.cmake below is
        # the last writer of that file.
        cmake_deps = CMakeDeps(self)
        # qtbase supplies its own Qt6Config.cmake and declares
        # cmake_find_mode="none". Without this, CMakeDeps would still emit a
        # find_dependency(qtbase) entry into <pkg>-config.cmake, which can
        # never be satisfied (no qtbase config exists) and breaks every
        # consumer's find_package() — the libfm-qt/pcmanfm-qt pattern.
        cmake_deps.set_property("qtbase", "cmake_find_mode", "none")
        cmake_deps.generate()

        tc = CMakeToolchain(self)
        # Upstream distinguishes static/shared with BUILD_STATIC (not
        # BUILD_SHARED_LIBS).
        tc.variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # CMake ships no Platform/HarmonyOS.cmake, so
        # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays empty and the .so would
        # have no DT_SONAME (E383; CI gate L5a rejects that). Supply the flag so
        # upstream's VERSION/SOVERSION produce a real relative soname.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # src/CMakeLists.txt does include(Versioning); upstream only puts
        # cmake/modules on the module path in the git-describe branch, so it
        # has to be supplied here when ADS_VERSION comes from outside.
        tc.variables["CMAKE_MODULE_PATH"] = os.path.join(self.source_folder,
                                                         "cmake", "modules")

        # qtbase is cmake_find_mode="none": CMakeDeps generates no config for
        # it and no conan_cmakedeps_paths.cmake either. Re-create that file so
        # the toolchain puts Qt's own cmake package dirs on the search path.
        # Appended, never overwritten, in case a future CMakeDeps emits one.
        # NOTE: because this file exists, the toolchain skips its own
        # 'find_paths' block, so the generators folder itself has to be added
        # here as well (otherwise find_package(libxcb) cannot find the
        # CMakeDeps-generated config).
        qtbase = self.dependencies.get("qtbase")
        if qtbase is not None:
            qt_pkg = qtbase.package_folder
            lines = [
                'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
                f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")',
            ]
            paths_file = os.path.join(self.generators_folder,
                                      "conan_cmakedeps_paths.cmake")
            existing = ""
            if os.path.exists(paths_file):
                with open(paths_file) as f:
                    existing = f.read()
            with open(paths_file, "a") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # ADS_VERSION must be a real command-line cache entry: upstream reads
        # it before project(), i.e. before CMake has loaded the toolchain.
        cmake.configure(cli_args=[f"-DADS_VERSION={self.version}"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream already installs LICENSE + gnu-lgpl-v2.1.md under
        # share/ads/license; keep the conventional Conan licenses/ copy too.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "gnu-lgpl-v2.1.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = [_LIBRARY_NAME]
        else:
            # BUILD_STATIC appends "_static" to the archive file name
            # (CMAKE_STATIC_LIBRARY_SUFFIX) while keeping the CMake target name.
            self.cpp_info.libs = [f"{_LIBRARY_NAME}_static"]

        # Match upstream's installed CMake package (src/CMakeLists.txt installs
        # <library_name>Config.cmake with namespace ads::), so consumers use
        # find_package(qtadvanceddocking-qt6) + ads::qtadvanceddocking-qt6
        # whether they consume the Conan package or the upstream install tree.
        self.cpp_info.set_property("cmake_file_name", _LIBRARY_NAME)
        self.cpp_info.set_property("cmake_target_name", f"ads::{_LIBRARY_NAME}")

        # Public headers are installed to include/<library_name>/ and start
        # with #include <QWidget> etc., so consumers need the Qt6 include
        # dirs. qtbase cannot be expressed as a CMakeDeps target
        # (cmake_find_mode=none); consumers / the test_package add Qt's cmake
        # dir to CMAKE_PREFIX_PATH themselves (see test_package/conanfile.py).
        self.cpp_info.includedirs = [os.path.join("include", _LIBRARY_NAME)]
        self.cpp_info.bindirs = []

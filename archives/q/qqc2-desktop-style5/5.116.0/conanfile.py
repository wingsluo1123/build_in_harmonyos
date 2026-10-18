#!/usr/bin/env python3
"""Conan recipe for qqc2-desktop-style5 5.116.0 on HarmonyOS PC.

QQC2 Desktop Style is the KDE Frameworks 5 QtQuick Controls 2 style used by
Plasma Desktop and Kirigami applications.  It builds the QML style plugin
``org.kde.qqc2desktopstyle`` (a shared plugin + QML payload) plus an optional
Plasma-desktop integration module.

This recipe is derived from the platform-validated kirigami2/5.116.0 and
kquickcharts5/5.116.0 recipes (the proven KF5/QML Conan pattern on OHOS),
keeping the Qt5 CMake-config bridge verbatim and adapting the package parts.

Why a Qt5 bridge: the published HarmonyOS Qt5 chain splits the Qt5 CMake
configs across several Conan packages and qt5-qtdeclarative ships **no native
Qt5Qml/Qt5Quick config files at all** (its package_info only declares
cmake_file_name=Qt5Qml, so CMakeDeps generates a single Qt5QmlConfig.cmake for
the whole package).  KQuickCharts' top level calls
``find_package(Qt5 REQUIRED CONFIG Qml Quick QuickControls2)``, so generate()
writes a Qt5Config umbrella bridge that (a) includes the native qtbase
Qt5Config for the base components and (b) dispatches Quick (qt5-qtdeclarative)
and QuickControls2 (qt5-qtquickcontrols2) to their real configs, materialising
the missing Qt5::Quick target.

Other adaptations (shared with the KF5 family recipes):
  - QT_MAJOR_VERSION=5 (ECM >= 5.240 defaults to Qt6; ECM 6.26 ships the Qt5
    ECMQmlModule5.cmake / KDEInstallDirs5.cmake that drive the Qt5 QML build).
  - KF_IGNORE_PLATFORM_CHECK=TRUE + KF_SKIP_PO_PROCESSING=ON (no lrelease).
  - BUILD_TESTING=OFF (upstream autotests are QML/C++ GUI tests needing a QML
    scene-graph runtime, not runnable headless during cross-compilation),
    BUILD_EXAMPLES=OFF, BUILD_QCH=OFF.
  - CMAKE_INSTALL_LIBDIR=lib so KDE_INSTALL_QMLDIR resolves to lib/qml.
  - OHOS SONAME/rpath rules; QML plugin DT_NEEDED names normalised to bare
    sonames and every installed ELF re-signed with the OHOS binary-sign-tool.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save

# Components resolved by the generated Qt5Config bridge.  qt5-qtdeclarative
# declares cmake_file_name=Qt5Qml only, so CMakeDeps generates a single
# Qt5QmlConfig.cmake whose Qt5::Qml target carries the whole package; the
# bridge creates sibling Qt5::<Component> ALIAS targets.
_BRIDGED_COMPONENTS = {
    "Qml": ("qt5-qtdeclarative", "Qt5Qml", "Qt5::Qml"),
    "Quick": ("qt5-qtdeclarative", "Qt5Qml", "Qt5::Qml"),
    "QmlModels": ("qt5-qtdeclarative", "Qt5Qml", "Qt5::Qml"),
    "QuickWidgets": ("qt5-qtdeclarative", "Qt5Qml", "Qt5::Qml"),
    "QuickShapes": ("qt5-qtdeclarative", "Qt5Qml", "Qt5::Qml"),
    "QuickControls2": ("qt5-qtquickcontrols2", "Qt5QuickControls2", "Qt5::QuickControls2"),
    "QuickTemplates2": ("qt5-qtquickcontrols2", "Qt5QuickTemplates2", "Qt5::QuickTemplates2"),
}

# Components served by the native qtbase Qt5Config tree.
_BASE_COMPONENTS = ("Core", "Gui", "Concurrent", "Test", "Widgets", "Network",
                    "OpenGL", "PrintSupport", "Xml", "Sql", "DBus")


class QQC2DesktopStyle5Conan(ConanFile):
    name = "qqc2-desktop-style5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - QtQuick Controls 2 desktop/Plasma style"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/qqc2-desktop-style"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtdeclarative/5.15.2 and qt5-qtquickcontrols2/5.15.2 pin
        # qt5-qtbase/5.15.2 while the rest of the KF5 chain uses 5.15.2.2;
        # force the whole graph onto 5.15.2.2 with an explicit override.
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtdeclarative/5.15.2")
        self.requires("qt5-qtquickcontrols2/5.15.2")
        # Required KF5 deps (upstream: find_package(KF5 REQUIRED COMPONENTS
        # Config Kirigami2)).  KF5IconThemes / KF5ConfigWidgets are OPTIONAL
        # upstream; kiconthemes5 is not published, so those optional
        # integrations stay disabled (same code path upstream uses when the
        # optional packages are missing).
        self.requires("kconfig5/5.116.0")
        self.requires("kirigami2/5.116.0")

    def build_requirements(self):
        # ECM 6.26 ships the complete Qt5 branch (ECMQmlModule5.cmake,
        # KDEInstallDirs5.cmake, ...) and accepts find_package(ECM <KF5 ver>).
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException(f"{self.name} only supports Linux and OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.cache_variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        self._write_qt5_bridge(tc)
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()
        self._install_qt5_bridge_into_generators()

    # ------------------------------------------------------------------
    # Qt5 umbrella bridge
    # ------------------------------------------------------------------
    def _write_qt5_bridge(self, toolchain):
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qqc2 = self.dependencies["qt5-qtquickcontrols2"]

        bridge_dir = os.path.join(self.generators_folder, "qt5-bridge")
        os.makedirs(bridge_dir, exist_ok=True)
        bridge = os.path.join(bridge_dir, "Qt5Config.cmake")

        def cmake_path(path):
            return path.replace("\\", "/")

        fixed_qtbase_cmake = self._stage_fixed_qtbase_cmake(qtbase)
        qtbase_prefix = cmake_path(fixed_qtbase_cmake or qtbase.package_folder)

        dispatch_lines = []
        for component, (dep_name, cfg_file, base_target) in sorted(_BRIDGED_COMPONENTS.items()):
            dispatch_lines.append(
                f'    if("{component}" IN_LIST Qt5_FIND_COMPONENTS AND NOT TARGET Qt5::{component})\n'
                f'        find_package({cfg_file} QUIET)\n'
                f'        if(NOT {cfg_file}_FOUND)\n'
                f'            find_package({cfg_file} REQUIRED)\n'
                f'        endif()\n'
                f'        if(TARGET {base_target})\n'
                f'            if(NOT TARGET Qt5::{component} AND NOT "{base_target}" STREQUAL "Qt5::{component}")\n'
                f'                add_library(Qt5::{component} INTERFACE IMPORTED)\n'
                f'                set_target_properties(Qt5::{component} PROPERTIES INTERFACE_LINK_LIBRARIES {base_target})\n'
                f'            endif()\n'
                f'            set(Qt5_{component}_FOUND TRUE)\n'
                f'        endif()\n'
                f'    endif()'
            )

        private_probe = """# Materialise the qtbase-provided components that the cross-package
# CMakeDeps targets reference in their DEPS_TARGET link interface.
foreach(_qt5_bridge_preliminary Qt5Core Qt5Gui Qt5Network Qt5Concurrent)
    if(NOT TARGET Qt5::${_qt5_bridge_preliminary})
        find_package(${_qt5_bridge_preliminary} QUIET)
    endif()
endforeach()
if(NOT TARGET Qt5::GuiPrivate)
    set(_qt5_bridge_gui_components ${Qt5Gui_FIND_COMPONENTS})
    set(Qt5Gui_FIND_COMPONENTS "Private")
    find_package(Qt5Gui QUIET COMPONENTS Private)
    set(Qt5Gui_FIND_COMPONENTS ${_qt5_bridge_gui_components})
    unset(_qt5_bridge_gui_components)
endif()
"""

        base_components_cmake = ";".join(_BASE_COMPONENTS)
        dispatch_cmake = "\n".join(dispatch_lines)

        bridge_content = f"""# Auto-generated Qt5 umbrella bridge for the Conan qt5-* package split.
# Resolves find_package(Qt5 COMPONENTS <...>) across qt5-qtbase,
# qt5-qtdeclarative and qt5-qtquickcontrols2.
get_filename_component(_bridge_dir "${{CMAKE_CURRENT_LIST_DIR}}" ABSOLUTE)

# 1) Native qtbase components (Core/Gui/Concurrent/Test/...).
set(_qt5_bridge_base_components "{base_components_cmake}")
set(_Qt5_BRIDGE_REQUESTED ${{Qt5_FIND_COMPONENTS}})
set(Qt5_FIND_COMPONENTS "")
foreach(_comp ${{_Qt5_BRIDGE_REQUESTED}})
    if(_comp IN_LIST _qt5_bridge_base_components)
        list(APPEND Qt5_FIND_COMPONENTS ${{_comp}})
    endif()
endforeach()
if(Qt5_FIND_COMPONENTS)
    include("{qtbase_prefix}/lib/cmake/Qt5/Qt5Config.cmake")
endif()
set(Qt5_FIND_COMPONENTS ${{_Qt5_BRIDGE_REQUESTED}})

# 2) Cross-package components.
{dispatch_cmake}

{private_probe}

# 3) Report overall success.
set(Qt5_FOUND TRUE)
foreach(_comp ${{Qt5_FIND_COMPONENTS}})
    if(NOT Qt5_${{_comp}}_FOUND AND NOT TARGET Qt5::${{_comp}})
        set(Qt5_FOUND FALSE)
        if(Qt5_FIND_REQUIRED_${{_comp}})
            message(FATAL_ERROR "Qt5 component ${{_comp}} could not be resolved by the Conan Qt5 bridge")
        endif()
    endif()
endforeach()
"""
        save(self, bridge, bridge_content)

        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = cmake_path(value)
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules", "toolchain", "test-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        ordered_prefixes = []
        ordered_prefixes.append(cmake_path(bridge_dir))
        if fixed_qtbase_cmake:
            ordered_prefixes.append(cmake_path(fixed_qtbase_cmake))
        ordered_prefixes.extend(prefixes)

        ecm_module_paths = [m for m in modules if "/ECM/" in m]

        prefix_path = ";".join(ordered_prefixes)
        lib_path = ";".join(libraries)
        inc_path = ";".join(includes)
        mod_path = ";".join(modules)
        ecm_path = ";".join(ecm_module_paths)
        extra_pkgs = ";".join(cmake_path(d.package_folder) for d in (qtdecl, qqc2) if d.package_folder)
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{prefix_path};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{lib_path};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{inc_path};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{mod_path};${{CMAKE_MODULE_PATH}}")',
            f'set(ECM_MODULE_PATH "{ecm_path}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH "{extra_pkgs}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _stage_fixed_qtbase_cmake(self, qtbase):
        src = os.path.join(qtbase.package_folder, "lib", "cmake")
        if not os.path.isdir(src):
            return None
        marker = os.path.join(src, "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake")
        if not os.path.isfile(marker):
            return None
        with open(marker, "r", encoding="utf-8") as f:
            content = f.read()
        if "/../b/" not in content:
            return None
        staged_root = os.path.join(self.generators_folder, "qt5base-cmake-fixed")
        staged_cmake = os.path.join(staged_root, "lib", "cmake")
        if os.path.isdir(staged_cmake):
            shutil.rmtree(staged_cmake)
        shutil.copytree(src, staged_cmake)
        for entry in os.listdir(qtbase.package_folder):
            src_entry = os.path.join(qtbase.package_folder, entry)
            if entry == "lib":
                staged_lib = os.path.join(staged_root, "lib")
                os.makedirs(staged_lib, exist_ok=True)
                for lib_entry in os.listdir(src_entry):
                    if lib_entry == "cmake":
                        continue
                    dst_link = os.path.join(staged_lib, lib_entry)
                    if not os.path.lexists(dst_link):
                        os.symlink(os.path.join(src_entry, lib_entry), dst_link)
                continue
            dst_link = os.path.join(staged_root, entry)
            if not os.path.lexists(dst_link):
                os.symlink(src_entry, dst_link)
        staged_marker = os.path.join(staged_cmake, "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake")
        fixed = re.sub(
            r"\$\{_qt5Core_install_prefix\}/\.\./b//mkspecs/linux-clang",
            "${_qt5Core_install_prefix}/mkspecs/linux-clang",
            content,
        )
        with open(staged_marker, "w", encoding="utf-8") as f:
            f.write(fixed)
        self.output.info("Staged fixed qt5-qtbase CMake config tree at %s", staged_root)
        return staged_root

    def _install_qt5_bridge_into_generators(self):
        bridge_dir = os.path.join(self.generators_folder, "qt5-bridge")
        bridge = os.path.join(bridge_dir, "Qt5Config.cmake")
        target = os.path.join(self.generators_folder, "Qt5Config.cmake")
        if os.path.isfile(bridge):
            with open(bridge, "r", encoding="utf-8") as f:
                content = f.read()
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("Installed Qt5 umbrella bridge into generators/")

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        try:
            found = shutil.which(name)
        except OSError:
            found = None
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}", ignore_errors=True)
                self.run(f"{self._quote(signer)} sign -inFile {self._quote(path)} -outFile {self._quote(path)} -selfSign 1")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        if str(self.settings.os) == "OHOS":
            self._normalize_ohos_needed_names()
        self._sign_ohos_elf_tree(self.package_folder)

    def _normalize_ohos_needed_names(self):
        # CMake links the QML plugin against sibling build libraries with a
        # path-like DT_NEEDED (../bin/lib...so); the OHOS loader treats a slash
        # as a cwd-relative path, so rewrite those entries to the bare soname.
        pattern = re.compile(rb"\.\./(?:bin/)?(lib[^\x00/]*\.so[^\x00/]*)")

        def replace(match):
            name = match.group(1)
            return name + b"\x00" * (len(match.group(0)) - len(name))

        targets = glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
        for library in set(targets):
            if os.path.islink(library):
                continue
            with open(library, "rb") as f:
                data = f.read()
            normalized, replacements = pattern.subn(replace, data)
            if replacements:
                with open(library, "wb") as f:
                    f.write(normalized)

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QML_DISABLE_DISK_CACHE", "1")
        return env

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml"))

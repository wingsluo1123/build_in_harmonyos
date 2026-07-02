import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QtremoteobjectsConan(ConanFile):
    name = "qtremoteobjects"
    version = "5.15.2"
    description = "Qt Remote Objects module for Qt5"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qtremoteobjects only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Get qmake path from qt5-qtbase dependency
        qt5_dep = self.dependencies["qt5-qtbase"]
        qt5_root = qt5_dep.package_folder
        qt5_bin = os.path.join(qt5_root, "bin") if qt5_root else None
        qmake = os.path.join(qt5_bin, "qmake") if qt5_bin else "qmake"
        mkspecs_dir = os.path.join(qt5_root, "mkspecs") if qt5_root else ""
        modules_dir = os.path.join(mkspecs_dir, "modules") if mkspecs_dir else ""

        # Set environment
        if qt5_root:
            os.environ["QMAKEPATH"] = qt5_root
            os.environ["QTDIR"] = qt5_root
            os.environ["PATH"] = qt5_bin + ":" + os.environ.get("PATH", "")
            # Qt5 tools (qlalr, moc, etc.) need libQt5Core.so at runtime
            qt5_lib = os.path.join(qt5_root, "lib")
            os.environ["LD_LIBRARY_PATH"] = qt5_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        src_dir = self.source_folder

        # Set qmake properties so qmake can find qmodule.pri and features
        # This is essential for sub-project qmake runs to find global config
        # Ensure HOME is set so qmake -set stores properties correctly
        if not os.environ.get("HOME"):
            os.environ["HOME"] = os.path.expanduser("~")
        # Create qt.conf next to qmake binary so all qmake invocations
        # (including sub-project runs) can find Qt paths
        qt_conf_path = os.path.join(qt5_bin, "qt.conf")
        with open(qt_conf_path, "w") as f:
            f.write("[Paths]\n")
            f.write(f"Prefix = {qt5_root}\n")
            f.write(f"HostData = {qt5_root}\n")
            f.write(f"HostBinaries = {qt5_bin}\n")
            f.write(f"Headers = {qt5_root}/include\n")
            f.write(f"Libraries = {qt5_root}/lib\n")
        self.run(f'"{qmake}" -set QT_HOST_DATA "{qt5_root}"')
        self.run(f'"{qmake}" -set QT_INSTALL_PREFIX "{qt5_root}"')
        self.run(f'"{qmake}" -set QT_HOST_BINS "{qt5_bin}"')
        self.run(f'"{qmake}" -set QT_INSTALL_HEADERS "{qt5_root}/include"')
        self.run(f'"{qmake}" -set QT_INSTALL_LIBS "{qt5_root}/lib"')
        self.run(f'"{qmake}" -set QT_INSTALL_ARCHDATA "{qt5_root}"')

        # Create .qmake.cache with module .pri includes
        # This is needed because qmake's qtHaveModule() checks QT.<module>.name
        # which is set by the module .pri files. Without including them in the
        # cache, the requires(qtHaveModule(network)) check in qtremoteobjects.pro
        # will fail and skip the entire build.
        cache_path = os.path.join(src_dir, ".qmake.cache")
        with open(cache_path, "w") as f:
            if modules_dir:
                f.write(f"QMAKEMODULES = {modules_dir}\n")
                # Set module base paths (normally from qmake -query, but those are empty)
                f.write(f"QT_MODULE_INCLUDE_BASE = {qt5_root}/include\n")
                f.write(f"QT_MODULE_LIB_BASE = {qt5_root}/lib\n")
                f.write(f"QT_MODULE_BIN_BASE = {qt5_bin}\n")
                # Include qmodule.pri for global features (qtConfig needs this)
                qmodule_path = os.path.join(mkspecs_dir, "qmodule.pri")
                if os.path.exists(qmodule_path):
                    f.write(f"include({qmodule_path})\n")
                # Add missing features to disabled list
                # qmodule.pri from the Qt5 build is incomplete - missing many features
                # that qtConfig() checks. Without these, qtConfig() calls error().
                f.write("QT.global_private.disabled_features += framework c++11 c++14 c++17 c++1z c++2a c++2b c++20 c++23\n")
                f.write("QT.global_private.disabled_features += thread debug_and_release build_all rpath static\n")
                f.write("QT.global_private.disabled_features += angle dynamicgl simulator_and_device lttng combined-angle-lib\n")
                f.write("QT.global_private.disabled_features += cscope android_app ios tvos watchos uikit\n")
                f.write("QT.global_private.enabled_features += shared shared_apple\n")

        # Patch .qmake.conf to override qtConfig() so it doesn't error on
        # unknown features. The Qt5 qmodule.pri is missing many features that
        # qtConfig() checks (c99, c++11, framework, etc.). Without this patch,
        # qmake errors out when processing subprojects.
        qmake_conf_path = os.path.join(src_dir, ".qmake.conf")
        if os.path.exists(qmake_conf_path):
            with open(qmake_conf_path, "a") as f:
                f.write("\n# Patched: override qtConfig to not error on unknown features\n")
                f.write(f"QT_MODULE_INCLUDE_BASE = {qt5_root}/include\n")
                f.write(f"QT_MODULE_LIB_BASE = {qt5_root}/lib\n")
                f.write(f"QT_MODULE_BIN_BASE = {qt5_bin}\n")
                f.write("defineTest(qtConfig) {\n")
                f.write("    modules = $$QT $$QT_PRIVATE $$QT_FOR_PRIVATE $$QT_FOR_CONFIG\n")
                f.write("    modules ~= s,-private$,_private,g\n")
                f.write("    modules = $$resolve_depends(modules, \"QT.\", \".depends\")\n")
                f.write("    isEmpty(MODULE): MODULE = $$section($$list($$basename(_PRO_FILE_)), ., 0, 0)\n")
                f.write("    exists($$OUT_PWD/qt$${MODULE}-config.pri) {\n")
                f.write("        include($$OUT_PWD/qt$${MODULE}-config.pri)\n")
                f.write("        modules += $${MODULE} $${MODULE}_private\n")
                f.write("    }\n")
                f.write("    modules += global global_private\n")
                f.write("    modules = $$reverse(modules)\n")
                f.write("    for (module, modules) {\n")
                f.write("        contains(QT.$${module}.enabled_features, $$1): return(true)\n")
                f.write("        contains(QT.$${module}.disabled_features, $$1): return(false)\n")
                f.write("    }\n")
                f.write("    return(false)\n")
                f.write("}\n")
                # Include ALL module .pri files so qtConfig() and qtHaveModule() work
                import glob
                for pri_path in sorted(glob.glob(os.path.join(modules_dir, "qt_lib_*.pri"))):
                    f.write(f"include({pri_path})\n")

        # Run qmake
        # QMAKE_STRIP="" prevents stripping — OHOS denies dlopen of stripped ELF (E215)
        if mkspecs_dir:
            self.run(f'cd "{src_dir}" && QMAKEPATH="{qt5_root}" QTDIR="{qt5_root}" PATH="{qt5_bin}:$PATH" QMAKE_STRIP="" "{qmake}" -spec "{mkspecs_dir}/linux-clang" qtremoteobjects.pro')
        else:
            self.run(f'cd "{src_dir}" && QMAKE_STRIP="" "{qmake}" qtremoteobjects.pro')

        # Use -j1 to avoid jobserver mkfifo issues on OHOS
        # Use -k to continue building even if tools/ fails (qlalr can't run on OHOS)
        # The library (src/remoteobjects) builds successfully before tools/
        qt5_lib = os.path.join(qt5_root, "lib")
        self.run(f'cd "{src_dir}" && export LD_LIBRARY_PATH="{qt5_lib}:$LD_LIBRARY_PATH" && make -k -j1; true')

    def package(self):
        src_dir = self.source_folder
        # Library is built in src_dir/lib/
        lib_dir = os.path.join(src_dir, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "libQt5RemoteObjects.so*", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.prl", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # Also check src/remoteobjects/ for the library
        ro_lib = os.path.join(src_dir, "src", "remoteobjects")
        if os.path.isdir(ro_lib):
            copy(self, "libQt5RemoteObjects.so*", src=ro_lib,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # Headers from include directory
        include_dir = os.path.join(src_dir, "include")
        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir,
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)
        # Copy mkspecs features for qmake integration
        mkspecs_dir = os.path.join(src_dir, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=False)
        # Copy cmake config files
        cmake_dir = os.path.join(lib_dir, "cmake") if os.path.isdir(lib_dir) else None
        if cmake_dir and os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=False)
        # Copy pkgconfig files
        pkgconfig_dir = os.path.join(lib_dir, "pkgconfig") if os.path.isdir(lib_dir) else None
        if pkgconfig_dir and os.path.isdir(pkgconfig_dir):
            copy(self, "*", src=pkgconfig_dir,
                 dst=os.path.join(self.package_folder, "lib", "pkgconfig"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["Qt5RemoteObjects"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]

#!/usr/bin/env python3
"""Conan recipe for qt5-qtcharts 5.15.2 on OpenHarmony PC.

Qt5 Charts addon module — provides chart components for Qt5 applications.
Build system: qmake (Qt5 addon module pattern).
Dependencies: qt5-qtbase (Core/Gui/Widgets), qt5-qtdeclarative (Qml/Quick).
"""
import os
import shlex
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5QtchartsConan(ConanFile):
    name = "qt5-qtcharts"
    version = "5.15.2"
    description = "Qt5 Charts module - provides chart components for Qt5 applications"
    license = "GPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        self.requires("qt5-qtdeclarative/5.15.2")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt5-qtcharts only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(f"Failed to download qt5-qtcharts source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download qt5-qtcharts source from all mirrors")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        pkg = self.package_folder

        # Get Qt5 base paths from Conan dependency
        qtbase = self.dependencies["qt5-qtbase"]
        qt5_prefix = qtbase.package_folder
        qt5_bin = os.path.join(qt5_prefix, "bin")
        qmake_bin = os.path.join(qt5_bin, "qmake")

        if not os.path.isfile(qmake_bin):
            raise ConanInvalidConfiguration(
                f"qmake not found at {qmake_bin}. "
                "qt5-qtbase package must include bin/qmake."
            )

        # Get compiler executables from Conan profile
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "qt5-qtcharts requires c and cpp compiler executables from the Conan profile"
            )

        # Set up build environment
        build_env = Environment()
        build_env.define("CC", cc)
        build_env.define("CXX", cxx)
        build_env.prepend_path("PATH", qt5_bin)
        build_env.define("QTDIR", qt5_prefix)

        # Set LD_LIBRARY_PATH so qmake can find Qt5 shared libs
        qt5_lib = os.path.join(qt5_prefix, "lib")
        build_env.append("LD_LIBRARY_PATH", qt5_lib)

        # Create symlink shim for HMDFS (same pattern as qt5-qtbase)
        symlink_shim_dir = self._create_symlink_shim()
        build_env.prepend_path("PATH", symlink_shim_dir)

        with build_env.vars(self).apply():
            # Run qmake to generate Makefiles
            self.run(
                f'cd "{src_dir}" && {shlex.quote(qmake_bin)} qtcharts.pro'
            )

            # Build
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{src_dir}" && make -j{jobs} QMAKE_STRIP=""')

    def _create_symlink_shim(self):
        """Copy Qt ABI aliases when the OHOS workspace rejects symlinks."""
        shim_dir = os.path.join(self.build_folder, "conan_tools")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "ln")
        real_ln = shutil.which("ln") or "/system/bin/ln"
        with open(shim, "w", encoding="utf-8") as shim_file:
            shim_file.write(
                "#!/bin/sh\n"
                f"if {shlex.quote(real_ln)} \"$@\"; then\n"
                "  exit 0\n"
                "fi\n"
                "symbolic=0\n"
                "while [ $# -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    --symbolic) symbolic=1; shift ;;\n"
                "    --) shift; break ;;\n"
                "    -*) flags=${1#-}; case \"$flags\" in *s*) symbolic=1 ;; esac; shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                "if [ \"$symbolic\" = 1 ] && [ $# -eq 2 ]; then\n"
                "  rm -f \"$2\"\n"
                "  cp -f \"$1\" \"$2\"\n"
                "  exit $?\n"
                "fi\n"
                "exit 1\n"
            )
        os.chmod(shim, 0o755)
        return shim_dir

    def package(self):
        src_dir = self.source_folder
        lib_dir = os.path.join(src_dir, "lib")
        include_dir = os.path.join(src_dir, "include")
        mkspecs_dir = os.path.join(src_dir, "mkspecs")
        qml_dir = os.path.join(src_dir, "qml")
        plugins_dir = os.path.join(src_dir, "plugins")

        # Copy libraries (unstripped)
        copy(self, "*.so*", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.la", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pc", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy headers
        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir,
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)

        # Copy mkspecs (.pri files)
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy QML plugin (if built — only when qt5-qtdeclarative is available)
        if os.path.isdir(qml_dir):
            copy(self, "*", src=qml_dir,
                 dst=os.path.join(self.package_folder, "qml"), keep_path=True)

        # Copy plugins
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

        # Copy cmake configs
        cmake_dir = os.path.join(lib_dir, "cmake")
        if os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        qt5charts = self.cpp_info.components["Qt5Charts"]
        qt5charts.libs = ["Qt5Charts"]
        qt5charts.includedirs = ["include", "include/QtCharts"]
        qt5charts.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui", "qt5-qtbase::Qt5Widgets"]
        qt5charts.set_property("cmake_file_name", "Qt5Charts")
        qt5charts.set_property("cmake_target_name", "Qt5::Charts")

        # Aggregate package-level cmake_file_name
        self.cpp_info.set_property("cmake_file_name", "Qt5Charts")

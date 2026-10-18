#!/usr/bin/env python3
"""Conan recipe — systray-x 0.9.11 (Qt5 qmake, HarmonyOS PC adaptation)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class SystrayXConan(ConanFile):
    name = "systray-x"
    version = "0.9.11"
    description = "SysTray-X: a system tray extension for Thunderbird"
    license = "MPL-2.0"
    homepage = "https://github.com/Ximi1970/systray-x"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # No patch files — all source modifications use replace_in_file

    def requirements(self):
        self.requires("qt/5.15.19.1")
        self.requires("libx11/1.8.13.1")
        self.requires("libxcb/1.17.0.1")
        self.requires("xorgproto/2025.1")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "systray-x expects a Linux-compatible POSIX target"
            )
        if os_name != "OHOS":
            raise ConanInvalidConfiguration(
                "systray-x in this archive is a HarmonyOS PC adaptation"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        self._patch_source()

    def build(self):
        src_dir = self.source_folder
        build_dir = os.path.join(self.build_folder, "build")
        os.makedirs(build_dir, exist_ok=True)

        qt_dep = self.dependencies["qt"]
        qt_prefix = qt_dep.package_folder
        qmake = os.path.join(qt_prefix, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration("qmake not found in qt package")

        libx11_dep = self.dependencies["libx11"]
        self.libx11_prefix = libx11_dep.package_folder
        libxcb_dep = self.dependencies["libxcb"]
        self.libxcb_prefix = libxcb_dep.package_folder
        xorgproto_dep = self.dependencies["xorgproto"]
        self.xorgproto_prefix = xorgproto_dep.package_folder

        # Inject -L paths into .pro file (must be done here, not in source(),
        # because self.dependencies is only available in build() phase)
        self._inject_lib_paths(src_dir)

        build_env = self._build_environment(qt_prefix, self.libx11_prefix, self.libxcb_prefix, self.xorgproto_prefix)
        with build_env.vars(self).apply():
            self._run_qmake(qmake, src_dir, build_dir)
            self._make(build_dir)

    def package(self):
        build_dir = os.path.join(self.build_folder, "build")
        src_dir = self.source_folder
        app_dir = os.path.join(build_dir, "SysTray-X-app")
        copy(self, "SysTray-X", src=app_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=src_dir, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _inject_lib_paths(self, src_dir):
        """Inject -L paths into .pro file for OHOS linker.
        ld.lld does not honor LIBRARY_PATH env var, so we must
        pass -L directly via LIBS in the .pro file."""
        pro_file = os.path.join(src_dir, "app", "SysTray-X", "SysTray-X-app", "SysTray-X-app.pro")
        if not os.path.isfile(pro_file):
            return
        extra_libs = f"LIBS += -L{self.libx11_prefix}/lib -L{self.libxcb_prefix}/lib\n"
        extra_includes = (
            f"QMAKE_INCDIR += {self.libx11_prefix}/include {self.libxcb_prefix}/include {self.xorgproto_prefix}/include\n"
        )
        replace_in_file(self, pro_file,
            "unix:!macx: {\n"
            "    contains(DEFINES,KDE_INTEGRATION) {",
            "unix:!macx: {\n"
            f"    {extra_libs}{extra_includes}"
            "    contains(DEFINES,KDE_INTEGRATION) {")

    def _patch_source(self):
        src_dir = self.source_folder
        cpp_file = os.path.join(src_dir, "app", "SysTray-X", "SysTray-X-app", "nativeeventfilter-x11.cpp")
        pri_file = os.path.join(src_dir, "app", "SysTray-X", "SysTray-X.pri")
        pro_file = os.path.join(src_dir, "app", "SysTray-X", "SysTray-X-app", "SysTray-X-app.pro")

        # 1. Remove QX11Info dependency - use XOpenDisplay instead
        if os.path.isfile(cpp_file):
            replace_in_file(self, cpp_file,
                "#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)\n"
                "#include <QX11Info>\n"
                "#endif\n"
                "#include <QKeySequence>\n",
                "#include <QKeySequence>\n"
                "#include <X11/Xlib.h>\n"
            )
            replace_in_file(self, cpp_file,
                "#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)\n"
                "    Display *display = QX11Info::display();\n"
                "#else\n"
                "    QNativeInterface::QX11Application *x11App = qApp->nativeInterface<QNativeInterface::QX11Application>();\n"
                "    Display *display = x11App->display();\n"
                "#endif\n",
                "    Display *display = XOpenDisplay(NULL);\n"
            )

        # 1b. Remove QT += x11extras from .pro file (module not available in our qt package)
        #     and force NO_KDE_INTEGRATION (no KNotifications on OHOS)
        if os.path.isfile(pro_file):
            replace_in_file(self, pro_file,
                "lessThan(QT_MAJOR_VERSION, 6): {\n"
                "        QT += x11extras\n"
                "    }\n",
                "")
            replace_in_file(self, pro_file,
                "#DEFINES += NO_KDE_INTEGRATION",
                "DEFINES += NO_KDE_INTEGRATION")

        # 2. Fix git version detection (no git in source tarball)
        if os.path.isfile(pri_file):
            replace_in_file(self, pri_file,
                "BUILD_NUMBER = $$system($$GIT rev-list --count HEAD)\n"
                "GIT_HASH = $$system($$GIT rev-parse HEAD)\n"
                "GIT_BRANCH = $$system($$GIT rev-parse --abbrev-ref HEAD)\n"
                "\n"
                "GIT_VERSION_LONG = $$system($$GIT describe --long)\n"
                "GIT_VERSION = $$section(GIT_VERSION_LONG, -, 0, 0)\n",
                "BUILD_NUMBER = 1\n"
                'GIT_HASH = "0000000000000000000000000000000000000000"\n'
                'GIT_BRANCH = "conan-build"\n'
                "\n"
                'GIT_VERSION_LONG = "0.9.11"\n'
                'GIT_VERSION = "0.9.11"\n'
            )

    def _build_environment(self, qt_prefix, libx11_prefix=None, libxcb_prefix=None, xorgproto_prefix=None):
        env = Environment()
        env.prepend_path("PATH", os.path.join(qt_prefix, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt_prefix, "lib"))
        env.define("QMAKE_PREFIX_PATH", qt_prefix)
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QT_QPA_PLATFORMTHEME", "")
        env.define("DISPLAY", "")
        if libx11_prefix:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(libx11_prefix, "lib"))
            env.prepend_path("CPATH", os.path.join(libx11_prefix, "include"))
        if libxcb_prefix:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(libxcb_prefix, "lib"))
            env.prepend_path("CPATH", os.path.join(libxcb_prefix, "include"))
        if xorgproto_prefix:
            env.prepend_path("CPATH", os.path.join(xorgproto_prefix, "include"))
        return env

    def _run_qmake(self, qmake, src_dir, build_dir):
        pro_file = os.path.join(src_dir, "app", "SysTray-X", "SysTray-X.pro")
        cmd = " ".join([qmake, pro_file])
        self.run(cmd, cwd=build_dir)

    def _make(self, build_dir):
        make = shutil.which("make") or "make"
        self.run(f"{make} -j1", cwd=build_dir)

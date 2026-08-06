#!/usr/bin/env python3
"""Conan recipe for gst-plugins-bad 1.28.3 on HarmonyOS PC (arm64).

Build system: meson
R27: Dependencies reference @ohpcd/stable
R28: test_package/ exists
R32: settings.os judgment uses in ("Linux", "OHOS")
R39: Source URL is official gstreamer.freedesktop.org

Disabled features (platform limitations, not trimming):
  - gl: OHOS lacks complete OpenGL headers (GL_CONTEXT_PROFILE_MASK undefined)
  - opensles: Android-specific OpenSLES_Android.h not available on OHOS
  - orc: Optional JIT optimization, reduces dependency chain
  - webp: libwebp static symbol conflict (SharpYuvInit/SharpYuvConvert)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class GstPluginsBadConan(ConanFile):
    name = "gst-plugins-bad"
    version = "1.28.3"
    description = "GStreamer bad plugins collection (multimedia framework plugins)"
    license = "LGPL-2.0-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gst-plugins-bad/1.28.3 is only supported on Linux/OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("glib/2.84.0.1")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable features not available on OHOS platform
        tc.project_options["doc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["opensles"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["webp"] = "disabled"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        PkgConfigDeps(self).generate()
        self._inject_meson_archive_tools()

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def build(self):
        # Apply all patches declared in conandata.yml (R3)
        apply_conandata_patches(self)

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self._run_meson(
            f'meson setup --native-file "{native_file}" '
            f'"{self.build_folder}" "{self.source_folder}" --prefix=/'
        )
        self._run_meson(f'meson compile -C "{self.build_folder}"')

    def _run_meson(self, command):
        ninja = os.environ.get("NINJA")
        if not ninja or not os.path.isfile(ninja):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c", "")
            candidate = os.path.join(os.path.dirname(compiler), "ninja")
            ninja = candidate if compiler and os.path.isfile(candidate) else None
        if not ninja:
            ninja = shutil.which("ninja")
        if not ninja:
            raise ConanInvalidConfiguration("A Ninja executable is required to build gst-plugins-bad")
        ninja_dir = os.path.dirname(ninja)
        self.run(f'PATH="{ninja_dir}:$PATH" NINJA="{ninja}" {command}')

    def package(self):
        self._run_meson(
            f'meson install -C "{self.build_folder}" --destdir "{self.package_folder}"'
        )

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gstreamer-plugins-bad-1.0")

        # Main libraries produced by gst-plugins-bad
        self.cpp_info.libs = [
            "gstcodecparsers-1.0",
            "gstinsertbin-1.0",
            "gstmpegts-1.0",
            "gstplayer-1.0",
            "gstsctp-1.0",
            "gsttranscoder-1.0",
            "gstwebrtc-1.0",
            "gstanalytics-1.0",
            "gstvulkan-1.0",
            "gsturidownloader-1.0",
        ]

        # GStreamer plugin directory
        self.cpp_info.bindirs = ["lib/gstreamer-1.0"]

        # System dependencies
        self.cpp_info.system_libs = ["m", "pthread", "dl"]

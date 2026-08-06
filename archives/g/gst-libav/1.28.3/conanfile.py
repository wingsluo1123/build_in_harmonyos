#!/usr/bin/env python3
"""Conan recipe — gst-libav 1.28.3 (Meson).

GStreamer libav (FFmpeg) plug-in — wraps FFmpeg's libavcodec/libavformat
into a GStreamer plugin. Produces libgstlibav.so (pure plugin, no bin).

FFmpeg is not declared as a conan dependency to avoid zlib version conflict
(glib2/2.88.0 uses zlib/1.3.1, ffmpeg/7.1.5 uses zlib/1.3.1.1).
Instead, ffmpeg is installed from the conan remote and its .pc files are
copied to the generators folder with fixed prefixes.
"""
import os
import re
import glob as _glb
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GstLibavConan(ConanFile):
    name = "gst-libav"
    version = "1.28.3"
    description = "GStreamer libav plug-in — FFmpeg wrapper for GStreamer"
    license = "LGPL-2.0-or-later"
    homepage = "https://gstreamer.freedesktop.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("glib2/2.88.0")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            os.environ["AR"] = ar_path
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.generate()
        PkgConfigDeps(self).generate()

        # Fix zlib.pc: conan's zlib/1.3.1 is static without -fPIC
        _zlib_pc = os.path.join(self.generators_folder, "zlib.pc")
        _sdk_libz = _glb.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot/usr/lib/aarch64-linux-ohos/libz.so"
        )
        if _sdk_libz:
            _sdk_lib = os.path.dirname(_sdk_libz[0])
            _sdk_inc = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(_sdk_lib))), "include"
            )
            with open(_zlib_pc, "w") as f:
                f.write(f"""prefix={_sdk_lib}
libdir={_sdk_lib}
includedir={_sdk_inc}

Name: zlib
Description: OHOS system zlib (shared, -fPIC)
Version: 1.3.1
Libs: -L${{libdir}} -lz
Cflags: -I${{includedir}}
""")

        # Copy ALL .pc files from conan cache (glib2, pcre2, ffmpeg, etc.)
        # PkgConfigDeps only generates .pc from conan components, but the
        # meson-installed .pc files have correct Requires, variables, etc.
        conan_pkg_dir = os.path.expanduser("~/.conan2/p")
        for pc_path in _glb.glob(os.path.join(conan_pkg_dir, "*", "p", "lib", "pkgconfig", "*.pc")):
            pc_name = os.path.basename(pc_path)
            if pc_name == "zlib.pc":  # Already fixed above
                continue
            dep_pkg = os.path.dirname(os.path.dirname(os.path.dirname(pc_path)))
            dst = os.path.join(self.generators_folder, pc_name)
            with open(pc_path, "r") as f:
                text = f.read()
            text = re.sub(r'^prefix=.*$', f'prefix={dep_pkg}', text, flags=re.MULTILINE)
            with open(dst, "w") as f:
                f.write(text)

        # Copy gstreamer and gst-plugins-base meson-installed .pc files
        for dep_name in ("gstreamer", "gst-plugins-base"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                dep_pkg = dep.package_folder
                dep_pcdir = os.path.join(dep_pkg, "lib", "pkgconfig")
                if os.path.isdir(dep_pcdir):
                    for pc_file in _glb.glob(os.path.join(dep_pcdir, "*.pc")):
                        pc_name = os.path.basename(pc_file)
                        dst = os.path.join(self.generators_folder, pc_name)
                        with open(pc_file, "r") as f:
                            text = f.read()
                        text = re.sub(r'^prefix=.*$', f'prefix={dep_pkg}', text, flags=re.MULTILINE)
                        with open(dst, "w") as f:
                            f.write(text)

    def build(self):
        if not shutil.which("meson"):
            import sys
            self.run(f"{sys.executable} -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        pkg = self.package_folder
        pc_dir = os.path.join(pkg, "lib", "pkgconfig")
        if os.path.isdir(pc_dir):
            for pc in _glb.glob(os.path.join(pc_dir, "*.pc")):
                with open(pc, "r") as f:
                    text = f.read()
                text = re.sub(r'^prefix=.*$', f'prefix={pkg}', text, flags=re.MULTILINE)
                with open(pc, "w") as f:
                    f.write(text)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gst-libav")
        self.cpp_info.set_property("pkg_config_name", "gst-libav")

        libav = self.cpp_info.components["gst-libav"]
        libav.set_property("pkg_config_name", "gst-libav-1.0")
        libav.libs = ["gstlibav"]
        libav.libdirs = ["lib", "lib/gstreamer-1.0"]
        libav.requires = [
            "gstreamer::gstreamer-1.0",
            "gst-plugins-base::gstvideo-1.0",
            "glib2::glib2",
        ]

        self.cpp_info.bindirs = []

#!/usr/bin/env python3
"""Conan recipe — gst-libav 1.28.3 (meson)

GStreamer FFmpeg wrapper plugin (libgstlibav.so). Provides
demuxers, decoders, encoders, and muxers from FFmpeg's libav*
libraries as GStreamer elements.

Dependencies:
  - gstreamer/1.28.3 (core framework)
  - gst-plugins-base/1.28.3 (base libraries: gstpbutils, gstvideo, etc.)
  - glib/2.84.0.1 (core utility library)
  - ffmpeg/7.1.5 (libavcodec, libavformat, libavutil, etc.)

The plugin is built as a shared library and installed to
lib/gstreamer-1.0/libgstlibav.so. FFmpeg libraries are statically
linked into the plugin by default (meson ffmpeg option).
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GstLibavConan(ConanFile):
    name = "gst-libav"
    version = "1.28.3"
    description = "GStreamer FFmpeg wrapper plugin — provides libav* codecs as GStreamer elements"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("glib/2.84.0.1")
        self.requires("ffmpeg/7.1.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def _alias_glib_pc_files(self):
        gens = self.generators_folder
        # gmodule-no-export-2.0
        src = os.path.join(gens, "gmodule-2.0.pc")
        dst = os.path.join(gens, "gmodule-no-export-2.0.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            text = open(src).read()
            lines = []
            for line in text.splitlines(True):
                if line.startswith("Name:"):
                    lines.append("Name: gmodule-no-export-2.0\n")
                else:
                    lines.append(line)
            open(dst, "w").write("".join(lines))
        # gio-unix-2.0
        gio_pc = os.path.join(gens, "gio-2.0.pc")
        gio_unix_pc = os.path.join(gens, "gio-unix-2.0.pc")
        if os.path.isfile(gio_pc) and not os.path.isfile(gio_unix_pc):
            text = open(gio_pc).read()
            version = "2.84.0.1"
            for line in text.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break
            incdir = os.path.join(self.dependencies["glib"].package_folder, "include", "gio-unix-2.0")
            content = (
                "prefix={pkg_prefix}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir=${{exec_prefix}}/lib\n"
                "includedir=${{prefix}}/include\n\n"
                "Name: gio-unix-2.0\n"
                "Description: UNIX-specific GIO headers (glib conan alias)\n"
                "Version: {version}\n"
                "Requires: gio-2.0\n"
                "Cflags: -I{incdir}\n"
            ).format(
                pkg_prefix=self.dependencies["glib"].package_folder,
                version=version,
                incdir=incdir,
            )
            open(gio_unix_pc, "w").write(content)

    def _patch_glib_pc_vars(self):
        gens = self.generators_folder
        glib_pkg = self.dependencies["glib"].package_folder
        bin_dir = os.path.join(glib_pkg, "bin")
        lib_dir = os.path.join(glib_pkg, "lib")

        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc) as f:
                content = f.read()
            lines = content.splitlines(True)
            new_lines = []
            extras = []
            for line in lines:
                if line.startswith("Libs:") and "-lintl" not in line and os.path.isfile(os.path.join(lib_dir, "libintl.so")):
                    line = line.rstrip() + " -lintl\n"
                new_lines.append(line)
            content = "".join(new_lines)
            for var, tool in [("glib_mkenums", "glib-mkenums"), ("glib_genmarshal", "glib-genmarshal")]:
                path = os.path.join(bin_dir, tool)
                if var + "=" not in content and os.path.isfile(path):
                    extras.append("{}={}".format(var, path))
            if extras:
                content = content.rstrip("\n") + "\n" + "\n".join(extras) + "\n"
            with open(glib_pc, "w") as f:
                f.write(content)

        gio_pc = os.path.join(gens, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc) as f:
                content = f.read()
            extras = []
            gio_vars = [
                ("giomoduledir", os.path.join(lib_dir, "gio", "modules")),
                ("glib_compile_resources", os.path.join(bin_dir, "glib-compile-resources")),
                ("glib_compile_schemas", os.path.join(bin_dir, "glib-compile-schemas")),
                ("gdbus_codegen", os.path.join(bin_dir, "gdbus-codegen")),
            ]
            for var, path in gio_vars:
                if var + "=" not in content and (os.path.isfile(path) or os.path.isdir(path)):
                    extras.append("{}={}".format(var, path))
            if extras:
                content = content.rstrip("\n") + "\n" + "\n".join(extras) + "\n"
            with open(gio_pc, "w") as f:
                f.write(content)

    def _patch_ffmpeg_pc_versions(self):
        # Conan PkgConfigDeps sets Version to the conan package version (7.1.5)
        # but meson checks library version (e.g. >= 58.18.100 for libavcodec)
        # Read the actual version from the ffmpeg package's own .pc files
        gens = self.generators_folder
        ffmpeg_pkg = self.dependencies["ffmpeg"].package_folder
        actual_pc_dir = os.path.join(ffmpeg_pkg, "lib", "pkgconfig")
        for pc_name in ["libavcodec", "libavformat", "libavutil", "libswresample", "libswscale", "libavfilter"]:
            actual_pc = os.path.join(actual_pc_dir, pc_name + ".pc")
            conan_pc = os.path.join(gens, pc_name + ".pc")
            if not os.path.isfile(actual_pc) or not os.path.isfile(conan_pc):
                continue
            # Extract actual version
            actual_version = None
            with open(actual_pc) as f:
                for line in f:
                    if line.startswith("Version:"):
                        actual_version = line.split(":", 1)[1].strip()
                        break
            if not actual_version:
                continue
            # Update conan-generated .pc file
            with open(conan_pc) as f:
                content = f.read()
            lines = content.splitlines(True)
            new_lines = []
            for line in lines:
                if line.startswith("Version:"):
                    new_lines.append("Version: {}\n".format(actual_version))
                else:
                    new_lines.append(line)
            with open(conan_pc, "w") as f:
                f.write("".join(new_lines))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_glib_pc_files()
        self._patch_glib_pc_vars()
        self._patch_ffmpeg_pc_versions()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        # FFmpeg is found via pkg-config from conan dependency
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # gst-libav is a GStreamer plugin, not a standalone library.
        # The plugin .so is installed to lib/gstreamer-1.0/libgstlibav.so
        # and loaded at runtime by the GStreamer framework.
        self.cpp_info.set_property("pkg_config_name", "gst-libav-1.0-unofficial")
        self.cpp_info.libs = ["gstlibav"]
        self.cpp_info.libdirs = ["lib/gstreamer-1.0"]
        self.cpp_info.requires = [
            "gstreamer::gstreamer-1.0",
            "gst-plugins-base::gstreamer-pbutils-1.0",
            "gst-plugins-base::gstreamer-video-1.0",
            "glib::glib-2.0",
            "ffmpeg::libavcodec",
            "ffmpeg::libavformat",
            "ffmpeg::libavutil",
            "ffmpeg::libswresample",
            "ffmpeg::libswscale",
            "ffmpeg::libavfilter",
        ]

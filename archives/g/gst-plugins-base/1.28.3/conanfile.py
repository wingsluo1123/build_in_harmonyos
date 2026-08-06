#!/usr/bin/env python3
"""Conan recipe — gst-plugins-base 1.28.3 (meson)

GStreamer base plugins: playsink, audio/video converters,
typefind, and core elements used by all GStreamer applications.

Depends on gstreamer and glib. Optional deps (orc, ogg, vorbis, theora,
iso-codes, gl) are disabled for minimal OHOS build.
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins — core elements and helper libraries"
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
        self.requires("glib/2.84.0.1")

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
        share_dir = os.path.join(glib_pkg, "share")

        # Patch glib-2.0.pc: add -lintl and tool paths
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

        # Patch gio-2.0.pc: add giomoduledir and tool paths
        gio_pc = os.path.join(gens, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc) as f:
                content = f.read()
            extras = []
            gio_vars = [
                ("giomoduledir", os.path.join(lib_dir, "gio", "modules")),
                ("glib_compile_resources", os.path.join(bin_dir, "glib-compile-resources")),
                ("glib_compile_schemas", os.path.join(bin_dir, "glib-compile-schemas")),
                ("gio_querymodules", os.path.join(bin_dir, "gio-querymodules")),
                ("gdbus_codegen", os.path.join(bin_dir, "gdbus-codegen")),
                ("schemasdir", os.path.join(share_dir, "glib-2.0", "schemas")),
            ]
            for var, path in gio_vars:
                if var + "=" not in content and (os.path.isfile(path) or os.path.isdir(path)):
                    extras.append("{}={}".format(var, path))
            # Also add -lintl if missing
            lines = content.splitlines(True)
            new_lines = []
            for line in lines:
                if line.startswith("Libs.private:") and "-lintl" not in line and os.path.isfile(os.path.join(lib_dir, "libintl.so")):
                    line = line.rstrip() + " -lintl\n"
                new_lines.append(line)
            content = "".join(new_lines)
            if extras:
                content = content.rstrip("\n") + "\n" + "\n".join(extras) + "\n"
            with open(gio_pc, "w") as f:
                f.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_glib_pc_files()
        self._patch_glib_pc_vars()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["iso-codes"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["nls"] = "disabled"
        tc.project_options["vorbis"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["ogg"] = "disabled"
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
        self.cpp_info.set_property("cmake_file_name", "GstPluginsBase")
        self.cpp_info.set_property("pkg_config_name", "gstreamer-plugins-base-1.0-unofficial")

        inc = ["include", "include/gstreamer-1.0"]

        # Core libraries
        gdp = self.cpp_info.components["gstreamer-pbutils-1.0"]
        gdp.set_property("pkg_config_name", "gstreamer-pbutils-1.0")
        gdp.set_property("cmake_target_name", "GstPluginsBase::gstreamer-pbutils-1.0")
        gdp.libs = ["gstpbutils-1.0"]
        gdp.includedirs = list(inc)
        gdp.requires = ["gstreamer::gstreamer-1.0", "gstreamer::gstreamer-base-1.0", "glib::glib-2.0"]

        alloc = self.cpp_info.components["gstreamer-allocators-1.0"]
        alloc.set_property("pkg_config_name", "gstreamer-allocators-1.0")
        alloc.set_property("cmake_target_name", "GstPluginsBase::gstreamer-allocators-1.0")
        alloc.libs = ["gstallocators-1.0"]
        alloc.includedirs = list(inc)
        alloc.requires = ["gstreamer::gstreamer-1.0"]

        app = self.cpp_info.components["gstreamer-app-1.0"]
        app.set_property("pkg_config_name", "gstreamer-app-1.0")
        app.set_property("cmake_target_name", "GstPluginsBase::gstreamer-app-1.0")
        app.libs = ["gstapp-1.0"]
        app.includedirs = list(inc)
        app.requires = ["gstreamer::gstreamer-1.0", "gstreamer::gstreamer-base-1.0"]

        audio = self.cpp_info.components["gstreamer-audio-1.0"]
        audio.set_property("pkg_config_name", "gstreamer-audio-1.0")
        audio.set_property("cmake_target_name", "GstPluginsBase::gstreamer-audio-1.0")
        audio.libs = ["gstaudio-1.0"]
        audio.includedirs = list(inc)
        audio.requires = ["gstreamer::gstreamer-1.0", "gstreamer::gstreamer-base-1.0"]

        video = self.cpp_info.components["gstreamer-video-1.0"]
        video.set_property("pkg_config_name", "gstreamer-video-1.0")
        video.set_property("cmake_target_name", "GstPluginsBase::gstreamer-video-1.0")
        video.libs = ["gstvideo-1.0"]
        video.includedirs = list(inc)
        video.requires = ["gstreamer::gstreamer-1.0", "gstreamer::gstreamer-base-1.0"]

        fft = self.cpp_info.components["gstreamer-fft-1.0"]
        fft.set_property("pkg_config_name", "gstreamer-fft-1.0")
        fft.set_property("cmake_target_name", "GstPluginsBase::gstreamer-fft-1.0")
        fft.libs = ["gstfft-1.0"]
        fft.includedirs = list(inc)
        fft.requires = ["gstreamer::gstreamer-1.0"]

        riff = self.cpp_info.components["gstreamer-riff-1.0"]
        riff.set_property("pkg_config_name", "gstreamer-riff-1.0")
        riff.set_property("cmake_target_name", "GstPluginsBase::gstreamer-riff-1.0")
        riff.libs = ["gstriff-1.0"]
        riff.includedirs = list(inc)
        riff.requires = ["gstreamer::gstreamer-1.0", "gstreamer-audio-1.0"]

        tag = self.cpp_info.components["gstreamer-tag-1.0"]
        tag.set_property("pkg_config_name", "gstreamer-tag-1.0")
        tag.set_property("cmake_target_name", "GstPluginsBase::gstreamer-tag-1.0")
        tag.libs = ["gsttag-1.0"]
        tag.includedirs = list(inc)
        tag.requires = ["gstreamer::gstreamer-1.0", "gstreamer::gstreamer-base-1.0"]

        sdp = self.cpp_info.components["gstreamer-sdp-1.0"]
        sdp.set_property("pkg_config_name", "gstreamer-sdp-1.0")
        sdp.set_property("cmake_target_name", "GstPluginsBase::gstreamer-sdp-1.0")
        sdp.libs = ["gstsdp-1.0"]
        sdp.includedirs = list(inc)
        sdp.requires = ["gstreamer::gstreamer-1.0", "gstreamer-riff-1.0"]

        rtsp = self.cpp_info.components["gstreamer-rtsp-1.0"]
        rtsp.set_property("pkg_config_name", "gstreamer-rtsp-1.0")
        rtsp.set_property("cmake_target_name", "GstPluginsBase::gstreamer-rtsp-1.0")
        rtsp.libs = ["gstrtsp-1.0"]
        rtsp.includedirs = list(inc)
        rtsp.requires = ["gstreamer::gstreamer-1.0", "gstreamer-sdp-1.0"]

        if not any(c.libs for c in self.cpp_info.components.values()):
            self.cpp_info.libs = collect_libs(self)

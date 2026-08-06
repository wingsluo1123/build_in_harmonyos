#!/usr/bin/env python3
"""Conan recipe — gstreamer 1.28.3 (meson)

Core GStreamer framework library. Provides libgstreamer-1.0.so,
libgstbase-1.0.so, libgstcontroller-1.0.so, libgstnet-1.0.so,
and the gst-inspect-1.0 / gst-launch-1.0 command-line tools.

Patch 0001: fix Python script execution on HMDFS (use python3 interpreter
instead of direct execution of glib-mkenums etc.).
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


class GstreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer — core framework for streaming media"
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
        # glib conan recipe provides some .pc files but not all variants
        # that downstream projects (gstreamer) expect
        gens = self.generators_folder

        # gmodule-no-export-2.0: same as gmodule-2.0 but without -Wl,--export-dynamic
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

        # gio-unix-2.0: platform-specific GIO headers, just requires gio-2.0
        gio_pc = os.path.join(gens, "gio-2.0.pc")
        gio_unix_pc = os.path.join(gens, "gio-unix-2.0.pc")
        if os.path.isfile(gio_pc) and not os.path.isfile(gio_unix_pc):
            text = open(gio_pc).read()
            # Extract version from gio-2.0.pc
            version = "2.84.0.1"
            for line in text.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break
            # Get includedir from the conan package
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
        # Add glib_mkenums variable and -lintl to glib-2.0.pc
        # glib conan recipe doesn't expose libintl in package_info,
        # so PkgConfigDeps omits -lintl from Libs line
        gens = self.generators_folder
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        glib_pkg = self.dependencies["glib"].package_folder
        mkenums = os.path.join(glib_pkg, "bin", "glib-mkenums")
        genmarshal = os.path.join(glib_pkg, "bin", "glib-genmarshal")
        compile_res = os.path.join(glib_pkg, "bin", "glib-compile-resources")
        libintl = os.path.join(glib_pkg, "lib", "libintl.so")
        with open(glib_pc) as f:
            content = f.read()
        lines = content.splitlines(True)
        new_lines = []
        for line in lines:
            # Add -lintl to Libs if missing
            if line.startswith("Libs:") and "-lintl" not in line and os.path.isfile(libintl):
                line = line.rstrip() + " -lintl\n"
            new_lines.append(line)
        content = "".join(new_lines)
        extras = []
        if "glib_mkenums=" not in content and os.path.isfile(mkenums):
            extras.append("glib_mkenums={}".format(mkenums))
        if "glib_genmarshal=" not in content and os.path.isfile(genmarshal):
            extras.append("glib_genmarshal={}".format(genmarshal))
        if "glib_compile_resources=" not in content and os.path.isfile(compile_res):
            extras.append("glib_compile_resources={}".format(compile_res))
        if extras:
            content = content.rstrip("\n") + "\n" + "\n".join(extras) + "\n"
        with open(glib_pc, "w") as f:
            f.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_glib_pc_files()
        self._patch_glib_pc_vars()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["nls"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["bash-completion"] = "disabled"
        tc.project_options["ptp-helper"] = "disabled"
        tc.project_options["gst_parse"] = "false"
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
        self.cpp_info.set_property("cmake_file_name", "GStreamer")
        self.cpp_info.set_property("pkg_config_name", "gstreamer-1.0-unofficial")

        inc = ["include", "include/gstreamer-1.0"]

        gstreamer = self.cpp_info.components["gstreamer-1.0"]
        gstreamer.set_property("pkg_config_name", "gstreamer-1.0")
        gstreamer.set_property("cmake_target_name", "GStreamer::gstreamer-1.0")
        gstreamer.libs = ["gstreamer-1.0"]
        gstreamer.includedirs = list(inc)
        gstreamer.requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            gstreamer.system_libs = ["m", "pthread", "dl", "rt"]

        base = self.cpp_info.components["gstreamer-base-1.0"]
        base.set_property("pkg_config_name", "gstreamer-base-1.0")
        base.set_property("cmake_target_name", "GStreamer::gstreamer-base-1.0")
        base.libs = ["gstbase-1.0"]
        base.includedirs = list(inc)
        base.requires = ["gstreamer-1.0"]

        controller = self.cpp_info.components["gstreamer-controller-1.0"]
        controller.set_property("pkg_config_name", "gstreamer-controller-1.0")
        controller.set_property("cmake_target_name", "GStreamer::gstreamer-controller-1.0")
        controller.libs = ["gstcontroller-1.0"]
        controller.includedirs = list(inc)
        controller.requires = ["gstreamer-1.0", "gstreamer-base-1.0"]

        net = self.cpp_info.components["gstreamer-net-1.0"]
        net.set_property("pkg_config_name", "gstreamer-net-1.0")
        net.set_property("cmake_target_name", "GStreamer::gstreamer-net-1.0")
        net.libs = ["gstnet-1.0"]
        net.includedirs = list(inc)
        net.requires = ["gstreamer-1.0", "gstreamer-base-1.0"]

        check = self.cpp_info.components["gstreamer-check-1.0"]
        check.set_property("pkg_config_name", "gstreamer-check-1.0")
        check.set_property("cmake_target_name", "GStreamer::gstreamer-check-1.0")
        check.libs = ["gstcheck-1.0"]
        check.includedirs = list(inc)
        check.requires = ["gstreamer-1.0", "gstreamer-base-1.0"]
        check.system_libs = ["pthread", "rt"]

        if not any(c.libs for c in self.cpp_info.components.values()):
            self.cpp_info.libs = collect_libs(self)

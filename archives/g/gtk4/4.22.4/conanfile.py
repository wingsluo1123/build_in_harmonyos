#!/usr/bin/env python3
"""Conan recipe — gtk4 4.22.4 (Meson).

GTK 4 (GIMP Toolkit 4) is a multi-platform GUI toolkit.
On OHOS, it uses the Broadway backend (HTML5/WebSocket remote rendering),
with X11/Wayland/Vulkan disabled.

Patch 0001 guards the epoxy/egl.h include in gdkdmabuf.c with #ifdef HAVE_EGL
because OHOS does not provide EGL.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Gtk4Conan(ConanFile):
    name = "gtk4"
    version = "4.22.4"
    description = "GTK 4 — multi-platform toolkit for creating graphical user interfaces"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org"
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

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("pango/1.56.4")
        self.requires("cairo/1.18.4")
        self.requires("harfbuzz/14.2.0.1")
        self.requires("fribidi/1.0.16")
        self.requires("gdk-pixbuf/2.44.6")
        self.requires("libepoxy/1.5.10")
        self.requires("fontconfig/2.18.1")
        self.requires("freetype/2.14.3")
        self.requires("graphene/1.10.8")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
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
            if (
                pkg_config
                and "\npkg-config =" not in content
                and "\npkgconfig =" not in content
            ):
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1
            )
            with open(nf, "w") as f:
                f.write(content)

    def _prepare_glib_build_tools(self):
        """Ensure glib build tools (glib-mkenums, glib-compile-resources) are
        available on PATH during meson build."""
        glib_bin = os.path.join(
            self.dependencies["glib"].package_folder, "bin"
        )
        tools_folder = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(tools_folder, exist_ok=True)

        for tool in ("glib-mkenums",):
            source = os.path.join(glib_bin, tool)
            if os.path.isfile(source):
                destination = os.path.join(tools_folder, tool)
                shutil.copyfile(source, destination)
                os.chmod(destination, 0o755)

        for tool in ("glib-compile-resources",):
            source = os.path.join(glib_bin, tool)
            if os.path.isfile(source):
                destination = os.path.join(tools_folder, tool)
                shutil.copyfile(source, destination)
                os.chmod(destination, 0o755)
        return tools_folder

    def _fix_glib_pc(self):
        """Add glib_mkenums variable to glib-2.0.pc so meson can find it."""
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc).read()
        if "glib_mkenums=" in text:
            return
        tools_folder = os.path.join(
            self.build_folder, "conan-native-tools"
        )
        glib_mkenums = os.path.join(tools_folder, "glib-mkenums")
        if not os.path.isfile(glib_mkenums):
            glib_mkenums = os.path.join(
                self.dependencies["glib"].package_folder, "bin", "glib-mkenums"
            )
        lines = text.splitlines(True)
        out = []
        injected = False
        for line in lines:
            out.append(line)
            if not injected and line.startswith("bindir="):
                out.append("glib_mkenums=%s\n" % glib_mkenums)
                injected = True
        if not injected:
            out.append(
                "glib_mkenums=${prefix}/bin/glib-mkenums\n"
            )
        open(pc, "w").write("".join(out))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._prepare_glib_build_tools()
        self._fix_glib_pc()

        # R33: use Conan Environment, not bare shell env vars
        env = Environment()
        tools_folder = os.path.join(
            self.build_folder, "conan-native-tools"
        )
        if os.path.isdir(tools_folder):
            env.prepend_path("PATH", tools_folder)
        glib_bin = os.path.join(
            self.dependencies["glib"].package_folder, "bin"
        )
        if os.path.isdir(glib_bin):
            env.prepend_path("PATH", glib_bin)
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script(
            "conanbuildenv_gtk4_tools"
        )

        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["wayland-backend"] = "false"
        tc.project_options["x11-backend"] = "false"
        tc.project_options["broadway-backend"] = "true"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["media-gstreamer"] = "disabled"
        tc.project_options["print-cups"] = "disabled"
        tc.project_options["print-cpdb"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["build-tests"] = "false"
        tc.project_options["build-testsuite"] = "false"
        tc.project_options["build-demos"] = "false"
        tc.project_options["build-examples"] = "false"
        tc.project_options["man-pages"] = "false"
        tc.project_options["documentation"] = "false"
        tc.project_options["colord"] = "disabled"
        tc.project_options["tracker"] = "disabled"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["cloudproviders"] = "disabled"
        tc.project_options["accesskit"] = "disabled"
        tc.project_options["f16c"] = "disabled"
        tc.project_options["screenshots"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # R32: sign shared libs on OHOS
        if self.settings.os in ("Linux", "OHOS") and self.options.shared:
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
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(
                0, os.path.join(os.path.dirname(cc), "llvm-objcopy")
            )
        objcopy = next(
            (p for p in candidates_objcopy if p and os.path.isfile(p)), None
        )
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skip OHOS codesign (cross/SDK env)"
            )
            return
        for so in sos:
            if objcopy:
                self.run(
                    '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                        oc=objcopy, f=so
                    )
                )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=so
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["gtk-4"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/gtk-4.0"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "GTK4")
        self.cpp_info.set_property("cmake_target_name", "GTK4::GTK4")
        self.cpp_info.set_property("pkg_config_name", "gtk-4.0")
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "pango::pango",
            "pango::pangocairo",
            "cairo::cairo",
            "harfbuzz::harfbuzz",
            "fribidi::fribidi",
            "gdk-pixbuf::gdk-pixbuf",
            "libepoxy::epoxy",
            "fontconfig::fontconfig",
            "freetype::freetype",
            "graphene-1.0::graphene-1.0",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

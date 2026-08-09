#!/usr/bin/env python3
"""Conan recipe — libadwaita 1.2.0 (Meson).

libadwaita provides building blocks for modern GNOME applications
using GTK4. It builds libadwaita-1.so and provides the
libadwaita-1 pkg-config.

On OHOS: introspection, tests, examples, vapi, and gtk_doc are disabled.
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


class LibadwaitaConan(ConanFile):
    name = "libadwaita"
    version = "1.2.0"
    description = "Building blocks for modern GNOME applications using GTK4"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libadwaita"
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
            "gtk4/4.22.4",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )

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
        """Ensure glib build tools are on PATH during meson build."""
        glib_bin = os.path.join(
            self.dependencies["glib"].package_folder, "bin"
        )
        if not os.path.isdir(glib_bin):
            return
        env = Environment()
        env.prepend_path("PATH", glib_bin)
        env.vars(self, scope="build").save_script(
            "conanbuildenv_libadwaita_tools"
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._prepare_glib_build_tools()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.generate()
        self._inject_meson_binaries()
        self._setup_lld_env()

    def _setup_lld_env(self):
        """Set LD_LIBRARY_PATH for OHOS SDK lld linker (needs libxml2.so.16)."""
        ce = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict) or {}
        cc = ce.get('c') or ''
        if not cc:
            return
        real_cc = os.path.realpath(cc)
        bindir = os.path.dirname(real_cc)
        for libdir in [os.path.join(bindir, 'lib'),
                       os.path.join(bindir, '..', 'lib')]:
            abspath = os.path.abspath(libdir)
            if os.path.isfile(os.path.join(abspath, 'libxml2.so.16')):
                env = Environment()
                env.prepend_path('LD_LIBRARY_PATH', abspath)
                env.vars(self, scope='build').save_script('conanbuildenv_lld')
                break

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

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
        self.cpp_info.libs = ["adwaita-1"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/libadwaita-1"]
        self.cpp_info.set_property("cmake_file_name", "libadwaita-1")
        self.cpp_info.set_property(
            "cmake_target_name", "libadwaita-1::libadwaita-1"
        )
        self.cpp_info.set_property("pkg_config_name", "libadwaita-1")
        self.cpp_info.requires = [
            "gtk4::gtk-4",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

#!/usr/bin/env python3
"""Conan recipe — zenity 4.2.2 (Meson).

Zenity is a tool that allows you to display GTK dialog boxes from
the command line. It is built with meson and links against libadwaita
and gtk4.

On OHOS: webkitgtk and manpage are disabled. The help subdirectory
(which requires itstool with libxml2 Python bindings) is made
conditional via patch 0001.
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


class ZenityConan(ConanFile):
    name = "zenity"
    version = "4.2.2"
    description = "Display GTK dialog boxes from the command line"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/zenity"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        self.requires(
            "libadwaita/1.2.0",
            transitive_headers=True,
            transitive_libs=True,
        )
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
        self.requires("pango/1.56.4")
        self.requires("cairo/1.18.4")

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
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script(
            "conanbuildenv_zenity_tools"
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._prepare_glib_build_tools()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["webkitgtk"] = "false"
        tc.project_options["manpage"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def _fix_lld_env(self):
        """Fix LD_LIBRARY_PATH for OHOS SDK lld linker (needs libxml2.so.16)."""
        ce = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict) or {}
        cc = ce.get('c') or ''
        if not cc:
            return
        bindir = os.path.dirname(cc)
        for libdir in [os.path.join(bindir, '..', 'lib'),
                      os.path.join(bindir, '..', '..', 'lib')]:
            abspath = os.path.abspath(libdir)
            if os.path.isfile(os.path.join(abspath, 'libxml2.so.16')):
                cur = os.environ.get('LD_LIBRARY_PATH', '')
                if abspath not in cur:
                    os.environ['LD_LIBRARY_PATH'] = abspath + (':' + cur if cur else '')
                break

    def build(self):
        apply_conandata_patches(self)
        self._fix_lld_env()
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        Meson(self).install()
        # R32: sign binary on OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _sign_binaries(self):
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern))
        if not candidates:
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
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            if objcopy:
                self.run(
                    '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                        oc=objcopy, f=binary
                    )
                )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=binary
                )
            )

    def package_info(self):
        # R38: command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

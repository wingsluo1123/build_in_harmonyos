#!/usr/bin/env python3
"""Conan recipe — qalculate-gtk 5.11.0 (Autotools).

qalculate-gtk is a GTK3-based GUI calculator front-end for libqalculate.
It builds two executables: qalculate-gtk and qalculate-search-provider.

Key design:
- libqalculate is referenced via Conan (R27: @ohpcd/stable)
- GUI deps (gtk3, glib, cairo, pango, etc.) are system-installed via cmd-pkgs
- System deps are discovered via PKG_CONFIG_PATH in generate()
- Autotools helper used (no self.run()) per quality rules
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class QalculateGtkConan(ConanFile):
    name = "qalculate-gtk"
    version = "5.11.0"
    description = "GTK3 GUI front-end for libqalculate (multi-purpose desktop calculator)"
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: dependency must use @ohpcd/stable
        self.requires("libqalculate/5.11.0@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try downloading from the URL in conandata.yml; if that fails
        # (e.g., network-restricted environment), fall back to a local copy.
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            local = os.path.expanduser("~/qalculate-gtk-5.11.0.tar.gz")
            if os.path.exists(local):
                get(self, "file://" + local,
                    sha256=self.conan_data["sources"]["sha256"],
                    strip_root=True)
            else:
                raise

    def generate(self):
        # R32: settings.os check must include OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception("Unsupported OS: {}".format(self.settings.os))

        tc = AutotoolsToolchain(self)
        # Only --prefix (R1: parameter minimization)
        # Force DT_RPATH (not DT_RUNPATH) for OHOS musl dynamic linker compatibility
        sys_lib = os.path.join(os.path.expanduser("~"), "usr/local/lib")
        sys_lib_ext = os.path.join(os.path.expanduser("~"), "usr/local/lib/external")
        tc.extra_ldflags.append(f"-Wl,--disable-new-dtags")
        tc.extra_ldflags.append(f"-Wl,-rpath,{sys_lib}")
        tc.extra_ldflags.append(f"-Wl,-rpath,{sys_lib_ext}")
        # PKG_CONFIG_PATH, CONFIG_SHELL, SHELL set via Environment below
        tc.generate()

        # Set environment variables for system GUI dependencies
        env = Environment()
        env.define("PKG_CONFIG_PATH", os.path.join(os.path.expanduser("~"), "usr/local/lib/pkgconfig"))
        env.define("CONFIG_SHELL", "/usr/bin/sh")
        env.define("SHELL", "/usr/bin/sh")
        env.define("LD_LIBRARY_PATH", os.path.join(os.path.expanduser("~"), "usr/local/lib") + ":" + os.path.join(os.path.expanduser("~"), "usr/local/lib/external"))
        envvars = env.vars(self)
        envvars.save_script("env_qalculate_gtk")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # qalculate-gtk is an executable package, not a library
        self.cpp_info.libs = []
        # libqalculate is a transitive dependency for consumers
        self.cpp_info.requires = ["libqalculate::libqalculate"]
        # GUI system dependencies (pre-installed via cmd-pkgs)
        self.cpp_info.system_libs = [
            "gtk-3", "gdk-3", "pangocairo-1.0", "pango-1.0",
            "harfbuzz", "atk-1.0", "cairo-gobject", "cairo",
            "gio-2.0", "gdk_pixbuf-2.0", "gobject-2.0", "glib-2.0",
            "gmodule-2.0", "intl", "pcre2-8", "ffi",
            "epoxy", "fontconfig", "freetype", "pixman-1",
            "png16", "fribidi", "xml2", "mpfr", "gmp",
            "z", "pthread", "m"
        ]

#!/usr/bin/env python3
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class WvConan(ConanFile):
    name = "wv"
    version = "1.2.9"
    package_type = "static-library"
    license = "GPL-2.0-or-later"
    homepage = "https://wvware.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Library and command-line tools for reading Microsoft Word documents"
    topics = ("word", "document", "parser")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*.patch"

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("wv/1.2.9 is adapted for OHOS only")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "shared=True is unsupported because the published zlib dependency is not PIC"
            )

    def requirements(self):
        self.requires("libgsf/1.14.53")
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")
        self.requires("gettext/0.22.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-libwmf",
            "--disable-shared",
            "--enable-static",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

    def _dependency_link_flags(self):
        clean_libs = os.path.join(self.build_folder, "clean-libs")
        os.makedirs(clean_libs, exist_ok=True)
        preferred = {
            "libgsf": ("libgsf-1.so.114.0.53",),
            "glib": ("libglib-2.0.a", "libgobject-2.0.a", "libgio-2.0.a",
                     "libgmodule-2.0.a", "libgthread-2.0.a"),
            "libffi": ("libffi.a",),
            "pcre2": ("libpcre2-8.a", "libpcre2-posix.a"),
            "libxml2": ("libxml2.so.16.1.3",),
            "zlib": ("libz.a",),
            "gettext": ("libintl.a",),
        }
        for dependency in self.dependencies.host.values():
            patterns = preferred.get(dependency.ref.name, ())
            for pattern in patterns:
                matches = sorted(glob.glob(os.path.join(dependency.package_folder, "lib", pattern)))
                if matches:
                    copy(self, os.path.basename(matches[-1]),
                         src=os.path.dirname(matches[-1]), dst=clean_libs)

        return " ".join([
            "-L{}".format(clean_libs), "-l:libgsf-1.so.114.0.53", "-lglib-2.0", "-lgobject-2.0",
            "-lgio-2.0", "-lgmodule-2.0", "-lgthread-2.0", "-lffi",
            "-lpcre2-8", "-lpcre2-posix", "-l:libxml2.so.16.1.3", "-lz", "-lintl",
            "-lm", "-lpthread", "-lrt", "-ldl",
        ])

    def build(self):
        apply_conandata_patches(self)
        env = Environment()
        env.define("DEPS_LIBS", self._dependency_link_flags())
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["wv"]
        self.cpp_info.includedirs = ["include/wv"]
        self.cpp_info.set_property("pkg_config_name", "wv-1.0")
        self.cpp_info.requires = [
            "libgsf::libgsf",
            "glib::glib",
            "libxml2::libxml2",
            "zlib::zlib",
            "gettext::gettext",
        ]

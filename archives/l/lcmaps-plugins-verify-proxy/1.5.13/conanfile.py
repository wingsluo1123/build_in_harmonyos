#!/usr/bin/env python3
"""Conan recipe for the LCMAPS verify-proxy plugin and verify-proxy-tool."""

import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcmapsPluginsVerifyProxyConan(ConanFile):
    name = "lcmaps-plugins-verify-proxy"
    version = "1.5.13"
    description = "LCMAPS proxy-chain verification plugin and verify-proxy-tool"
    license = "Apache-2.0"
    homepage = "https://github.com/Nikhef-lcaae/lcmaps"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lcmaps/1.6.7")
        self.requires("openssl/3.5.6.1.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _abs_dirs(cpp_info, kind):
        dirs = []
        pkg = getattr(cpp_info, "package_folder", None)
        for directory in getattr(cpp_info, kind, []) or []:
            dirs.append(directory if os.path.isabs(directory) or not pkg else os.path.join(pkg, directory))
        for component in (getattr(cpp_info, "components", None) or {}).values():
            for directory in getattr(component, kind, []) or []:
                dirs.append(directory if os.path.isabs(directory) or not pkg else os.path.join(pkg, directory))
        return dirs

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        lcmaps_pkg = self.dependencies["lcmaps"].package_folder
        toolchain.configure_args.append("--with-lcmaps-prefix=%s" % lcmaps_pkg)

        env = toolchain.environment()
        env.unset("C_INCLUDE_PATH")
        env.unset("CPLUS_INCLUDE_PATH")
        env.unset("LIBRARY_PATH")

        includes = []
        libdirs = []
        for _, dependency in self.dependencies.host.items():
            if not getattr(dependency, "package_folder", None):
                continue
            includes.extend(self._abs_dirs(dependency.cpp_info, "includedirs"))
            libdirs.extend(self._abs_dirs(dependency.cpp_info, "libdirs"))

        if includes:
            env.append("CPPFLAGS", " ".join("-I%s" % directory for directory in dict.fromkeys(includes)))

        env.append_path("PKG_CONFIG_PATH", os.path.join(lcmaps_pkg, "lib", "pkgconfig"))

        link_dirs = []
        for directory in dict.fromkeys(libdirs):
            link_dirs.extend(["-L%s" % directory, "-Wl,-rpath-link,%s" % directory])
        if link_dirs:
            env.append("LDFLAGS", " ".join(link_dirs))

        # OHOS resolves undefined symbols of a dlopen()ed DSO only through
        # its own DT_NEEDED closure, so make both runtime dependencies explicit.
        env.append(
            "LDFLAGS",
            "-Wl,--as-needed -llcmaps_without_gsi -lcrypto -Wl,--no-as-needed",
        )
        toolchain.generate(env=env)

    def _remove_broken_libtool_wrappers(self):
        for _, dependency in self.dependencies.host.items():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in self._abs_dirs(dependency.cpp_info, "libdirs"):
                for wrapper in glob.glob(os.path.join(libdir, "*.la")):
                    try:
                        with open(wrapper, "r", encoding="utf-8", errors="ignore") as handle:
                            text = handle.read()
                    except OSError:
                        continue
                    if "//lib" in text:
                        self.output.info("Removing broken libtool wrapper: %s" % wrapper)
                        os.remove(wrapper)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        self._remove_broken_libtool_wrappers()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

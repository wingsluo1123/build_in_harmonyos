#!/usr/bin/env python3
"""Conan recipe for Icecast 2.4.4-r14."""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class IcecastConan(ConanFile):
    name = "icecast"
    version = "2.4.4-r14"
    description = "Streaming media server for Ogg and other formats"
    license = "GPL-2.0-only"
    homepage = "https://icecast.org"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Icecast requires POSIX sockets and threads")

    def requirements(self):
        self.requires("curl/8.15.0")
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45")
        self.requires("openssl/3.5.6")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        libxml2 = self.dependencies["libxml2"].package_folder
        libxslt = self.dependencies["libxslt"].package_folder
        xslt_config = os.path.join(self.build_folder, "xslt-config-conan")
        save(
            self,
            xslt_config,
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            f"  --cflags) echo \"-I{libxslt}/include -I{libxml2}/include/libxml2\" ;;\n"
            f"  --libs) echo \"-L{libxslt}/lib -lxslt -lexslt -L{libxml2}/lib -lxml2\" ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n",
        )
        os.chmod(xslt_config, os.stat(xslt_config).st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--host=aarch64-unknown-linux-gnu",
                "--disable-shared",
                "--enable-static",
                "--disable-yp",
                "--without-theora",
                "--without-speex",
                f"--with-xslt-config={xslt_config}",
            ]
        )
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

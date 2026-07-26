#!/usr/bin/env python3
"""Conan recipe for Icecast 2.4.4.

Builds the static streaming server for Linux and OHOS targets.
"""
import os
import shlex
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class IcecastConan(ConanFile):
    name = "icecast"
    version = "2.4.4"
    description = "Streaming media server for Ogg and other formats"
    license = "GPL-2.0-only"
    homepage = "https://icecast.org"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Icecast requires POSIX sockets and threads")

    def requirements(self):
        self.requires("libogg/1.3.5")
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
        if self.settings.os == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-yp",
                "--with-curl=no",
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
        self._build_upstream_tests()

    def _build_upstream_tests(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = shlex.quote(compilers.get("c", "cc"))
        source = self.source_folder
        build = self.build_folder
        avl_test = os.path.join(build, "upstream-avl-test")
        log_test = os.path.join(build, "upstream-log-test")

        self.run(
            f"{cc} -std=gnu11 -DNO_THREAD "
            f"-I{shlex.quote(os.path.join(source, 'src'))} "
            f"{shlex.quote(os.path.join(source, 'src', 'avl', 'test.c'))} "
            f"{shlex.quote(os.path.join(source, 'src', 'avl', 'avl.c'))} "
            f"-o {shlex.quote(avl_test)}"
        )
        self.run(
            f"{cc} -std=gnu11 -DHAVE_CONFIG_H "
            f"-I{shlex.quote(build)} "
            f"-I{shlex.quote(os.path.join(source, 'src', 'log'))} "
            f"{shlex.quote(os.path.join(source, 'src', 'log', 'test.c'))} "
            f"{shlex.quote(os.path.join(source, 'src', 'log', 'log.c'))} "
            f"-pthread -o {shlex.quote(log_test)}"
        )

        if can_run(self):
            self.run(f"{shlex.quote(avl_test)} 25")
            self.run(shlex.quote(log_test))

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

#!/usr/bin/env python3
"""Conan recipe — libsrtp 2.8.0 (Autotools)

Cisco libsrtp — Secure Real-time Transport Protocol (SRTP) library.
"""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SrtpConan(ConanFile):
    name = "srtp"
    version = "2.8.0"
    description = "Cisco libsrtp — Secure Real-time Transport Protocol (SRTP) library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cisco/libsrtp"
    url = "https://github.com/cisco/libsrtp"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        import tarfile
        from conan.tools.files import download
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        tgz = "src.tar.gz"
        download(self, url, tgz, sha256=sha256)
        with tarfile.open(tgz, "r:gz") as tar:
            # Strip root directory
            members = tar.getmembers()
            root = members[0].name.split("/")[0] + "/"
            for m in members:
                m.name = m.name[len(root):] if m.name.startswith(root) else m.name
                if m.name:
                    tar.extract(m)
        import os
        os.unlink(tgz)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix shebang for HarmonyOS: /bin/bash -> /data/service/hnp/bin/bash
        import glob as g
        src = self.source_folder
        for f in [f"{src}/configure"] + g.glob(f"{src}/**/*.sh", recursive=True):
            try:
                with open(f, "r") as fh:
                    content = fh.read()
                content = content.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
                content = content.replace("#!/bin/sh", "#!/system/bin/sh")
                with open(f, "w") as fh:
                    fh.write(content)
            except Exception as e:
                self.output.warning(f"Failed to fix shebang in {f}: {e}")
        # Fix mktemp compatibility: HarmonyOS mktemp doesn't support XXXXXX template
        cfg = f"{src}/configure"
        with open(cfg, "r") as fh:
            c = fh.read()
        c = c.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp=`(umask 077 && d="./conf.$$" && mkdir "$d" && echo "$d") 2>/dev/null` &&')
        with open(cfg, "w") as fh:
            fh.write(c)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["srtp2"]

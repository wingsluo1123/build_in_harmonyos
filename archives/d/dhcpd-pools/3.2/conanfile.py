#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class DhcpdpoolsConan(ConanFile):
    name = "dhcpd-pools"
    version = "3.2"
    description = ("dhcpd-pools is a ISC dhcpd lease analysis tool that "
                   "parses dhcpd.conf and dhcpd.leases to produce pool "
                   "usage statistics")
    license = "BSD-2-Clause"
    homepage = "http://dhcpd-pools.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("uthash/2.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS: config.guess cannot detect the system type, specify explicitly
        tc.configure_args.append("--build=aarch64-linux-gnu")
        # Point --with-uthash to the Conan dependency include path
        uthash = self.dependencies["uthash"]
        uthash_include = os.path.join(uthash.package_folder, "include")
        tc.configure_args.append(f"--with-uthash={uthash_include}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # OHOS HMDFS workaround: configure's config.status cannot create temp dirs
        # in the build directory. Patch the configure script in the source folder
        # before running it to use a static temp directory instead of random ./confXXXXXX.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path) as f:
                content = f.read()
            import re
            # Replace mktemp/mkdir tmp dir creation with a static dir
            content = re.sub(
                r'tmp=`\(umask 077 \&\& mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
                'tmp=./conftmp',
                content
            )
            content = re.sub(
                r'tmp=\./conf\$\$-\$RANDOM\n[^\n]*\(umask 077 \&\& mkdir "\$tmp"\)',
                'tmp=./conftmp\n  mkdir -p "$tmp"',
                content
            )
            with open(configure_path, "w") as f:
                f.write(content)
        # Ensure the temp dir exists in the build folder before configure runs
        os.makedirs(os.path.join(self.build_folder, "conftmp"), exist_ok=True)
        # Now run configure and make normally
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []

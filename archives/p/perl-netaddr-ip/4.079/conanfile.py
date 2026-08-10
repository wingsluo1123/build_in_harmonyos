#!/usr/bin/env python3
"""Conan recipe — perl-netaddr-ip 4.079 (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get

class PerlNetaddrIp(ConanFile):
    name = "perl-netaddr-ip"
    version = "4.079"
    description = "perl-netaddr-ip 4.079"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/netaddr::ip"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):

        src = self.source_folder
        self.run("perl Makefile.PL", cwd=src)
        # HarmonyOS: generate config.h for NetAddr::IP::Util (configure script unavailable)
        if self.settings.os == "OHOS":
            util_dir = os.path.join(src, "Lite", "Util")
            config_h_in = os.path.join(util_dir, "config.h.in")
            config_h = os.path.join(util_dir, "config.h")
            if os.path.exists(config_h_in) and not os.path.exists(config_h):
                shutil.copy2(config_h_in, config_h)
            localperl_h = os.path.join(util_dir, "localperl.h")
            if not os.path.exists(localperl_h):
                with open(localperl_h, "w") as f:
                    f.write("/* Auto-generated for OHOS */\n")
            makefile = os.path.join(src, "Makefile")
            if os.path.exists(makefile):
                with open(makefile, "r") as mf:
                    content = mf.read()
                if "-nostartfiles" not in content:
                    content = content.replace("LDDLFLAGS =", "LDDLFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc")
                with open(makefile, "w") as mf:
                    mf.write(content)
        self.run("make -j1", cwd=src)

    def package(self):
        dest = self.package_folder
        src = self.source_folder
        self.run("make install DESTDIR=" + dest, cwd=src)

        for root, dirs, files in os.walk(dest):
            for fn in files:
                if fn.endswith(".so"):
                    lib_dir = os.path.join(dest, "lib")
                    os.makedirs(lib_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), lib_dir)

    def package_info(self):
        # The shared library is Util.so (Perl XS extension)
        self.cpp_info.libs = ["Util"]
        self.cpp_info.libdirs = ["lib"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []

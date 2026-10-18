import os
import shlex
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

class RNAhybridConan(ConanFile):
    name = "rnahybrid"
    version = "2.1.2"
    description = "RNA hybridisation, calibration and effective target statistics"
    homepage = "https://bibiserv.cebitec.uni-bielefeld.de/rnahybrid/"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        shell = os.environ.get("CONFIG_SHELL", "sh")
        args = [shell, os.path.join(self.source_folder, "configure"), "--prefix=/", "CC="+cc,
                "CFLAGS=-O2 -fPIE -fcommon", "LDFLAGS=-pie -Wl,-z,relro,-z,now", "ac_cv_lib_g2_g2_open_vd=no", "ac_cv_lib_gd_gdImageLine=no"]
        self.run(shlex.join(args), env="conanbuild")
        self.run("make -j1", env="conanbuild")
        self.run("timeout 60 make -j1 check", env="conanbuild")
        self.output.info('HMBS_UPSTREAM_TEST_RESULT={"status":"skipped","reason":"No TESTS or check_PROGRAMS in release; make check is empty","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}')

    def package(self):
        # This release's install-sh supports only one input file, while its
        # generated Makefile passes all three programs at once and silently
        # installs only the first. Install the complete explicit inventory.
        for name in ("RNAhybrid", "RNAcalibrate", "RNAeffective"):
            src = os.path.join(self.build_folder, "src")
            if not os.path.isfile(os.path.join(src, name)):
                raise ConanException("Missing built executable: "+name)
            copy(self, name, src, os.path.join(self.package_folder, "bin"))
            copy(self, name+".1", os.path.join(self.source_folder, "man"), os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*", os.path.join(self.source_folder, "examples"), os.path.join(self.package_folder, "share", "rnahybrid", "examples"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

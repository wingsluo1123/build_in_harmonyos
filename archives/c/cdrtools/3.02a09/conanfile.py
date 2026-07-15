import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


class CdrtoolsConan(ConanFile):
    name = "cdrtools"
    version = "3.02a09"
    description = "CD/DVD/BD recording tools (cdrecord, mkisofs, cdda2wav, readcd)"
    license = "CDDL-1.0"
    homepage = "https://sourceforge.net/projects/cdrtools/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # cdrtools uses Schily makefilesystem, not autotools configure
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            os.remove(configure_path)

        # Skip avoffset.mk to avoid running the avoffset binary which hangs on HarmonyOS
        # The avoffset.h is already provided by patch 0005
        makefile_path = os.path.join(self.source_folder, "inc", "Makefile")
        replace_in_file(self, makefile_path,
                        "MK_FILES= align_test.mk avoffset.mk",
                        "MK_FILES= align_test.mk")

        # Touch avoffset.h to prevent make from regenerating it
        avoffset_h = os.path.join(self.source_folder, "incs", "aarch64-linux-clang", "avoffset.h")
        if os.path.exists(avoffset_h):
            os.utime(avoffset_h, None)

        # R33: Get compiler from Conan conf, set as env vars for Schily makefilesystem
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx

        # R9: Use -j1, never -j$(nproc)
        # Schily makefilesystem uses GMAKE_NOWARN=true to suppress GNU make warnings
        # INS_BASE=/ installs to DESTDIR/bin instead of DESTDIR/opt/schily/bin
        self.run("make GMAKE_NOWARN=true INS_BASE=/ -j1", cwd=self.source_folder)

    def package(self):
        # Install using Schily make install with DESTDIR
        # INS_BASE=/ puts binaries in bin/ at the package root
        self.run(f"make install GMAKE_NOWARN=true INS_BASE=/ DESTDIR={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]

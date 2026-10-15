#!/usr/bin/env python3
"""Conan 2 recipe for yamcha 0.33 on HarmonyOS PC."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class YamchaConan(ConanFile):
    name = "yamcha"
    version = "0.33"
    description = "Yet Another Multipurpose CHunk Annotator: supervised chunking trainer and tagger"
    license = "LGPL-2.1-or-later"
    homepage = "http://chasen.org/~taku/software/yamcha/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yamcha is supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # configure hard-requires svm_learn (AC_PATH_PROGS + AC_MSG_ERROR)
        # and make check trains with it; tinysvm provides bin/svm_learn.
        # run=True puts tinysvm's bin on the build-env PATH so configure
        # and make check can find svm_learn, while tinysvm also stays a
        # runtime dependency of the installed training pipeline.
        self.requires("tinysvm/0.09", run=True)

    def layout(self):
        # This 2005-era autotools tree assumes srcdir == builddir
        # (libexec/Makefile.am hardcodes the relative include -I../src),
        # so the build must be in-source, matching upstream and the
        # verified host build. basic_layout's out-of-source folder breaks
        # that relative include on both the CI worker and local builds.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(self.folders.build, "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Install directly into the package folder (libtool honors the last
        # --prefix), matching the upstream --prefix layout.
        tc.configure_args.append(f"--prefix={self.package_folder}")
        tc.generate()
        buildenv = VirtualBuildEnv(self)
        # Configure and make check need svm_learn on PATH; host-context
        # requires do not contribute bindirs to the build env, so expose
        # tinysvm's bin explicitly (prepend keeps the system PATH).
        if "tinysvm" in self.dependencies:
            dep = self.dependencies["tinysvm"]
            if dep.package_folder:
                buildenv.environment().prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin"))
        buildenv.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Autotools passes --build/--host from the toolchain, so local
        # cross builds (build=darwin, host=linux-ohos) and the native
        # OHOS CI worker (build==host) both configure correctly.
        autotools.configure()
        jobs = 1 if str(self.settings.os) == "OHOS" else (os.cpu_count() or 1)
        autotools.make(args=[f"-j{jobs}"])
        if can_run(self):
            # Upstream inventory: tests/test1.sh through test4.sh, all mandatory.
            self.run("make check", env="conanbuild")
        else:
            self.output.warning("cross-build: four upstream training tests were skipped")

    def package(self):
        # --prefix is already the package folder; install without DESTDIR
        # to avoid double nesting.
        self.run("make install", env="conanbuild")
        for libtool_archive in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(libtool_archive)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "yamcha")
        self.cpp_info.set_property("cmake_target_name", "yamcha::yamcha")
        self.cpp_info.set_property("pkg_config_name", "yamcha")
        self.cpp_info.libs = ["yamcha"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]

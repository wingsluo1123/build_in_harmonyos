import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, load, replace_in_file, unzip


class QuorumConan(ConanFile):
    name = "quorum"
    version = "1.1.2"
    description = "Quality-aware DNA read error correction with Jellyfish"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gmarcais/Quorum"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "config.h.cmake", "gzip_stream.hpp"

    def export_sources(self):
        for filename in self.exports_sources:
            copy(self, filename, src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # The published mixed CLI/library package is typed application.
        # Request its real headers/library explicitly, not only its bin path.
        self.requires("jellyfish/2.3.1", headers=True, libs=True)
        self.requires("zlib/1.3.2.1")
        self.requires("perl/5.42.2")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.quorum:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        if self.export_sources_folder != self.source_folder:
            for leaf in ("CMakeLists.txt", "config.h.cmake"):
                copy(self, leaf, self.export_sources_folder, self.source_folder)
        # Replace a GNU libstdc++ private stream with real zlib output.
        copy(self, "gzip_stream.hpp", self.export_sources_folder,
             os.path.join(self.source_folder, "include"))
        unit = os.path.join(self.source_folder, "unit_tests", "test_mer_database.cc")
        original = load(self, unit)
        if len(re.findall(r"\bTEST_P\(", original)) != 1 or "::testing::Values(1, 10, 20, 40)" not in original:
            raise ConanInvalidConfiguration("Upstream four-instance inventory changed")
        replace_in_file(self, unit, "INSTANTIATE_TEST_CASE_P(", "INSTANTIATE_TEST_SUITE_P(")
        # The documented -p prefix and -P paired-files are distinct switches.
        # Getopt::Long's default case folding otherwise aliases them.
        replace_in_file(self, os.path.join(self.source_folder, "src", "quorum.in"),
                        "use Getopt::Long;", "use Getopt::Long qw(:config no_ignore_case);")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["CMAKE_SKIP_RPATH"] = True
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        if can_run(self):
            perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
            self.run(shlex.quote(perl) + " -MGetopt::Long -MFile::Basename -e 'print qq(PERL_FRONTEND_MODULES_PASS\\n)'",
                     env=["conanbuild", "conanrun"])
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            unit = os.path.join(self.build_folder, "all_tests")
            self.run(shlex.quote(unit) + " --gtest_list_tests", env=["conanbuild", "conanrun"])
            self.run(shlex.quote(unit), env=["conanbuild", "conanrun"])
            self.output.info("QUORUM_UPSTREAM_RESULT=4/4")

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

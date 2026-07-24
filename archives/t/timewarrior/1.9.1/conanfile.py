#!/usr/bin/env python3
"""Conan recipe for Timewarrior 1.9.1."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)


class TimewarriorConan(ConanFile):
    name = "timewarrior"
    version = "1.9.1"
    description = "Command-line time tracking application"
    license = "MIT"
    homepage = "https://timewarrior.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Timewarrior supports Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "cmake", "CXXSniffer.cmake"),
            '${CMAKE_SYSTEM_NAME} MATCHES "Linux"',
            '${CMAKE_SYSTEM_NAME} MATCHES "Linux|OHOS|HarmonyOS"',
        )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_source = os.path.join(self.source_folder, "test")
            test_build = os.path.join(self.build_folder, "test")
            copy(self, "*.t", src=test_source, dst=test_build)
            for directory in ("basetest", "simpletap", "test_extensions"):
                copy(
                    self,
                    "*",
                    src=os.path.join(test_source, directory),
                    dst=os.path.join(test_build, directory),
                )
            for helper in (
                "bash_tap.sh",
                "bash_tap_ti.sh",
                "timemachine",
            ):
                copy(self, helper, src=test_source, dst=test_build)
            copy(self, "run_all", src=test_source, dst=test_build)
            if not os.path.isfile(os.path.join(test_build, "run_all")):
                raise ConanInvalidConfiguration("Missing upstream test runner: run_all")
            copy(
                self,
                "totals.py",
                src=os.path.join(self.source_folder, "ext"),
                dst=test_build,
            )
            shim_dir = os.path.join(test_build, "test-bin")
            os.makedirs(shim_dir, exist_ok=True)
            man_shim = os.path.join(shim_dir, "man")
            save(
                self,
                man_shim,
                "#!/bin/sh\n"
                "name=\"$1\"\n"
                "old_ifs=$IFS\n"
                "IFS=:\n"
                "for directory in ${MANPATH:-}; do\n"
                "  for section in 1 5 7; do\n"
                "    for page in \"$directory/$name.$section\" \"$directory/man$section/$name.$section\"; do\n"
                "      if [ -f \"$page\" ]; then cat \"$page\"; exit 0; fi\n"
                "    done\n"
                "  done\n"
                "done\n"
                "IFS=$old_ifs\n"
                "echo \"No manual entry for $name\" >&2\n"
                "exit 1\n",
            )
            os.chmod(man_shim, 0o755)
            test_env = Environment()
            test_env.prepend_path("PATH", shim_dir)
            with test_env.vars(self).apply():
                self.run("chmod +x *.t run_all", cwd=test_build)
                cmake.build(target="test")
                self.run("./AtomicFileTest", cwd=test_build)

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

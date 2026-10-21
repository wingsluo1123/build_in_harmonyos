#!/usr/bin/env python3
"""Package official Python sources, licenses, CLI and real tests."""
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PcppConan(ConanFile):
    name = "pcpp"
    version = "1.30"
    description = "pcpp Python tool and module"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ned14/pcpp"
    settings = "os", "arch", "compiler", "build_type"
    # Runtime Python module, neither an executable nor a C/C++ library.
    # Leave Conan's C/C++ package_type inference unspecified.

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "launcher.py", self.recipe_folder, self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["ply"], strip_root=True, destination=os.path.join(self.source_folder, "pcpp", "ply"))
        apply_conandata_patches(self)

    def build(self):
        # The official version tag includes all 71 unittest methods and fixtures.
        # subprocess argv avoids shell-specific quoting and returns real status.
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys, unittest; "
             "suite=unittest.defaultTestLoader.discover('tests', pattern='*.py'); "
             "count=suite.countTestCases(); "
             "print('UPSTREAM_DISCOVERED=%d' % count); "
             "result=unittest.TextTestRunner(verbosity=2).run(suite); "
             "sys.exit(0 if count == 71 and result.testsRun == 71 "
             "and not result.skipped and result.wasSuccessful() else 1)"],
            cwd=self.source_folder, check=False)
        if result.returncode:
            raise ConanException("Upstream unittest suite failed")

    def package(self):
        copy(self, "*.py", os.path.join(self.source_folder, "pcpp"),
             os.path.join(self.package_folder, "site-packages", "pcpp"))
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        # PLY carries its complete BSD notice at the start of README.md.
        copy(self, "README.md", os.path.join(self.source_folder, "pcpp", "ply"),
             os.path.join(self.package_folder, "licenses", "ply"))

        target = os.path.join(self.package_folder, "bin")
        copy(self, "launcher.py", self.source_folder, target)
        launcher = os.path.join(target, "pcpp")
        os.rename(os.path.join(target, "launcher.py"), launcher)
        os.chmod(launcher, 0o755)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PYTHONPATH",
                                     os.path.join(self.package_folder, "site-packages"))

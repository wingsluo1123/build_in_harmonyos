import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class MeteocalcConan(ConanFile):
    name = "meteocalc"
    version = "1.1.0"
    description = "Pure Python meteorological temperature calculations"
    license = "MIT"
    homepage = "https://github.com/malexer/meteocalc"
    settings = "os", "arch", "compiler", "build_type"
    # Runtime Python module, neither an executable nor a C/C++ library.
    # Leave Conan's C/C++ package_type inference unspecified.

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # The official version tag includes all 35 unittest methods and fixtures.
        # subprocess argv avoids shell-specific quoting and returns real status.
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys, unittest; "
             "suite=unittest.defaultTestLoader.discover('tests'); "
             "count=suite.countTestCases(); "
             "print('UPSTREAM_DISCOVERED=%d' % count); "
             "result=unittest.TextTestRunner(verbosity=2).run(suite); "
             "sys.exit(0 if count == 35 and result.testsRun == 35 "
             "and not result.skipped and result.wasSuccessful() else 1)"],
            cwd=self.source_folder, check=False)
        if result.returncode:
            raise ConanException("Upstream unittest suite failed")

    def package(self):
        copy(self, "*.py", os.path.join(self.source_folder, "meteocalc"),
             os.path.join(self.package_folder, "site-packages", "meteocalc"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH",
                                     os.path.join(self.package_folder, "site-packages"))

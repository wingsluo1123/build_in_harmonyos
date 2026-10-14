import os

from conan import ConanFile
from conan.tools.build import cross_building


class RaidtestTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The raidtest binary only runs on the target OS; the test suite is
        # executed there (device shadow CI / native host), not on Windows.
        if not cross_building(self):
            dep = self.dependencies["raidtest"]
            bindir = dep.cpp_info.bindirs[0]
            if not os.path.isabs(bindir):
                bindir = os.path.join(dep.cpp_info.rootpath, bindir)
            # Pass the bindir as an explicit argument: runenv-based handover
            # proved unreliable on the device runner (CONAN_TEST_PACKAGE_BIN
            # did not reach the script), an argv is deterministic.
            self.run('sh "%s" "%s"'
                     % (os.path.join(self.source_folder, "test.sh"), bindir))

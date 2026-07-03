import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libgit2TestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: use bash to run binary (mksh cannot execute ELF)
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.exists(bash):
            for candidate in ["/data/service/hnp/bin/bash",
                              "/storage/Users/currentUser/usr/local/bin/bash",
                              "/usr/bin/bash", "/bin/bash"]:
                if os.path.exists(candidate):
                    bash = candidate
                    break
        if bash:
            self.run(f"{bash} -c './test_package'", env="conanrun")
        else:
            self.run("./test_package", env="conanrun")

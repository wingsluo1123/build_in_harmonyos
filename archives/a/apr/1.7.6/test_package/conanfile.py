import os
from conan import ConanFile
from conan.tools.build import cross_building


class AprTestConan(ConanFile):
    """test_package for apr — calls apr_initialize() and prints apr_version_string()."""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["apr"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            root = _d.package_folder
            for p in _d.cpp_info.includedirs:
                abs_path = os.path.join(root, str(p)) if not os.path.isabs(str(p)) else str(p)
                incs.append("-I" + abs_path)
        inc = " ".join(incs)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            root = _d.package_folder
            for p in _d.cpp_info.libdirs:
                abs_path = os.path.join(root, str(p)) if not os.path.isabs(str(p)) else str(p)
                libdirs.append(abs_path)
        link = " ".join(
            ["-L" + p for p in libdirs]
            + ["-l" + l for l in dep.libs]
            + ["-Wl,-rpath," + p for p in libdirs]
        )
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_package.c -o test_package {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verify compile+link")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_package'", env="conanrun")

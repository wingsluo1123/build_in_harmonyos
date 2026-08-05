import os
from conan import ConanFile
from conan.tools.build import cross_building


class AprUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Ensure compiler is on PATH (CI worker may not have clang in PATH)
        for p in ["/data/service/hnp/bin", os.path.expanduser("~/usr/local/bin")]:
            if os.path.isdir(p):
                os.environ["PATH"] = p + ":" + os.environ.get("PATH", "")

        dep = self.dependencies["apr-util"].cpp_info
        incs = []
        libdirs = []
        libs = dep.libs[:]
        for _ref, _d in self.dependencies.items():
            root = _d.package_folder
            for p in _d.cpp_info.includedirs:
                abs_path = os.path.join(root, str(p)) if not os.path.isabs(str(p)) else str(p)
                incs.append("-I" + abs_path)
            for p in _d.cpp_info.libdirs:
                abs_path = os.path.join(root, str(p)) if not os.path.isabs(str(p)) else str(p)
                libdirs.append(abs_path)
            for lib in _d.cpp_info.libs:
                if lib not in libs:
                    libs.append(lib)
        inc = " ".join(incs)
        link = " ".join(
            ["-L" + p for p in libdirs]
            + ["-l" + l for l in libs]
            + ["-Wl,-rpath," + p for p in libdirs]
        )
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_package.c -o test_package {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verify compile+link")
            return
        self.run("./test_package", env="conanrun")

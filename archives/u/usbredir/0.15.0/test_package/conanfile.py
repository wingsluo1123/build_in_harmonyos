import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        includes = []
        libdirs = []
        tested_libs = []
        dependency_libs = []
        system_libs = []
        tested_ref = self.dependencies["usbredir"].ref
        for _ref, dependency in self.dependencies.items():
            info = dependency.cpp_info
            includes.extend(info.includedirs)
            libdirs.extend(info.libdirs)
            if dependency.ref == tested_ref:
                tested_libs.extend(info.libs)
            else:
                dependency_libs.extend(info.libs)
            system_libs.extend(info.system_libs)

        def unique(items):
            seen = set()
            result = []
            for item in items:
                if item and item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        include_flags = " ".join(f'-I"{path}"' for path in unique(includes))
        libdir_flags = " ".join(f'-L"{path}"' for path in unique(libdirs))
        lib_flags = " ".join(
            f"-l{name}" for name in unique(tested_libs + dependency_libs + system_libs)
        )
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} test_usbredir.c -o test_usbredir "
            f"{include_flags} {libdir_flags} {lib_flags}"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link test completed")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_usbredir'", env="conanrun")

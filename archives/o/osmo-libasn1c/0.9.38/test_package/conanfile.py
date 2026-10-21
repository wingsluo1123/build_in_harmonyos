import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Conan 2 test packages do not expose every transitive header directory
        # through cpp_info here, while asn_internal.h publicly includes talloc.h.
        self.requires("talloc/2.4.4")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        incs, libdirs, libs = [], [], []
        for item in self.dependencies.host.values():
            for path in item.cpp_info.includedirs:
                p = os.path.join(item.package_folder, path)
                if p not in incs:
                    incs.append(p)
            for path in item.cpp_info.libdirs:
                p = os.path.join(item.package_folder, path)
                if p not in libdirs:
                    libdirs.append(p)
            for name in list(item.cpp_info.libs or []) + list(item.cpp_info.system_libs or []):
                if name not in libs:
                    libs.append(name)

        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        source = os.path.join(self.source_folder, "test_libasn1c.c")
        if not os.path.isfile(source):
            source = os.path.join(self.recipe_folder, "test_libasn1c.c")
        executable = os.path.join(self.build_folder, "test_libasn1c")
        command = [
            f'"{cc}"',
            "-O1",
            f'-I"{os.path.join(dep.package_folder, "include")}"',
        ]
        command += [f'-I"{path}"' for path in incs]
        command += [
            f'"{source}"',
            "-o",
            f'"{executable}"',
            f'-L"{os.path.join(dep.package_folder, "lib")}"',
            "-lasn1c",
        ]
        command += [f'-L"{path}"' for path in libdirs]
        command += [f"-l{name}" for name in libs]
        command += ["-lm"]
        self.run(" ".join(command))
        runtime = ":".join([os.path.join(dep.package_folder, "lib")] + libdirs)
        self.run(f'LD_LIBRARY_PATH="{runtime}" "{executable}"')

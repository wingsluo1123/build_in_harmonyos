import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    """Consumer check: compile and run a small program against the installed
    libosmo-cc (public headers + shared library + link closure)."""
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libosmocore/1.11.0")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg_inc = os.path.join(dep.package_folder, "include")
        pkg_lib = os.path.join(dep.package_folder, "lib")

        incs, libdirs, libs = [], [], []
        for d in self.dependencies.host.values():
            for i in d.cpp_info.includedirs:
                p = os.path.join(d.package_folder, i)
                if p not in incs:
                    incs.append(p)
            for i in d.cpp_info.libdirs:
                p = os.path.join(d.package_folder, i)
                if p not in libdirs:
                    libdirs.append(p)
            for n in list(d.cpp_info.libs or []) + list(d.cpp_info.system_libs or []):
                if n not in libs:
                    libs.append(n)
        for n in ("osmocore",):
            if n not in libs:
                libs.append(n)

        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        src = os.path.join(self.source_folder, "test_cc.c")
        if not os.path.isfile(src):
            src = os.path.join(self.recipe_folder, "test_cc.c")
        exe = os.path.join(self.build_folder, "test_cc")
        cmd = [f'"{cc}"', "-O1", f'-I"{pkg_inc}"']
        cmd += [f'-I"{i}"' for i in incs]
        cmd += [f'"{src}"', "-o", f'"{exe}"', f'-L"{pkg_lib}"', "-losmocc"]
        cmd += [f'-L"{d}"' for d in libdirs]
        cmd += [f"-l{n}" for n in libs]
        cmd += ["-lm", "-lpthread", "-ldl"]
        self.run(" ".join(cmd))

        run_env = ":".join([pkg_lib] + libdirs)
        self.run(f'LD_LIBRARY_PATH="{run_env}" "{exe}"')

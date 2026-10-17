import os
import shlex

from conan import ConanFile


class MeepTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_dir = self.dependencies["meep"].package_folder

        # 1) Structural installability checks (rule 12, non-assertion).
        test_script = os.path.join(os.path.dirname(__file__), "test_consumer.sh")
        self.run(f"bash {shlex.quote(test_script)} {shlex.quote(pkg_dir)}")

        # 2) Real API consumer test (R34): compile + link against libmeep.a
        #    with ALL transitive static deps, then run it. Catches packages
        #    that build fine but are unusable by consumers (missing headers,
        #    broken transitive deps, bad pkgconfig metadata, ...).
        src = os.path.join(os.path.dirname(__file__), "test_consumer.cpp")
        bin_path = os.path.join(self.build_folder, "test_consumer")

        incs, libs, libdirs = [], [], []
        for dep in self.dependencies.host.values():
            if not getattr(dep, "package_folder", None):
                continue
            for inc_dir in dep.cpp_info.includedirs:
                full = os.path.join(dep.package_folder, inc_dir)
                if os.path.isdir(full):
                    incs.append(full)
            for lib_dir in dep.cpp_info.libdirs:
                full = os.path.join(dep.package_folder, lib_dir)
                if os.path.isdir(full):
                    libdirs.append(full)
            libs.extend(dep.cpp_info.libs)

        # --start-group/--end-group: static-lib order does not matter.
        compile_cmd = " ".join(
            [
                "/data/service/hnp/bin/clang++",
                "-std=c++11",
                shlex.quote(src),
                "-o",
                shlex.quote(bin_path),
                *[f"-I{p}" for p in incs],
                *[f"-L{p}" for p in libdirs],
                "-Wl,--start-group",
                *[f"-l{l}" for l in libs],
                "-Wl,--end-group",
                "-lm -ldl -lpthread",
            ]
        )
        self.run(compile_cmd)

        ld_path = ":".join(libdirs)
        self.run(f'LD_LIBRARY_PATH="{ld_path}" {shlex.quote(bin_path)}')

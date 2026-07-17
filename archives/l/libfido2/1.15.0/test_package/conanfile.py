import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _get_all_paths(self):
        """Collect include and library paths from all dependencies."""
        inc_paths = []
        lib_paths = []
        libs_list = []
        lib_dirs = []

        for dep_name in ["libfido2", "libcbor", "openssl", "zlib"]:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg_folder = str(getattr(dep, "package_folder", "") or "")
            for incdir in dep.cpp_info.includedirs:
                if pkg_folder:
                    inc_paths.append(f"-I{os.path.join(pkg_folder, str(incdir))}")
                else:
                    inc_paths.append(f"-I{incdir}")
            for libdir in dep.cpp_info.libdirs:
                abs_libdir = os.path.join(pkg_folder, str(libdir)) if pkg_folder else str(libdir)
                lib_paths.append(f"-L{abs_libdir}")
                lib_dirs.append(abs_libdir)
            for lib in dep.cpp_info.libs:
                libs_list.append(f"-l{lib}")

        return inc_paths, lib_paths, libs_list, lib_dirs

    def build(self):
        inc_paths, lib_paths, libs_list, _ = self._get_all_paths()
        inc = " ".join(inc_paths)
        libdir_str = " ".join(lib_paths)
        libs = " ".join(libs_list)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_libfido2 {inc} {libdir_str} {libs}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        _, _, _, lib_dirs = self._get_all_paths()
        if lib_dirs:
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(lib_dirs) + ":" + old_ld
        self.run("./test_libfido2")

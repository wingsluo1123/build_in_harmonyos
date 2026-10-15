import os

from conan import ConanFile


class RmapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp") or "c++"
        src = os.path.join(self.source_folder, "test_rmap.cpp")
        exe = os.path.join(self.build_folder, "test_rmap")
        self.run(f"{cc} -std=c++17 {src} -o {exe}")

    def test(self):
        dep = self.dependencies["rmap"]
        rmap_bin = os.path.join(dep.cpp_info.bindirs[0], "rmap")
        resdir = dep.cpp_info.resdirs[0]
        self.run(f'RMAP_BIN="{rmap_bin}" RMAP_RESDIR="{resdir}" '
                 f'"{os.path.join(self.build_folder, "test_rmap")}"')

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    """Consumer view：链接安装后的 libgenometools 并运行 gt CLI。"""

    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link only")
            return
        pkg = None
        for ref, dep in self.dependencies.items():
            if str(getattr(ref, "ref", ref)).split("/")[0] == "genometools":
                pkg = dep
                break
        if pkg is None:
            raise Exception("genometools not found in dependency graph")
        cpp = pkg.cpp_info.aggregated_components()
        base = pkg.package_folder or ""
        inc = [d if os.path.isabs(d) else os.path.join(base, d)
               for d in cpp.includedirs]
        lib = [d if os.path.isabs(d) else os.path.join(base, d)
               for d in cpp.libdirs]
        defines = list(cpp.defines or [])
        cc = os.environ.get("CC") or "clang"
        cmd = [cc, "-O2",
               os.path.join(self.source_folder, "test_genometools.c"),
               "-o", os.path.join(self.build_folder, "test_genometools")]
        cmd += ["-I" + d for d in inc]
        cmd += ["-D" + d for d in defines]
        cmd += ["-L" + d for d in lib]
        cmd += ["-lgenometools", "-lm", "-lpthread"]
        cmd += ["-Wl,-rpath," + d for d in lib]
        self.output.info("compiling consumer probe: " + " ".join(cmd))
        self.run(" ".join(cmd))

    def test(self):
        if cross_building(self):
            return
        pkg = None
        for ref, dep in self.dependencies.items():
            if str(getattr(ref, "ref", ref)).split("/")[0] == "genometools":
                pkg = dep
                break
        base = pkg.package_folder
        bindir = os.path.join(base, "bin")
        probe = os.path.join(self.build_folder, "test_genometools")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or "/bin/sh"

        # 1. 消费者探针（conanrun + 裸环境各一次）
        self.run('%s -c "%s"' % (bash, probe), env="conanrun")
        self.run('%s -c "%s"' % (bash, probe))

        # 2. bin/gt 裸环境冒烟（-version 与内建单元测试）
        self.run('%s -c "%s/gt -version"' % (bash, bindir))
        self.run('%s -c "%s/gt -test"' % (bash, bindir))

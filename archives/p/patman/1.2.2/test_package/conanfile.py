import os
import platform

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PatmanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _patman(self):
        dep = self.dependencies["patman"]
        return os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "patman")

    def test(self):
        patman = self._patman()
        if not os.path.isfile(patman):
            raise RuntimeError(f"patman binary missing from package: {patman}")
        # 注意：build/host profile 相同时 can_run() 恒为真，必须再看物理 CPU
        if not (can_run(self) and platform.machine().lower() in ("aarch64", "arm64")):
            # 物理 CPU 非 aarch64（如 x86 runner 交叉构建）：无法执行目标二进制，
            # 只确认产物是 ELF，并如实标记为 skip——这不等于功能已验证。
            with open(patman, "rb") as f:
                magic = f.read(4)
            if magic != b"\x7fELF":
                raise RuntimeError(f"patman is not an ELF binary: {magic!r}")
            self.output.warning("SKIP: cannot run target binary on this host; "
                                "functional consumer cases not executed")
            return
        check = os.path.join(self.build_folder, "check_hits")
        data = os.path.join(self.source_folder, "data")
        exp = os.path.join(self.source_folder, "expected")
        db, pat = os.path.join(data, "db.fa"), os.path.join(data, "pat.fa")

        # 1. 版本串来自补丁（上游 Makefile 硬编码 1.2）
        ver_file = os.path.join(self.build_folder, "version.txt")
        self.run(f'"{patman}" -V > "{ver_file}"', env="conanrun")
        with open(ver_file) as f:
            ver = f.read().strip()
        if not ver.endswith("revision 1.2.2"):
            raise RuntimeError(f"unexpected version output: {ver!r}")

        # 2-5. patman 产出命中表 -> 编译出的 check_hits 解析并逐行比对
        cases = [
            ("exact", "-q -e 0"),                # 双链精确匹配（含反向互补）
            ("singlestrand", "-q -s -e 0"),      # -s 只匹配正链
            ("mismatch", "-q -e 1"),             # 允许 1 个错配
            ("gaps", "-q -e 1 -g 1"),            # 允许 1 个缺口
        ]
        for name, opts in cases:
            hits = os.path.join(self.build_folder, f"{name}.tsv")
            self.run(f'"{patman}" {opts} -o "{hits}" -D "{db}" -P "{pat}"', env="conanrun")
            self.run(f'"{check}" "{hits}" "{os.path.join(exp, name + ".tsv")}"', env="conanrun")

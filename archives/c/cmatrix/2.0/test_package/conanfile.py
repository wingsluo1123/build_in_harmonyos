from conan import ConanFile
from conan.tools.build import can_run

class CmatrixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 实际调用 cmatrix 二进制验证功能
            self.run("cmatrix -V", env="conanrun")
        else:
            # 交叉编译：验证二进制存在
            pkg = self.dependencies["cmatrix"]
            self.run(f"test -x {pkg.cpp_info.bindirs[0]}/cmatrix")
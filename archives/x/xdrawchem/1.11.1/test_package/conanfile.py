"""test_package — xdrawchem 1.11.1（XDrawChem，Qt5 二维分子结构绘制程序，qmake 工程）。

R34 反空壳：测试实质执行被测包二进制——test_xdrawchem.sh 驱动
`xdrawchem --version` / `--help`，并断言包内可执行文件为 OHOS aarch64 ELF、
实际链接了 Qt5Widgets/libopenbabel、且上游运行期数据（ring/ + doc/，RINGHOME）
已随包安装。工作目录用 tempfile.mkdtemp()（TMPDIR 下），不污染配方目录。
"""
import os
import tempfile

from conan import ConanFile


class XdrawchemTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["xdrawchem"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        data_dir = os.path.join(pkg.package_folder, "share", "xdrawchem")
        script = os.path.join(self.recipe_folder, "test_xdrawchem.sh")
        work_dir = tempfile.mkdtemp(prefix="xdrawchem-test-")
        # OHOS /system/bin/sh（mksh）不能执行 ELF，用 bash 包裹（模板先例）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} "{script}" "{bin_dir}" "{data_dir}" "{work_dir}"', env="conanrun")

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class GtkgreetTestConan(ConanFile):
    """gtkgreet 是无测试套件的 GTK 可执行程序；test_package 冒烟：
    制品含 bin/gtkgreet，且 --help 能在打包产物上正常退出。"""
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_gtkgreet.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["gtkgreet"]
        binary = os.path.join(package.package_folder, "bin", "gtkgreet")
        if not os.path.isfile(binary):
            raise ConanException("gtkgreet binary is missing: {}".format(binary))
        if cross_building(self):
            self.output.info(
                "cross-building: 目标 ELF 无法在构建主机运行，仅校验产物存在")
            return
        script = os.path.join(self.source_folder, "test_gtkgreet.sh")
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run('"{}" "{}" "{}"'.format(bash, script, binary), env="conanrun")

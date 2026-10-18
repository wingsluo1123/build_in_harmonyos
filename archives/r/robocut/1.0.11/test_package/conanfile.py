import os

from conan import ConanFile


class RobocutTestConan(ConanFile):
    """test_package — robocut 1.0.11（Qt5 Widgets GUI + libusb 切割机控制程序）。

    消费者视角冒烟：真实执行被测包安装的 bin/robocut，断言自报版本与帮助
    路径（`--version` / `--help` 在 main.cpp 的 QApplication 之前处理，无需
    显示设备；QT_QPA_PLATFORM=offscreen 兜底）。
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，须用 bash 包装
        # （knowthelist 2.3.1 先例）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

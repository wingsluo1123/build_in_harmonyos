import os

from conan import ConanFile


class RtkitTestConan(ConanFile):
    """test_package — rtkit 是可执行工具包（无库产物），此处执行安装后的二进制。

    覆盖三项：rtkit-daemon/rtkitctl 能在真机装载执行、CLI 契约完整、
    daemon 的 root 特权契约成立（非 root 必须拒绝启动）。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh（mksh）不能执行 ELF，必须用 bash 包裹
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

#!/usr/bin/env python3
"""Conan test_package — pacredir/0.7.10（R34 真实消费者验证）。

pacredir 是纯可执行文件包（package_type = "application"，只导出 bindirs），
没有可供链接的库 API，因此消费者验证 = **实际执行被测二进制**：

  * CLI 身份（-V / -h）与编入的 VERSION/ID/ARCH；
  * ELF/ABI 契约（AArch64 PIE、RELRO+BIND_NOW+NX、DT_NEEDED 收敛）；
  * 拉起守护进程走真实 HTTP：状态页 / Server 头 / favicon.png / style.css /
    /check / 404；
  * 无 systemd 平台上的降级与生命周期（首轮 mDNS 更新存活、SIGUSR1 状态转储、
    SIGTERM 干净退出）。

16 个独立检查项，口径与逐条清单见 test_pacredir.py 与 MANIFEST.yml。驱动只用
Python 标准库：CI worker 上没有 curl，也不能假设 readelf/objdump 在 PATH 上
（ELF 检视用 struct 手解）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        here = os.path.dirname(os.path.abspath(__file__))
        driver = os.path.join(here, "test_pacredir.py")
        # 守护进程日志落在 test_package 的构建目录：OHOS 的 /tmp 只读（E002）。
        log_path = os.path.join(self.build_folder, "pacredir-daemon.log")

        if not can_run(self):
            # 交叉编译且无法在构建机上运行目标二进制。仍然核对打包产物本身，
            # 不静默跳过（R34：至少要证明产物存在且形态正确）。
            binary = os.path.join(pkg, "bin", "pacredir")
            if not os.path.isfile(binary):
                raise SystemExit("缺少打包产物 bin/pacredir：%s" % binary)
            with open(binary, "rb") as fh:
                magic = fh.read(20)
            self.output.info("can_run()=False（交叉编译），跳过 16 项运行期检查")
            self.output.info("产物核对: %s (%d bytes), ELF magic=%r, class=%d, "
                             "e_machine=%d (183=AArch64)"
                             % (binary, os.path.getsize(binary), magic[:4],
                                magic[4], int.from_bytes(magic[18:20], "little")))
            if magic[:4] != b"\x7fELF" or magic[4] != 2 or \
                    int.from_bytes(magic[18:20], "little") != 183:
                raise SystemExit("bin/pacredir 不是 ELF64 AArch64 可执行文件")
            return

        self.run('%s "%s" "%s" "%s"' % (sys.executable, driver, pkg, log_path),
                 env="conanrun")

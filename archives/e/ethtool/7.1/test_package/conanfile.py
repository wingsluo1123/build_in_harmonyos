from conan import ConanFile
from conan.tools.build import can_run


class EthtoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 能力面边界（详见 notes.md 能力墙披露段）：本平台测试进程无相应
            # capability（SIOCETHTOOL ioctl 与 NETLINK_GENERIC socket 均 EACCES），
            # 因此这里只断言二进制真实可运行 + 信息面真实输出（上游 no_dev=true
            # 的两条入口 ethtool.c:6386(-h|--help) / :6392(--version)），
            # 不断言任何网卡诊断功能；断言失败即非零退出，不用 || true 兜底。
            self.run("ethtool --version", env="conanrun")
            self.run('ethtool --version 2>&1 | grep -q "ethtool version 7.1"',
                     env="conanrun")
            self.run("ethtool -h", env="conanrun")
            self.run('ethtool -h 2>&1 | grep -q "Usage:"', env="conanrun")
            self.run('ethtool -h 2>&1 | grep -q -- "--disable-netlink"',
                     env="conanrun")

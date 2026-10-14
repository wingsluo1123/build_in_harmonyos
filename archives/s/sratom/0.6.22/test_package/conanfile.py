import os

from conan import ConanFile


class SratomTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # PkgConfigDeps：依赖头文件路径经 .pc Cflags 解析（lv2/serd/sord 的
    # 包缓存目录布局不一，手工聚合 package_folder 会漏 lv2——G2 两轮实证；
    # 主包构建已实证 .pc 通道可用）。VirtualRunEnv：运行期环境聚合。
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lv2 头文件（<lv2/atom/atom.h>）消费者测试直接使用：显式声明使
        # PkgConfigDeps 生成 lv2.pc（G2 两轮实证：仅靠传递依赖不生成）
        self.requires("lv2/1.18.11-git")

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        src = os.path.join(self.source_folder, "test_sratom_roundtrip.c")
        exe = os.path.join(self.build_folder, "test_sratom_roundtrip")
        gen = self.generators_folder
        # 两步法（G2 五轮实证：嵌套 "$(...)" 子 shell 展开在沙箱不稳）：
        # ①pkg-config 输出落盘 ②Python 读回字面量 flags 拼编译命令
        flags_file = os.path.join(self.build_folder, "pc-flags.txt")
        self.run(f'PKG_CONFIG_PATH="{gen}" pkg-config --cflags --libs '
                 f'sratom-0 sord-0 serd-0 lv2 > "{flags_file}"')
        with open(flags_file) as fh:
            flags = fh.read().strip()
        # sratom-0.pc 链已含全部依赖 -L/-l（含 -lzix-0，拓扑序由 pkg-config
        # 保证）；勿追加 -lzix——zix 库文件名是 libzix-0（G2 实证 -lzix 404）
        self.run(f"{cc} {src} -o {exe} {flags}")

    def test(self):
        exe = os.path.join(self.build_folder, "test_sratom_roundtrip")
        self.run(f'"{exe}"', env="conanrun")

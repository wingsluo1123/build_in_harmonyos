import os

from conan import ConanFile


class LilvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # PkgConfigDeps（依赖 .pc 通道，sratom 同款实证）+ VirtualRunEnv
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者测试直接使用 lv2 头文件域（lilv.h 内部引用），显式声明使
        # PkgConfigDeps 生成 lv2.pc（sratom G2 五轮实证：仅靠传递依赖
        # 不生成 .pc）
        self.requires("lv2/1.18.11-git")

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        src = os.path.join(self.source_folder, "test_lilv_discovery.c")
        exe = os.path.join(self.build_folder, "test_lilv_discovery")
        gen = self.generators_folder
        # 两步法（sratom G2 五轮实证：嵌套 $() 子 shell 展开在沙箱不稳）：
        # pkg-config 输出落盘，Python 读回字面量 flags 拼编译命令。
        # 静态链接顺序由 pkg-config 拓扑序保证（lilv-0 最先）。
        flags_file = os.path.join(self.build_folder, "pc-flags.txt")
        self.run(f'PKG_CONFIG_PATH="{gen}" pkg-config --cflags --libs '
                 f'lilv-0 sratom-0 sord-0 serd-0 lv2 > "{flags_file}"')
        with open(flags_file) as fh:
            flags = fh.read().strip()
        self.run(f"{cc} {src} -o {exe} {flags}")

    def test(self):
        exe = os.path.join(self.build_folder, "test_lilv_discovery")
        fixture = os.path.join(self.source_folder, "fixture",
                               "consumer-test.lv2", "..")
        self.run(f'LV2_PATH="{os.path.abspath(fixture)}" '
                 f'"{os.path.join(self.build_folder, "test_lilv_discovery")}"',
                 env="conanrun")

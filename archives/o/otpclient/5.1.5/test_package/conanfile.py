#!/usr/bin/env python3
"""otpclient 消费者测试（Conan L1，test_package）

验证三件事，缺一不可：
  1) 包内产物齐全（可执行文件按 gui 选项门控 + 桌面数据 + GSettings schema 编译产物）
  2) 可执行文件为本机 OHOS AArch64 ELF
  3) 被测程序能被真实执行（CLI 版本输出），而不是只做静态断言
"""
import os
import struct

from conan import ConanFile


class OtpclientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        bindir = os.path.join(pkg, "bin")
        # GUI 版可执行文件受 gui 选项门控（本环境默认 False，见配方 default_options 说明）
        gui = bool(dep.options.gui)

        # ── 1) 产物齐全 ──────────────────────────────────────────────
        expected = ["otpclient-cli", "otpclient-search-provider"]
        if gui:
            expected.append("otpclient")
        missing = [b for b in expected if not os.path.isfile(os.path.join(bindir, b))]
        assert not missing, f"包内缺少可执行文件: {missing}"

        # 数据编译产物：上游在 install 阶段调用 glib-compile-schemas
        # （CMakeLists.txt:237）与 glib-compile-resources（src/gui/CMakeLists.txt:5）。
        # 若宿主工具在 OHOS 上没跑起来，这个文件就会缺失或为空 —— 由本断言兜住。
        schema = os.path.join(pkg, "share", "glib-2.0", "schemas", "gschemas.compiled")
        assert os.path.isfile(schema), f"GSettings schema 未编译（宿主工具未生效）: {schema}"
        assert os.path.getsize(schema) > 0, f"GSettings schema 为空: {schema}"

        # KRunner 桌面文件与 GUI 无关，任何配置都必须存在
        desktop = os.path.join(
            pkg, "share", "krunner", "dbusplugins",
            "com.github.paolostivanin.OTPClient.KRunner.desktop")
        assert os.path.isfile(desktop), f"缺少 KRunner 桌面文件: {desktop}"

        # ── 2) 架构正确性（ELF e_machine == 0xB7 AArch64）────────────
        with open(os.path.join(bindir, "otpclient-cli"), "rb") as fh:
            head = fh.read(20)
        assert head[:4] == b"\x7fELF", "otpclient-cli 不是 ELF 文件"
        assert head[4] == 2, "otpclient-cli 不是 64 位 ELF"
        machine = struct.unpack("<H", head[18:20])[0]
        assert machine == 0xB7, f"otpclient-cli 架构非 AArch64（e_machine=0x{machine:x}）"

        # ── 3) 真实执行（消费者视角）────────────────────────────────
        cli = os.path.join(bindir, "otpclient-cli")
        self.run(f'"{cli}" --version', env="conanrun")
        self.run(f'sh "{os.path.join(self.recipe_folder, "test.sh")}" "{pkg}" "{cli}"', env="conanrun")

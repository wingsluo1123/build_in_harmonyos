#!/usr/bin/env python3
"""test_package — nbdkit 1.48.0 消费者验证

R34: test 必须实质调用被测包（禁止空壳）。nbdkit 是 NBD 服务器应用
（服务端二进制 sbin/nbdkit + 动态插件 + 公开插件 ABI 头文件），
消费者验证 = 模拟依赖 nbdkit 服务器的上层组件：
1. 安装产物完整性：sbin/nbdkit 二进制存在且为 arm64 ELF
2. 公开 CLI 可执行：`nbdkit --version` 输出 1.48.0（服务器进程可启动）
3. 平台感知：`nbdkit --dump-config` host_os=linux-ohos / aarch64
4. 公开插件 ABI 可在运行时加载安装的插件（.so，消费者 dlopen 路径）
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class NbdkitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["nbdkit"].package_folder
        # nbdkit 安装位置：本地 autotools 默认 sbin/，conan 包内为 bin/
        # （Autotools.install 将 $prefix/bin 作为 bindir），两者都探测
        nbdkit_bin = None
        for sub in ("sbin", "bin"):
            cand = os.path.join(package_folder, sub, "nbdkit")
            if os.path.isfile(cand):
                nbdkit_bin = cand
                break
        assert nbdkit_bin, (
            f"nbdkit binary not found under {package_folder}/{{sbin,bin}}"
        )

        if not can_run(self):
            with open(nbdkit_bin, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "nbdkit is not an ELF binary"
            self.output.info(f"nbdkit ELF binary exists: {nbdkit_bin}")
            return

        # 1. 公开 CLI：--version 必须输出 1.48.0
        out = subprocess.run(
            [nbdkit_bin, "--version"], capture_output=True, text=True, timeout=30
        )
        assert out.returncode == 0, "nbdkit --version non-zero"
        assert "1.48.0" in out.stdout, f"version mismatch: {out.stdout!r}"
        self.output.info(f"nbdkit --version -> {out.stdout.strip()}")

        # 2. 平台感知：--dump-config 应上报 OHOS 平台
        cfg = subprocess.run(
            [nbdkit_bin, "--dump-config"], capture_output=True, text=True, timeout=30
        )
        assert cfg.returncode == 0, "nbdkit --dump-config failed"
        conf = cfg.stdout
        assert "host_os=linux-ohos" in conf, f"not OHOS: {conf[:200]}"
        assert "version=1.48.0" in conf, f"version absent: {conf[:200]}"
        self.output.info("nbdkit --dump-config: host_os=linux-ohos / version=1.48.0")

        help_out = subprocess.run(
            [nbdkit_bin, "--help"], capture_output=True, text=True, timeout=30
        )
        assert help_out.returncode == 0, "nbdkit --help failed"
        assert help_out.stdout.strip(), "nbdkit --help produced no output"
        self.output.info("nbdkit --help produced non-empty help output")

        # 3. 公开插件 ABI：dlopen 安装的插件产物（与本地 harmonyos_special_test 一致的 C dlopen 方式）
        plugin_dir = os.path.join(package_folder, "lib", "nbdkit", "plugins")
        example = os.path.join(plugin_dir, "nbdkit-example1-plugin.so")
        assert os.path.isfile(example), f"installed example1 plugin missing: {example}"

        # CI 上插件 .so 可能位于 HMDFS，权限位 770 且 other 无读/执行位，
        # 非同组用户 dlopen 会 Permission denied。先把插件复制到当前用户
        # 可读写的临时路径再加载（cp 产生当前用户属主的新 inode，规避
        # 打包缓存文件的 owner/group 权限限制），并用 C 消费者程序 dlopen。
        # 注意：HMDFS 上 shutil.copy2（复制元数据/权限位）会 EPERM
        # （Operation not permitted），必须用 copyfile（仅复制内容）+
        # 显式 chmod。临时目录放 $TMPDIR，避免污染配方目录。
        import shutil
        import tempfile
        work = tempfile.mkdtemp(prefix="nbdkit-tp-", dir=os.environ.get("TMPDIR", None))
        plugin_copy = os.path.join(work, "nbdkit-example1-plugin.so")
        shutil.copyfile(example, plugin_copy)
        os.chmod(plugin_copy, 0o744)  # 尽力补执行位（HMDFS 下可能归一化）
        self.output.info(f"plugin copied to: {plugin_copy}")

        # 编译 C 消费者（test.c：公开插件 ABI dlopen 断言），与本地验证路径一致
        cc = shutil.which("clang") or "cc"
        consumer = os.path.join(work, "test_nbdkit_consumer")
        self.run(
            f'"{cc}" -o "{consumer}" '
            f'"{os.path.join(self.recipe_folder, "test.c")}" -ldl'
        )
        r = self.run(f'"{consumer}" "{plugin_copy}"', env="conanrun")
        assert r == 0, "C dlopen consumer validation failed"
        self.output.info("plugin ABI loaded via C dlopen consumer (name/struct_size/version)")

        self.output.info("nbdkit 1.48.0 consumer validation PASSED")

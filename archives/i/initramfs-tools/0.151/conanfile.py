#!/usr/bin/env python3
"""initramfs-tools 0.151 — Debian initramfs 构建工具集（Debian native 包）。

上游是 Debian **native** 包（无独立上游仓库）：源码 = `Makefile`（唯一 C 程序 `unmkinitramfs.c`）
+ shell 工具（`mkinitramfs`/`update-initramfs`/`lsinitramfs`）+ `hooks/`、`scripts/`、`conf/`、
`kernel/` + `debian/`。OHOS 环境没有 dh/debhelper，故本配方**不跑 dh**，按
`debian/initramfs-tools*.install` 声明的映射直接安装（与同族 `archives/i/installation-report`、
`archives/i/init-system-helpers` 同一做法），并按 `debian/rules` 的 `override_dh_install` 做法
对 `mkinitramfs` 做 `@VERSION@`/`@BUSYBOX_PACKAGES@` 变量替换。

依赖：**无 Conan requires**。`debian/control` 的 Build-Depends 里 debhelper-compat 只是 dh 版本声明、
bash-completion 只用于装源码自带的 `bash_completion.d/` 补全脚本、**shunit2 是 `<!nocheck>` 的
测试框架**（仓库与制品仓都没有）→ 按"缺环境就下"在 build() 内从 Debian pool 取来仅用于跑上游测试，
不进包产物。Depends 是 initramfs-tools-core 等**同源子包**，无外部运行期库依赖。

上游测试（N=16）：①`tests/functions_test`（POSIX sh + shunit2，6 个测试函数；`oneTimeSetUp` 里
source `scripts/functions`，末尾 `. shunit2` → 需把 shunit2 放到 PATH 上）—— build() 内真跑 6/6；
②`debian/tests/control` 注册的 10 个 Debian autopkgtest 用例（copy-file + unmkinitramfs + 8 个
qemu-*）—— 需 Debian 测试床（linux-image-generic + qemu-system-native + root），OHOS 架构上不可
满足，按平台级系统性阻塞逐项写进 manifest.yaml 的 blocked_cases（不虚报通过数）。
"""
import os
import re
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# 按 debian/initramfs-tools*.install 的映射：(源内相对路径, 包内相对路径, 是否可执行)
PAYLOAD = (
    # initramfs-tools-bin.install
    ("unmkinitramfs", "bin/unmkinitramfs", True),        # Makefile 编译产物
    # initramfs-tools-core.install
    ("conf/initramfs.conf", "etc/initramfs-tools/initramfs.conf", False),
    ("conf/modules", "share/initramfs-tools/modules", False),
    ("hook-functions", "share/initramfs-tools/hook-functions", False),
    ("init", "share/initramfs-tools/init", False),
    ("lsinitramfs", "bin/lsinitramfs", True),
    # initramfs-tools.install
    ("conf/update-initramfs.conf", "etc/initramfs-tools/update-initramfs.conf", False),
    ("debian/script", "share/bug/initramfs-tools/script", False),
    ("update-initramfs", "sbin/update-initramfs", True),
    # man 页（dh_installman 负责，映射同 Debian 的分类）
    ("initramfs.conf.5", "share/man/man5/initramfs.conf.5", False),
    ("update-initramfs.conf.5", "share/man/man5/update-initramfs.conf.5", False),
    ("initramfs-tools.7", "share/man/man7/initramfs-tools.7", False),
    ("lsinitramfs.8", "share/man/man8/lsinitramfs.8", False),
    ("mkinitramfs.8", "share/man/man8/mkinitramfs.8", False),
    ("unmkinitramfs.8", "share/man/man8/unmkinitramfs.8", False),
    ("update-initramfs.8", "share/man/man8/update-initramfs.8", False),
)
# 目录型产物：(源内目录, 包内目录)
PAYLOAD_DIRS = (
    ("hooks", "share/initramfs-tools/hooks"),
    ("scripts", "share/initramfs-tools/scripts"),
    ("bash_completion.d", "share/bash-completion/completions/initramfs-tools"),
    ("kernel", "etc/kernel"),
)


class InitramfsToolsConan(ConanFile):
    name = "initramfs-tools"
    version = "0.151"
    description = ("Debian initramfs tools (mkinitramfs, update-initramfs, lsinitramfs, "
                   "unmkinitramfs, hooks/scripts framework) — native shell package + 1 C program")
    license = "GPL-2.0-or-later"          # debian/copyright: License: GPL-2+
    homepage = "https://salsa.debian.org/kernel-team/initramfs-tools"
    url = "https://salsa.debian.org/kernel-team/initramfs-tools"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Makefile 是手写的（只编一个 unmkinitramfs.c），靠工具链提供 CC/CFLAGS 等环境
        AutotoolsToolchain(self).generate()

    def build(self):
        # 1) `make all` → 编译 unmkinitramfs（Makefile 里 all: unmkinitramfs，用隐式规则 + $(CC)）
        self.run("make all", cwd=self.source_folder)
        # 2) 上游测试：tests/functions_test（shunit2 驱动的 6 个用例）
        if os.path.isfile(os.path.join(self.source_folder, "unmkinitramfs")):
            self.output.info("[build] make all 产出 unmkinitramfs 成功")
        else:
            raise ConanInvalidConfiguration("make all 未产出 unmkinitramfs")
        self._run_upstream_tests()

    def _fetch_shunit2(self):
        """按"缺环境就下"取测试框架（不进产物）。"""
        spec = self.conan_data["test_framework"]
        dest = os.path.join(self.build_folder, "test-framework")
        os.makedirs(dest, exist_ok=True)
        get(self, url=spec["url"], sha256=spec["sha256"], destination=dest,
            strip_root=spec.get("strip_root", True))
        return dest

    def _run_upstream_tests(self):
        framework = self._fetch_shunit2()
        if not os.path.isfile(os.path.join(framework, "shunit2")):
            raise ConanInvalidConfiguration("shunit2 测试框架未取到（%s）" % framework)
        testdir = os.path.join(self.source_folder, "tests")
        tests = sorted(f for f in os.listdir(testdir)
                       if os.path.isfile(os.path.join(testdir, f)) and not f.endswith("~"))
        if not tests:
            raise ConanInvalidConfiguration("未找到上游测试（tests/ 为空）")
        # 用 subprocess 直接捕获输出：不依赖 shell 重定向（实测经 bash -c + 重定向时输出会跑到
        # conan 控制台、日志文件为空，导致解析不到 Ran/OK 而误判"未真跑"）
        env = dict(os.environ)
        env["PATH"] = framework + os.pathsep + env.get("PATH", "")
        proc = subprocess.run(["sh", os.path.join("tests", tests[0])],
                              cwd=self.source_folder, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=300)
        raw = proc.stdout.decode("utf-8", "replace")
        # 剥掉 ANSI 颜色码：shunit2 会给数字/OK 着色（实测 repr 里是 `Ran \x1b[1;36m6\x1b[0m tests.`），
        # 不剥离则 `Ran (\d+) tests?` 永远匹配不到；再归一化空白后解析
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw)
        tail = "\n".join(text.splitlines()[-20:])
        norm = " ".join(text.split())
        ran = re.search(r"Ran (\d+) tests?", norm)
        if "FAILED" in text or re.search(r"^not ok", text, re.M):
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游用例失败（真实失败）：\n" + tail)
        if not ran:
            raise ConanInvalidConfiguration(
                "[upstream tests] 未取得 shunit2 运行结果（可能未真跑，exit=%s，输出 %d 字节）：\n%s"
                % (proc.returncode, len(text), tail))
        self.output.info("[upstream tests] shunit2: Ran %s tests（%d 个 test_* 函数）"
                         % (ran.group(1), text.count("\ntest_") + text.startswith("test_")))
        for line in text.splitlines()[-5:]:
            self.output.info("    " + line)

    def package(self):
        src = self.source_folder
        for rel, target, executable in PAYLOAD:
            source = os.path.join(src, rel)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration("缺少产物源文件: %s" % rel)
            dest = os.path.join(self.package_folder, *target.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(source, dest)
            os.chmod(dest, 0o755 if executable else 0o644)

        for rel, target in PAYLOAD_DIRS:
            source = os.path.join(src, rel)
            if not os.path.isdir(source):
                raise ConanInvalidConfiguration("缺少产物源目录: %s" % rel)
            shutil.copytree(source, os.path.join(self.package_folder, *target.split("/")),
                            dirs_exist_ok=True)

        # mkinitramfs 需按 debian/rules 的 override_dh_install 做变量替换
        template = os.path.join(src, "mkinitramfs")
        if not os.path.isfile(template):
            raise ConanInvalidConfiguration("缺少 mkinitramfs 模板")
        with open(template, errors="replace") as fh:
            body = fh.read()
        if "@VERSION@" not in body:
            raise ConanInvalidConfiguration("mkinitramfs 模板里未找到 @VERSION@ 占位符")
        body = body.replace("@VERSION@", self.version)
        body = body.replace("@BUSYBOX_PACKAGES@", "busybox or busybox-static")
        dest = os.path.join(self.package_folder, "sbin", "mkinitramfs")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as fh:
            fh.write(body)
        os.chmod(dest, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

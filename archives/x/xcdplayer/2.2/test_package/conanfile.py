#!/usr/bin/env python3
"""Conan test_package — xcdplayer 2.2

L1 test: xcdplayer 是 X11 交互式 CD 播放器，test_xcdplayer.sh 真实执行被测包
二进制（R34 实质依赖被测包）。无 DISPLAY 时程序在 XtOpenDisplay 失败处
exit(1) 并打印 "can't open display"（top_setup.c），该路径已完整走过
动态链接/运行时库解析，足以验证包完整性与可执行性。

运行时库补齐沿用 xeyes 1.3.1 先例：主配方所有 X11 库均来自 conan 依赖，
conanrun 环境注入 LD_LIBRARY_PATH；另按 HMBS [stale_runtime_library] 把
依赖包内 .so 绝对路径按依赖序拼成 LD_PRELOAD 兜底（loader 可能忽略
LD_LIBRARY_PATH）。HMBS [shell_getcwd]：POSIX sh，不用 set -e/-u/pipefail。
"""
import os
import shutil

from conan import ConanFile


class XcdplayerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件（优先非符号链接实体文件，
        HMFS 对 symlink 物化不可靠，E050 —— xeyes 同款处理）。"""
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in sorted(files):
                if f.startswith(soname_prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        for p in hits:
            if not os.path.islink(p):
                return p
        return hits[0]

    def _runtime_preload(self):
        """按依赖序拼接 X11 运行时共享库的绝对路径（LD_PRELOAD 兜底）。"""
        order = [("libxau", "libXau.so.6"),
                 ("libxdmcp", "libXdmcp.so.6"),
                 ("libxcb", "libxcb.so.1"),
                 ("libice", "libICE.so.6"),
                 ("libsm", "libSM.so.6"),
                 ("libx11", "libX11.so.6"),
                 ("libxext", "libXext.so.6"),
                 ("libxt", "libXt.so.6"),
                 ("libxmu", "libXmu.so.6"),
                 ("libxpm", "libXpm.so.4"),
                 ("libxaw", "libXaw.so.7")]
        found = []
        for name, prefix in order:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xcdplayer"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        xcd_bin = os.path.join(bin_dir, "xcdplayer")

        # HMBS [shell_getcwd]：使用注入的 SHELL/CONFIG_SHELL（/bin/sh）
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xcdplayer.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xcd_bin}" "{bin_dir}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_xcdplayer.sh 在真实断言结束后打印。
        # 上游套件审计结论（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # xcdplayer 2.2 发布包无自动化测试 —— Imakefile 只有
        # NormalProgramTarget(xcdplayer/cdinfo/cdgrab)，无 make test/check。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -f Imakefile (no check target)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xcdplayer 2.2 上游无测试套件：Imakefile 无 check/TESTS '
              '目标，源码树无 tests/ 目录"}')

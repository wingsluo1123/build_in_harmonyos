#!/usr/bin/env python3
"""Conan test_package — rawtran 1.1（application 包的消费者视角验证）。

把实质验证交给独立的测试源 test_rawtran.py（经 self.run() 调用，满足 L0c/L0d：
test_package 里存在非 conanfile.py 的测试源），本文件只负责：
  * 解析解释器（绝对路径候选 + PATH，避免只靠 PATH —— CI worker 的 PATH 可能很贫）；
  * 用 conanrun 环境执行测试（被验证包的 bin/ 在 PATH 上）；
  * 子进程输出镜像到日志文件，失败时由 Conan 输出把日志尾部打出来
    （否则 CI 只留 conan 日志的一段时看不到是哪一项失败）。

检查面见 test_rawtran.py 顶部：A 包布局 5 项 + B 命令行契约 1 项 +
C dcraw 存在性探测两条分支 2 项 + D 消费者端到端用例 7 项 = 15 项。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment

# OHOS PC（CI worker / 真机）上的解释器候选，路径习惯与仓库既有配方一致
# （audioflux 0.1.9 的 _python3()、gymnasium 1.3.0 的注释都指向 /data/service/hnp/bin）。
PYTHON_CANDIDATES = ("/storage/Users/currentUser/usr/local/bin/python3",
                     "/data/service/hnp/bin/python3",
                     "/usr/local/bin/python3",
                     "/usr/bin/python3")


class RawtranTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _python3(self):
        for cand in PYTHON_CANDIDATES:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        for name in ("python3", "python"):
            hit = shutil.which(name)
            if hit:
                return hit
        raise ConanException("no python3 interpreter found (tried %s and PATH)"
                             % (list(PYTHON_CANDIDATES),))

    def _dump_log(self, log):
        self.output.error("rawtran consumer test FAILED; tail of %s:" % log)
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError as exc:
            self.output.error("  (log unreadable: %r)" % exc)
            return
        for line in lines[-60:] or ["  (log is empty)"]:
            self.output.error("  | %s" % line)

    def test(self):
        pkg_root = self.dependencies["rawtran"].package_folder
        script = os.path.join(self.source_folder, "test_rawtran.py")
        if not os.path.isfile(script):
            raise ConanException("test_rawtran.py missing from test_package: %s" % script)
        python = self._python3()
        log = os.path.join(tempfile.mkdtemp(prefix="rawtran-consumer-test-"), "test.log")
        self.output.info("rawtran consumer test interpreter: %s" % python)
        self.output.info("rawtran consumer test log: %s" % log)

        env = Environment()
        env.define("RAWTRAN_PKG_ROOT", pkg_root)
        env.define("RAWTRAN_TEST_LOG", log)
        env.define("PYTHONUNBUFFERED", "1")
        with env.vars(self).apply():
            try:
                self.run('"%s" -u "%s" %s' % (python, script, pkg_root), env="conanrun")
            except ConanException:
                self._dump_log(log)
                raise

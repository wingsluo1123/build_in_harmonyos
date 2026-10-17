#!/usr/bin/env python3
"""Conan test_package — istgt 0.4-20111008（application 包的消费者视角验证）。

把实质验证交给独立的测试源 test_istgt.py（经 self.run() 调用，满足 L0c/L0d：
test_package 里存在非 conanfile.py 的测试源），本文件只负责：
  * 解析 python3 解释器（绝对路径候选 + PATH，避免只靠 PATH —— CI worker
    的 PATH 可能很贫）；
  * 用 conanrun 环境执行测试（libcrypto.so 经 conanrun 的 LD_LIBRARY_PATH
    与二进制内嵌 RPATH 双通道解析）；
  * 子进程输出镜像到日志文件，失败时把日志尾部回灌 conan 输出
    （否则 CI 只留 conan 日志的一段时看不到是哪一项失败）。

检查面见 test_istgt.py 顶部：A 包布局 8 项 + B 命令行契约 3 项 +
C 守护进程端到端 4 项 = 15 项。
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment

# OHOS PC（CI worker / 真机）上的解释器候选，路径习惯与仓库既有配方一致
# （rawtran 1.1 同模式）
PYTHON_CANDIDATES = ("/storage/Users/currentUser/usr/local/bin/python3",
                     "/data/service/hnp/bin/python3",
                     "/usr/local/bin/python3",
                     "/usr/bin/python3")


class IstgtTestConan(ConanFile):
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
        self.output.error("istgt consumer test FAILED; tail of %s:" % log)
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError as exc:
            self.output.error("  (log unreadable: %r)" % exc)
            return
        for line in lines[-60:] or ["  (log is empty)"]:
            self.output.error("  | %s" % line)

    def test(self):
        pkg_root = self.dependencies["istgt"].package_folder
        script = os.path.join(self.source_folder, "test_istgt.py")
        if not os.path.isfile(script):
            raise ConanException("test_istgt.py missing from test_package: %s"
                                 % script)
        python = self._python3()
        log = os.path.join(tempfile.mkdtemp(prefix="istgt-consumer-test-"),
                           "test.log")
        self.output.info("istgt consumer test interpreter: %s" % python)
        self.output.info("istgt consumer test log: %s" % log)

        env = Environment()
        env.define("ISTGT_PKG_ROOT", pkg_root)
        env.define("ISTGT_TEST_LOG", log)
        env.define("PYTHONUNBUFFERED", "1")
        with env.vars(self).apply():
            try:
                self.run('"%s" -u "%s" %s' % (python, script, pkg_root),
                         env="conanrun")
            except ConanException:
                self._dump_log(log)
                raise

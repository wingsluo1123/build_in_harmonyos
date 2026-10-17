#!/usr/bin/env python3
"""Conan test_package — verhaal 025

Consumer test (R34): drives the installed public CLI (bin/verhaal) end to end —
builds a database from a synthetic kernel stable tree and reads the resulting
backport mapping back out.  No private headers, no upstream test directory
(upstream 025 ships no registered test suite; the unregistered
scripts/git-resolve.sh --selftest entry is recorded in MANIFEST.yml as
upstream_tests_unrunnable).

CI worker 的沙箱进程配额被打满时（`/bin/sh: can't fork - try again`），用例里
的 git/verhaal 调用会被打断 —— 与 build 步同根因（见 025/notes.md 问题 7）。
故这里对**仅命中进程创建失败特征**的失败做纯 Python 退避重试（time.sleep +
进程内读日志/匹配，重试路径本身不 fork，避免 shell 版重试先死于配额枯竭，
pgqd/PR #16073 教训）；其他任何失败首次即失败并打印完整转录。
"""
import os
import re
import time

from conan import ConanFile
from conan.errors import ConanException

_FORK_RETRY_ATTEMPTS = 10
_FORK_RETRY_WAIT = 30  # 秒
_FORK_FAILURE_PATTERNS = (
    re.compile(r"(?:posix_spawn|fork|spawn)[^\n]{0,80}Resource temporarily unavailable"),
    re.compile(r"Resource temporarily unavailable[^\n]{0,80}(?:posix_spawn|fork)"),
    re.compile(r"(?:can'?t|cannot) fork"),
    re.compile(r"fork: retry"),
    re.compile(r"No record of process"),
)


class VerhaalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        script = os.path.join(self.source_folder, "test.sh")
        log_path = os.path.join(self.build_folder, "test-sh.log")
        command = '{} -ec "sh {}"'.format(bash, script)

        for attempt in range(1, _FORK_RETRY_ATTEMPTS + 1):
            try:
                retcode = self.run('{} > "{}" 2>&1'.format(command, log_path),
                                   env="conanrun", ignore_errors=True)
            except ConanException:
                retcode = -1
            output = _read(log_path)
            if retcode == 0:
                self.output.info(output)
                return
            self.output.error(output)
            signature = None
            for pattern in _FORK_FAILURE_PATTERNS:
                match = pattern.search(output)
                if match:
                    signature = match.group(0).strip()[:120]
                    break
            if signature is None or attempt == _FORK_RETRY_ATTEMPTS:
                raise ConanException("consumer test failed (exit {})".format(retcode))
            self.output.warning(
                "consumer test: 进程创建失败特征命中: {}（第 {}/{} 次重试），{}s 后重试"
                .format(signature, attempt, _FORK_RETRY_ATTEMPTS - 1, _FORK_RETRY_WAIT)
            )
            time.sleep(_FORK_RETRY_WAIT)


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return handle.read()
    except OSError:
        return ""

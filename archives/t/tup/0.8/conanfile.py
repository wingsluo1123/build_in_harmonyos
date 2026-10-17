#!/usr/bin/env python3
"""Conan recipe — tup 0.8 (upstream `build.sh`, ldpreload server).

tup is a file-based build system written in C that builds itself through its own
`build.sh` (neither cmake, autotools nor make). It produces two artifacts that
must be installed **side by side**:

  * bin/tup               — the CLI
  * bin/tup-ldpreload.so  — the LD_PRELOAD dependency-tracking shim

`src/tup/server/depfile.c` derives the shim path from the tup executable itself
(`<exe-path>-ldpreload.so`), so splitting them across directories silently
breaks every build that runs through the ldpreload server.

OpenHarmony/HarmonyOS PC (aarch64) notes — see patches/0001 and patches/0002:

  * `uname -s` reports "HarmonyOS", while the runtime is musl on the Linux ABI.
    Patch 0001 adds that branch to build.sh and selects the ldpreload server
    (the sandbox has no usable /dev/fuse, so fuse/fuse3 are not options).
  * Patch 0002 fixes the shim itself: glibc-only wrappers are guarded behind
    __GLIBC__ for musl, the dependency fd is opened lazily (OHOS opens files
    before the shim's constructor runs), and utimensat() plus O_CREAT-created
    opens are reported as writes — which is what the toybox `touch` shipped by
    OpenHarmony needs to be tracked at all.
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# build.sh 的产物。缺任意一个都不算构建成功：package() 用的 copy() 在没有匹配
# 文件时不报错，会把残缺的构建静默打成只有一个 COPYING 的空包。
_ARTIFACTS = ("tup", "tup-ldpreload.so")

# OHOS CI worker 的进程槽位长期处在临界点：PR #15176 的失败构建机上 procs≈668、
# load≈21，而同一台设备的本地同配方同源码（procs≈180）一次通过。clang 拉起链接器
# 时报 `posix_spawn failed: Resource temporarily unavailable`，链接脚本里的 shell 报
# `can't fork - try again`。判定见 notes.md #9：成败取决于该步**同时**需要几个进程，
# 故 build.sh 已把链接步的进程层级压到与普通编译步一致；这里只做外层兜底。
_SPAWN_PRESSURE_MARKERS = (
    "resource temporarily unavailable",
    "can't fork",
    "cannot fork",
)
# build.sh 内层窗口（patch 0001 的 retry_spawn：15 次、退避 20→60s ≈ 13 分钟）
# 耗尽后才整棵重建。最坏 2×(13min+~2min) 仍在 CI 的 3600s 单包超时内。
_BUILD_ATTEMPTS = 2


class TupConan(ConanFile):
    name = "tup"
    version = "0.8"
    description = "A file-based build system"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/gittup/tup"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器取自 conan conf，不使用 ${CC} 之类的 shell 环境变量
        comp = self.conf.get("tools.build:compiler_executables",
                             check_type=dict, default={}) or {}
        cc = comp.get("c", "clang")

        # build.sh 是上游唯一的构建入口，全部通过环境变量配置：
        #   TUP_SERVER=ldpreload — 本平台无 /dev/fuse，仅此后端可用
        #   TUP_LABEL=<version>  — 写入 `tup --version`（默认是 bootstrap）
        #
        # 脚本必须以 `<shell> <script>` 形式调用（它要读 conanbuild 环境，还得
        # 落在源码根做 cwd），shebang 因此不生效，`#! /bin/sh -e` 里的 -e 必须
        # 自己补上：否则任何一步失败后脚本都会继续跑完，留下一个没有 tup 的
        # build/，package() 再把它静默打成空包，直到 test_package 才以
        # `tup: command not found` (127) 报错——PR CI #90146 即如此。
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        cmd = (f"CC={cc} CFLAGS='-O2' TUP_SERVER=ldpreload TUP_LABEL={self.version} "
               f"{shell} -e ./build.sh")

        # build.sh 已把每个脆弱 spawn 的进程层级压到与普通编译步相同（patch 0001：
        # 去掉 retry_spawn 里的命令替换子 shell、把 link.sh 就地展开，见 notes.md #9），
        # 本层只做兜底：内层窗口（~13 分钟）耗尽后等更久再整棵重建，给同机其它构建
        # 让路。build.sh 开头 `rm -rf build`，重跑就是干净的全量重建。
        log_file = os.path.join(self.build_folder, "tup-build.log")
        rc_file = log_file + ".rc"
        for attempt in range(1, _BUILD_ATTEMPTS + 1):
            self.output.info("tup: build.sh attempt {}/{}, host: {}".format(
                attempt, _BUILD_ATTEMPTS, self._host_pressure()))
            status, output = self._run_logged(cmd, log_file, rc_file)

            missing = [name for name in _ARTIFACTS
                       if not os.path.isfile(os.path.join(self.source_folder, "build", name))]
            if status == 0 and not missing:
                return
            detail = ("exit {}".format(status) if status
                      else "missing {}".format(", ".join(missing)))

            exhaustion = status != 0 and self._spawn_spike(output)
            if exhaustion and attempt < _BUILD_ATTEMPTS:
                delay = 30 * attempt
                self.output.warning(
                    "tup: build.sh aborted by spawn-resource exhaustion ({}); "
                    "retrying in {}s".format(detail, delay))
                time.sleep(delay)
                continue
            if exhaustion:
                raise ConanException(
                    "tup: build.sh still aborted by spawn-resource exhaustion after "
                    "{} attempts ({}), host: {}; full output in {}".format(
                        _BUILD_ATTEMPTS, detail, self._host_pressure(), log_file))
            raise ConanException(
                "tup: build.sh failed ({}) on attempt {}, host: {}; "
                "full output in {}".format(detail, attempt, self._host_pressure(), log_file))

    def _run_logged(self, cmd, log_file, rc_file):
        """Run ``cmd``; returns (exit status, this attempt's output).

        The output is tee'd so it stays live on the CI console while the tail is
        also kept for triage, and the real status is carried out through fd 3:
        a pipeline reports tee's status, and POSIX sh has no ``pipefail``.
        """
        try:
            offset = os.path.getsize(log_file)
        except OSError:
            offset = 0
        self.run('exec 3>"{}"; {{ {} ; echo $? >&3 ; }} 2>&1 | tee -a "{}"; '
                 'exec 3>&-'.format(rc_file, cmd, log_file),
                 env="conanbuild", cwd=self.source_folder, ignore_errors=True)
        try:
            with open(rc_file) as handle:
                status = int(handle.read().strip() or 1)
        except (OSError, ValueError):
            status = 1
        try:
            with open(log_file, "rb") as handle:
                handle.seek(offset)
                output = handle.read().decode("utf-8", "replace")
        except OSError:
            output = ""
        return status, output

    @staticmethod
    def _spawn_spike(output):
        """True when ``output`` carries a spawn-resource failure signature."""
        low = output.lower()
        return any(marker in low for marker in _SPAWN_PRESSURE_MARKERS)

    @staticmethod
    def _host_pressure():
        """Snapshot the host's process pressure without forking.

        Reads /proc only: the moment a spawn fails with EAGAIN is exactly the
        wrong time to spawn a helper, so the diagnostics never fork.
        """
        bits = []
        try:
            with open("/proc/loadavg") as handle:
                bits.append("load=" + "/".join(handle.read().split()[:3]))
        except OSError:
            pass
        procs = 0
        try:
            for entry in os.listdir("/proc"):
                if entry.isdigit():
                    procs += 1
        except OSError:
            pass
        if procs:
            bits.append("procs={}".format(procs))
        return ", ".join(bits) or "n/a"

    def package(self):
        src = self.source_folder
        # tup-ldpreload.so 必须与 tup 同目录（depfile.c 按可执行文件路径推导）
        copy(self, "tup", os.path.join(src, "build"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "tup-ldpreload.so", os.path.join(src, "build"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

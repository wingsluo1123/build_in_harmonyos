#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fuse_tmp_write_guard.py — FUSE 临时目录写入被拒检测与预防（fuse-tmp-write-guard）

为什么需要它
------------
本仓库 OHOS PC 开发环境的工作目录挂载在 FUSE 文件系统上（HMDFS），存在一个
复合型平台陷阱（E046 的具体化变体）：

  1. **uid 映射错位**：进程以 uid A（如 20020084）运行，而 FUSE 显示的文件
     属主是 uid B（如 20001006）——进程对「属主显示为自己」的文件反而没有
     属主权限；
  2. **chmod 被静默忽略**（E046）：`chmod 777 x` 不报错但也**不生效**，无法
     事后补救；
  3. **umask 放大**：绝大多数 Unix 工具（autotools config.status、mktemp、
     cargo、cmake 临时区……）按惯例 `umask 077` 创建临时目录/文件，得到
     0700/0600 权限——在这种文件系统上，**创建者自己随即就写不进去**。

典型症状（构建日志特征行）：

    ./config.status[1101]: can't create ./confABFQpX/subs1.awk: Permission denied
    ./config.status: line 860: ./confflt9Qn/subs1.awk: Permission denied
    cmp: EOF on /tmp/cmdparseH82MfT after byte 0, line 0     # 写入失败导致空输出
    sh: can't create ./confrv3ITW/f1: Permission denied

已在两个独立包上实证（一类问题，非单库补丁）：

  * **oddjob 0.34.7**：`./configure` 的 config.status 在 mktemp -d 出的临时
    目录里写 subs1.awk 被拒 —— configure 阶段即失败（手工复现：
    `umask 077 && mktemp -d && echo > f` 直接 Permission denied）；
  * **oddjob 上游 tests/cmdparse**：test-cmdparse.sh 用 mktemp 建的输出文件
    写不进 → cmp 收到空文件 → 9 组向量全部 EOF 误报失败。

处理策略（本工具 -f/--fix 输出的建议，见 apply_fix）
--------------------------------------------------
  * **umask 000 环境注入**：对构建命令显式放宽 umask（0700/0600 不可写，
    但 000 创建的 0777/0666 目录任何 uid 均可写——FUSE 语义下这是唯一可靠
    的绕法）；
  * **构建目录迁移**：若注入 umask 不可行（如配方内部 spawn），把构建目录
    迁到非 FUSE 文件系统（如 /data/local/tmp）。

用法示例
--------
    # 只检测（扫构建日志 / 探测当前 FS 特性）
    python3 fuse_tmp_write_guard.py --log conan-create.log
    python3 fuse_tmp_write_guard.py --probe-fs /path/to/workdir

    # 检测 + 输出修复命令（JSON）
    python3 fuse_tmp_write_guard.py --log build.log --fix --json

退出码
------
    0 = 未命中（干净）；1 = 命中（日志含特征 / FS 探测证实 umask 陷阱）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys

# ---------------------------------------------------------------------------
# 检测特征：构建日志里 "Permission denied" 的 FUSE 临时目录形态。
# 四类证据行（按强度排序；匹配顺序即优先级——config.status 专属形态优先）：
#   L1 强证据：config.status 前缀（mksh `[pid]:` 或 bash `line NNN:`）+ conf* 目录
#   L2 强证据：通用 shell（sh:/bash:/裸）can't create ./conf*/...
#   L3 弱证据：cmp: EOF on <mktemp path> after byte 0（写入失败→空文件的下游）
# 命名特征：conf??????（autotools mktemp 惯例）、subs?.awk（config.status 专用）
LOG_PATTERNS = [
    (re.compile(r"config\.status[^\n]*can't create \S*conf[A-Za-z0-9]{6}\S*"
                r": Permission denied"),
     "L1", "config.status: mktemp 临时目录内写入被拒"),
    (re.compile(r"config\.status: line \d+: \S*conf[A-Za-z0-9]{6}\S*"
                r": Permission denied"),
     "L1", "config.status(bash): mktemp 临时目录内写入被拒"),
    (re.compile(r"can't create \S*conf[A-Za-z0-9]{6}\S*: Permission denied"),
     "L2", "shell: conf* 临时目录写入被拒"),
    (re.compile(r"cmp: EOF on \S*(cmdparse|tmp)\S* after byte 0"),
     "L3", "cmp 空文件对比失败（上游 mktemp 输出文件写入失败的下游症状）"),
]

# 源码特征：构建脚本/测试 harness 里 umask 077 + mktemp/mkdir 组合
SOURCE_PATTERNS = [
    (re.compile(r"umask\s+0?7[7]", re.M), "umask 077 创建临时区"),
    (re.compile(r"mktemp\s+(-d\s+)?[\"']?\.?/?\w+XXXXXX", re.M),
     "mktemp XXXXXX（配合 umask 077 即触发）"),
]

MKTEMP_RES = re.compile(r"^[d-][r-][w-][xSs-]{3}[r-][w-]{2}$")


def scan_log(text: str) -> list:
    """扫构建日志，返回命中的证据行列表 [(level, line, why)]。"""
    hits = []
    for line in text.splitlines():
        for pat, level, why in LOG_PATTERNS:
            if pat.search(line):
                hits.append((level, line.strip()[:300], why))
                break
    # 按强度稳定排序
    hits.sort(key=lambda h: h[0])
    return hits


def scan_source(text: str) -> list:
    """扫源码/脚本内容，返回 umask+mktemp 风险点 [(line_no, line, why)]。

    只有 umask 077 与 mktemp XXXXXX **同文件共现**才报（单独 mktemp 极常见，
    单独 umask 也未必配临时区——共现才是本陷阱的代码特征）。
    """
    lines = text.splitlines()
    umask_hits = [(i, ln.strip()[:200], "umask 077 创建临时区")
                  for i, ln in enumerate(lines, 1)
                  if re.search(r"umask\s+0?7[7]", ln)]
    mktemp_hits = [(i, ln.strip()[:200], "mktemp XXXXXX（配合 umask 077 即触发）")
                   for i, ln in enumerate(lines, 1)
                   if re.search(r"mktemp\s+(-d\s+)?[\"']?\.?/?\w*XXXXXX", ln)]
    if not umask_hits or not mktemp_hits:
        return []
    return sorted(umask_hits + mktemp_hits, key=lambda h: h[0])


def probe_fs(workdir: str) -> dict:
    """在 workdir 实测 FUSE umask 陷阱是否存在（不落业务文件，只建临时探针）。

    返回 {harness_vulnerable: bool, evidence: str, details: {...}}：
      1. umask 077 + mktemp -d 建目录 → 尝试写内层文件；
      2. 记录 chmod 前后 mode（chmod 无效则 stat 不变 → E046 佐证）。
    任何一步失败都会清理探针，不污染工作区。
    """
    details = {}
    vulnerable = False
    evidence = ""

    old_umask = os.umask(0o077)
    probe = None
    try:
        # ① umask 077 下建临时目录（模拟 config.status/mktemp 行为）
        prefix = os.path.join(workdir, ".fuseprobeXXXXXX")
        try:
            probe = _mkdtemp(prefix)
        except OSError as exc:
            details["mkdtemp"] = f"OSError: {exc}"
            return {"harness_vulnerable": False,
                    "evidence": f"mkdtemp 不可用: {exc}", "details": details}
        details["dir_mode"] = stat.filemode(os.stat(probe).st_mode)
        details["dir_uid_display"] = os.stat(probe).st_uid

        # ② 写内层文件（若 uid 映射错位，这里 Permission denied）
        inner = os.path.join(probe, "subs1.awk")
        try:
            with open(inner, "w") as fh:
                fh.write("probe\n")
            details["inner_write"] = "ok"
        except OSError as exc:
            details["inner_write"] = f"PermissionDenied: {exc}"
            vulnerable = True

        # ③ chmod 补救是否生效（E046：被静默忽略）
        if not vulnerable:
            try:
                os.chmod(probe, 0o777)
                mode_after = stat.filemode(os.stat(probe).st_mode)
                details["chmod_effective"] = (mode_after != details["dir_mode"])
                details["dir_mode_after_chmod"] = mode_after
            except OSError as exc:
                details["chmod_effective"] = f"OSError: {exc}"

        # ④ 对照组：umask 000 下**新建**目录并写入（证明问题由 umask+FUSE
        #    组合引发——0700 目录任何 uid 都不可写，000 目录可写）。
        #    注意不能往 0700 旧目录里写：那测的是目录权限而非 umask 效果。
        os.umask(0o000)
        probe_ok = None
        try:
            probe_ok = _mkdtemp(prefix)
            with open(os.path.join(probe_ok, "write.ok"), "w") as fh:
                fh.write("probe\n")
            details["umask000_write"] = "ok"
            # 证据文本必须与 vulnerable 结论一致（检视 Medium 修复）：
            # 仅 umask077 内层写入被拒时才可宣称"陷阱证实"，
            # 正常 FS（两层都可写）输出中性证据，避免自相矛盾输出误导使用者。
            if vulnerable:
                evidence = ("umask077 目录内写文件被拒；umask000 新建目录可写 → "
                            "FUSE umask 陷阱证实")
            else:
                evidence = ("umask077 与 umask000 目录均可写——未复现陷阱"
                            "（正常 FS 或 umask 未触发该平台组合）")
        except OSError as exc:
            details["umask000_write"] = f"PermissionDenied: {exc}"
            evidence = ("umask077 与 umask000 目录均不可写——非 umask 单因素，"
                        f"存在更广的权限问题（如实标注）: {exc}")
        finally:
            if probe_ok:
                _rmtree_ignore_errors(probe_ok)
    finally:
        os.umask(old_umask)
        if probe:
            _rmtree_ignore_errors(probe)

    return {"harness_vulnerable": vulnerable, "evidence": evidence,
            "details": details}


def _mkdtemp(prefix: str) -> str:
    """mkdtemp（要求 6 个 X，Python 会随机填充）。"""
    import tempfile
    return tempfile.mkdtemp(prefix=prefix.rsplit("XXXXXX", 1)[0],
                            suffix="", dir=os.path.dirname(prefix))


def _rmtree_ignore_errors(path: str) -> None:
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def suggest_fix() -> dict:
    """给出两段可直接执行的修复命令（umask 注入 / 目录迁移）。"""
    return {
        "umask_injection": (
            "umask 000 && <原构建命令>   "
            "# 例: umask 000 && ./configure ... && make   "
            "# 或在 conanfile build() 内: os.umask(0o000) 后再 spawn"),
        "build_dir_migration": (
            "把构建目录迁到非 FUSE 文件系统（如 /data/local/tmp 下），"
            "或将 OHC 构建根环境变量指向该目录"),
        "recipe_pattern": (
            "conanfile build() 若需写临时文件，用 "
            "os.umask(0o000) 包裹 mktemp/mkdir 段落，结束后恢复原 umask"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="FUSE 临时目录写入被拒检测（umask+uid 映射复合陷阱）")
    ap.add_argument("--log", action="append", default=[],
                    help="构建日志文件（可多次传入）")
    ap.add_argument("--source", action="append", default=[],
                    help="待检源码/脚本文件（可多次传入，检 umask+mktemp 共现）")
    ap.add_argument("--probe-fs", metavar="DIR",
                    help="在 DIR 实测 FUSE umask 陷阱（创建并清理临时探针）")
    ap.add_argument("--fix", action="store_true",
                    help="输出建议修复命令")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    result = {"skill": "fuse-tmp-write-guard", "hit": False,
              "log_hits": [], "source_hits": [], "fs_probe": None,
              "fix": None}

    for logf in args.log:
        try:
            with open(logf, "r", errors="replace") as fh:
                hits = scan_log(fh.read())
        except OSError as exc:
            hits = [("E", f"读取失败: {exc}", "log")]
        result["log_hits"].append({"file": logf, "hits": hits})
        if hits:
            result["hit"] = True

    for srcf in args.source:
        try:
            with open(srcf, "r", errors="replace") as fh:
                hits = scan_source(fh.read())
        except OSError as exc:
            hits = [(0, f"读取失败: {exc}", "source")]
        result["source_hits"].append({"file": srcf, "hits": hits})
        if hits:
            result["hit"] = True

    if args.probe_fs:
        if not os.path.isdir(args.probe_fs):
            result["fs_probe"] = {"error": f"目录不存在: {args.probe_fs}"}
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
        probe = probe_fs(args.probe_fs)
        result["fs_probe"] = probe
        if probe.get("harness_vulnerable"):
            result["hit"] = True

    if args.fix and result["hit"]:
        result["fix"] = suggest_fix()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "HIT" if result["hit"] else "CLEAN"
        print(f"[fuse-tmp-write-guard] {status}")
        for entry in result["log_hits"]:
            for lvl, line, why in entry["hits"]:
                print(f"  [{lvl}] {entry['file']}: {line}")
        for entry in result["source_hits"]:
            for no, line, why in entry["hits"]:
                print(f"  [S] {entry['file']}:{no}: {why} | {line}")
        if result["fs_probe"]:
            fp = result["fs_probe"]
            print(f"  [FS] vulnerable={fp.get('harness_vulnerable')} "
                  f"evidence={fp.get('evidence')}")
            print(f"  [FS] details={json.dumps(fp.get('details', {}), ensure_ascii=False)}")
        if result["fix"]:
            for k, v in result["fix"].items():
                print(f"  [FIX:{k}] {v}")

    return 1 if result["hit"] else 0


if __name__ == "__main__":
    sys.exit(main())

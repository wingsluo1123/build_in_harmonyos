#!/usr/bin/env python3
"""meson-cross-pkgconfig guard — meson 直驱交叉配方陷阱检测器.

语料来源（一类共性问题，≥2 例实证）：
  - sratom 0.6.22：G2 修复循环 5 轮（--default-library 映射 / 嵌套 $() 沙箱
    不稳 / 传递依赖 .pc 不生成 / backup 源钉死 / 兜底库名未核实）
  - lilv 0.28.0：套用同套策略后 G2 一次通过（仅 backup 源一坑重现）——
    策略可迁移性证明

三通道检测：
  L1 构建日志特征（事后归因）
  L2 配方反模式（建 PR 前预检）
  L3 环境陷阱（conan global.conf / 包缓存状态）

用法：
  meson_cross_pkgconfig_guard.py --log <build.log> [--log N ...]
  meson_cross_pkgconfig_guard.py --recipe <conanfile.py> [--recipe N ...]
  meson_cross_pkgconfig_guard.py --env [--conan-home <dir>]
  meson_cross_pkgconfig_guard.py --all --json -o <report.json>

输出规范：JSON（stdout 或 -o 文件）；日志一律写文件/内存，不走管道
（规避 SIGPIPE）；不写死任何本机路径（conan home 可传参，默认读 env）。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

# ---------------------------------------------------------------- L1 日志特征

LOG_SIGNATURES = [
    ("meson-no-shared-option",
     re.compile(r'ERROR: Unknown option: "shared"'),
     "上游 meson_options.txt 无 shared 选项——库形态必须用 "
    "--default-library=shared|static 全局开关表达（勿传 -Dshared=）"),
    ("meson-default-library-choice",
     re.compile(r"--default-library: invalid choice: '(?:true|false)'"),
     "meson --default-library 只接受 shared/static 字面量；conan bool "
    "选项须映射 true→shared / false→static"),
    ("pkgconfig-pc-missing",
     re.compile(r"was not found in the pkg-config search path"),
     "传递依赖的 .pc 未生成——test_package/消费者必须显式 requires 该包"
    "（仅靠传递依赖 PkgConfigDeps 不生成其 .pc）"),
    ("linker-lib-not-found",
     re.compile(r"unable to find library -l(\S+)"),
     "硬编码兜底库名未核实——库文件名可能带版本后缀（如 libzix-0 而非 "
    "libzix）；兜底 -l 前先 ls 依赖 lib 目录核实命名"),
    ("hmdfs-shared-load-fail",
     re.compile(r"Error loading shared library (\S+)"),
     "HMDFS exec 陷阱族：meson install --destdir 重写过的 .so 可能加载"
    "失败（内容决定可执行性）——改用构建目录 ld 直出版验证"),
    ("conan-source-backup-block",
    re.compile(r"not found in remote backup \S+"),
     "conan global.conf core.sources:download_urls 钉死本地 backup 源且"
    "未回退原始 URL——临时注释该行跑 source()，验证后还原"),
]


def scan_log(path: str) -> list[dict]:
    hits: list[dict] = []
    try:
        with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                for sig_id, pattern, advice in LOG_SIGNATURES:
                    m = pattern.search(line)
                    if m:
                        hits.append({
                            "channel": "L1-log",
                            "signature": sig_id,
                            "file": path,
                            "line": lineno,
                            "evidence": line.strip()[:200],
                            "advice": advice,
                        })
    except OSError as exc:
        hits.append({"channel": "L1-log", "signature": "io-error",
                     "file": path, "evidence": str(exc)[:200],
                     "advice": "日志文件不可读"})
    return hits


# ------------------------------------------------------------ L2 配方反模式

RECIPE_ANTI_PATTERNS = [
    ("nested-pkgconfig-substitution",
     re.compile(r'self\.run\([^)]*\$\(PKG_CONFIG_PATH[^)]*pkg-config'),
     "self.run 内嵌套 \"$(pkg-config ...)\" 子 shell 展开在 conan 沙箱"
    "不稳定——改两步法：pkg-config 输出落盘文件，Python 读回字面量 flags"),
    ("dash-d-shared-option",
     re.compile(r"-Dshared=(?:true|false)"),
     "-Dshared= 传给了没有该选项的 meson 项目——用 --default-library="),
    ("hardcoded-fallback-lib",
     re.compile(r"-l(zix|serd|sord|lv2)(?!-0)\b"),
     "兜底库名未带上游版本后缀（lv2 生态库实体名是 lib<name>-0）——"
    "兜底 -l 前先核实依赖 lib 目录命名，勿凭直觉补 -l"),
]


def scan_recipe(path: str) -> list[dict]:
    hits: list[dict] = []
    try:
        with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                for sig_id, pattern, advice in RECIPE_ANTI_PATTERNS:
                    if pattern.search(line):
                        hits.append({
                            "channel": "L2-recipe",
                            "signature": sig_id,
                            "file": path,
                            "line": lineno,
                            "evidence": line.strip()[:200],
                            "advice": advice,
                        })
    except OSError as exc:
        hits.append({"channel": "L2-recipe", "signature": "io-error",
                     "file": path, "evidence": str(exc)[:200],
                     "advice": "配方文件不可读"})
    return hits


# ---------------------------------------------------------------- L3 环境陷阱

def scan_env(conan_home: str | None = None) -> list[dict]:
    hits: list[dict] = []
    home = conan_home or os.environ.get("CONAN_HOME") or os.path.expanduser(
        "~/.conan2")
    conf = os.path.join(home, "global.conf")
    try:
        with io.open(conf, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if "core.sources:download_urls" in line and not line.startswith(
                        "#"):
                    hits.append({
                        "channel": "L3-env",
                        "signature": "source-download-urls-pinned",
                        "file": conf,
                        "line": lineno,
                        "evidence": line.strip()[:200],
                        "advice": "源下载被钉死（通常指向本地 backup），"
                                  "新包 source() 会 NotFoundException——"
                                  "临时注释跑 conan create，验证后还原",
                    })
    except OSError:
        hits.append({"channel": "L3-env", "signature": "conf-missing",
                     "file": conf, "evidence": "global.conf 不可读",
                     "advice": "无 global.conf 属正常新环境"})
    return hits


# -------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="meson 直驱交叉配方陷阱检测器（L1 日志 / L2 配方 / "
                    "L3 环境）")
    parser.add_argument("--log", action="append", default=[],
                        help="构建日志文件（可多次）")
    parser.add_argument("--recipe", action="append", default=[],
                        help="conanfile.py（可多次）")
    parser.add_argument("--env", action="store_true",
                        help="检查 conan global.conf / 环境陷阱")
    parser.add_argument("--conan-home", default=None,
                        help="conan home 目录（默认 $CONAN_HOME 或 ~/.conan2）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("-o", "--out", default=None,
                        help="报告写文件（推荐，规避管道 SIGPIPE）")
    args = parser.parse_args(argv)

    hits: list[dict] = []
    for p in args.log:
        hits.extend(scan_log(p))
    for p in args.recipe:
        hits.extend(scan_recipe(p))
    if args.env:
        hits.extend(scan_env(args.conan_home))

    report = {"tool": "meson-cross-pkgconfig-guard", "hit_count": len(hits),
              "hits": hits}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"report written: {args.out} (hits={len(hits)})")
    else:
        # 无 -o 时 stdout 直写，捕获 BrokenPipeError 防 SIGPIPE 崩溃
        try:
            sys.stdout.write(text + "\n")
        except BrokenPipeError:
            try:
                sys.stdout.close()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

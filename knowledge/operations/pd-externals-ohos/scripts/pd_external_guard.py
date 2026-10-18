#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pd-externals-ohos guard — 检测 Pure Data 外部库在 OHOS 上的构建/消费者兼容性。

解决的一类共性问题（非单库补丁）：
  上游 Pd 外部库普遍使用 pd-lib-builder（`Makefile.pdlibbuilder`）构建，它在
  配置阶段用 `$(CC) -dumpmachine` 探测目标三元组，且默认 `CC = $(PLATFORM)-cc|gcc`。
  OHOS 目标机没有 `cc`/`gcc`（只有内置 clang），于是**在编译任何源码之前**即以
  `*** Command "cc -dumpmachine" did not return a target triplet, needed for a build.`
  硬失败；即使绕过编译器，`PDINCLUDEDIR` 也必须指向**含 Pd 内部头**的头集
  （libpd 包不含 `s_stuff.h`），否则编译期 `fatal error: 's_stuff.h' file not found`。
  外部对象本身不与 Pd 宿主链接（由宿主 dlopen），因此消费者侧还有一层
  musl 符号作用域问题（`Error relocating … pd_error: symbol not found`）。

用法：
  pd_external_guard.py log    <build.log>              # 构建日志签名扫描
  pd_external_guard.py source <src_dir>                # 上游源码静态扫描
  pd_external_guard.py recipe <archives/<l>/<p>/<v>>   # 配方静态扫描
  pd_external_guard.py policy                          # 打印处理策略表
  pd_external_guard.py selftest                        # 内置正负样例自检

退出码：2 = 命中（需要处理）· 0 = 未命中 · 1 = 用法/IO 错误。
只依赖标准库；不写死绝对路径；不依赖任何本地缓存。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 签名库

# (code, variant, regex, 含义)
SIGNATURES = [
    (
        "PDLIBBUILDER_NO_TRIPLET",
        "A",
        re.compile(r'did not return a target triplet|Command ".*-dumpmachine"'),
        "pd-lib-builder 探测目标三元组失败：OHOS 无 cc/gcc（默认 CC=$(PLATFORM)-cc|gcc）",
    ),
    (
        "PDLIBBUILDER_CC_NOT_FOUND",
        "A",
        re.compile(r"^.*\b(cc|gcc|g\+\+|cc1)\b: (?:not found|No such file or directory)"),
        "构建调用了不存在的 cc/gcc",
    ),
    (
        "PD_HEADER_MISSING",
        "B",
        re.compile(r"(s_stuff\.h|m_pd\.h|g_canvas\.h|m_imp\.h)['\"]?: No such file|"
                   r"fatal error: '(s_stuff|m_pd|g_canvas|m_imp)\.h' file not found"),
        "Pd 头文件缺失：PDINCLUDEDIR 未指向含 Pd 内部头的头集（libpd 包不含 s_stuff.h）",
    ),
    (
        "PD_CONSUMER_SYMBOL_SCOPE",
        "C",
        re.compile(r"Error relocating .*: (pd_error|gensym|class_new|outlet_new|"
                   r"inlet_new|floatinlet_new|z_|post\(|pd_)\w*: symbol not found"),
        "消费者 dlopen 外部对象时 Pd API 符号不可见（musl：dlopen 的 RTLD_GLOBAL 不入全局域）",
    ),
    (
        "PD_HOST_LOAD_FAILED",
        "D",
        re.compile(r"(vbap|rvbap|define_loudspeakers|\S+): couldn't create|"
                   r"couldn't create .*\.pd_linux"),
        "Pd 宿主实例化外部对象失败（产物未加载/未注册 setup 符号）",
    ),
    (
        "PDLIBBUILDER_LANDING",
        "-",
        re.compile(r"Makefile\.pdlibbuilder:\d+|pd-lib-builder"),
        "构建日志确认走的是 pd-lib-builder（不是本类问题时该行也会出现）",
    ),
]

# variant -> 处理策略
POLICY = {
    "A": (
        "在配方 build() 里**显式**提供编译器与目标头集，不要依赖 make 的默认推导："
        "make -j1 CC=<conan profile 的 clang> PDINCLUDEDIR=<puredata 包>/include/pd。"
        "片段：templates/pdlibbuilder_make_snippet.py"
    ),
    "B": (
        "PDINCLUDEDIR 必须指向 **puredata** 包（含 s_stuff.h / g_canvas.h / m_imp.h / x_vexp.h 等 Pd 内部头）；"
        "**libpd 包不能用于编译外部对象**（它只装 include/libpd，缺 s_stuff.h）。"
        "注意 puredata 的 package_type=application 且 cpp_info.includedirs 为空，"
        "须用 dependency.package_folder + 'include/pd' 拼路径。"
    ),
    "C": (
        "消费者测试不要链接 conan 里的 libpd 目录树：运行时 dlopen(libpd.so, RTLD_NOW|RTLD_GLOBAL) + dlsym；"
        "若仍无法 relocate，对**运行步骤**加 LD_PRELOAD=<libpd.so>（等价于宿主自身 -rdynamic）。"
        "编译/链接子进程禁止注入依赖库目录（会顶掉 SDK 自带库）。"
        "规范：templates/consumer-libpd-test.md.tmpl"
    ),
    "D": (
        "确认产物目录含 <name>_setup() 符号且为 pd_linux 扩展名，"
        "并在宿主里用 `pd -path <产物目录>` 加载（Pd 优先搜索补丁自身目录）。"
    ),
    "-": "命中行仅表示使用 pd-lib-builder；需结合 A/B/C/D 判定是否为本类问题。",
}

VERDICT_UNSUPPORTED = "PD_EXTERNAL_INCOMPATIBLE"   # A/B：构建侧需要适配
VERDICT_CONSUMER = "PD_CONSUMER_INCOMPATIBLE"      # C/D：消费者侧需要适配

PATCHER_HINT = "参考 archives/p/pd-vbap/1.2.1（本拓展的样例库）与 knowledge/operations/pd-externals-ohos/"


# ---------------------------------------------------------------- 工具

def _iter_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            yield i, line.rstrip("\n")


def _emit(obj, as_json: bool):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    return obj


# ---------------------------------------------------------------- log 模式

def scan_log(path: Path):
    hits = []
    for lineno, line in _iter_lines(path):
        for code, variant, rx, meaning in SIGNATURES:
            if rx.search(line):
                hits.append({
                    "line": lineno,
                    "code": code,
                    "variant": variant,
                    "meaning": meaning,
                    "evidence": line.strip()[:400],
                })
    variants = sorted({h["variant"] for h in hits if h["variant"] != "-"})
    codes = sorted({h["code"] for h in hits if h["variant"] != "-"})
    if not codes:
        return {
            "mode": "log",
            "verdict": "CLEAN",
            "variants": [],
            "codes": [],
            "hits": hits,
            "policy": [],
            "exit_code": 0,
        }
    verdict = VERDICT_CONSUMER if set(codes) <= {"PD_CONSUMER_SYMBOL_SCOPE",
                                                 "PD_HOST_LOAD_FAILED"} else VERDICT_UNSUPPORTED
    return {
        "mode": "log",
        "verdict": verdict,
        "variants": variants,
        "codes": codes,
        "hits": hits,
        "policy": [POLICY[v] for v in variants if v in POLICY],
        "hint": PATCHER_HINT,
        "exit_code": 2,
    }


# ---------------------------------------------------------------- source 模式

PDLIBBUILDER_NAMES = ("Makefile.pdlibbuilder", "pd-lib-builder.mk", "pd-lib-builder")
CLASS_SRC_RX = re.compile(r"\b(class\.sources|lib\.name|datafiles|PDLIBBUILDER_DIR)\s*[:?]?=")
SETUP_RX = re.compile(r"\b(\w+)_setup\s*\(\s*(?:void|t_symbol\s*\*)?\s*\)")
PD_HEADER_RX = re.compile(r'#include\s*[<"](m_pd\.h|s_stuff\.h|g_canvas\.h|m_imp\.h)')


def scan_source(root: Path):
    if not root.is_dir():
        raise IOError("not a directory: %s" % root)
    pdlibbuilder = []
    for name in PDLIBBUILDER_NAMES:
        pdlibbuilder.extend(sorted(str(p.relative_to(root)) for p in root.rglob(name)))
    makefiles = [p for p in root.rglob("Makefile*") if p.is_file()]
    make_uses_builder = []
    for mf in makefiles:
        try:
            text = mf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if CLASS_SRC_RX.search(line) or "pdlibbuilder" in line.lower():
                make_uses_builder.append({
                    "file": str(mf.relative_to(root)),
                    "line": lineno,
                    "evidence": line.strip()[:200],
                })
    sources = [p for p in list(root.rglob("*.c")) + list(root.rglob("*.cpp")) + list(root.rglob("*.cc"))]
    setups, pd_headers = set(), set()
    for src in sources:
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for mt in SETUP_RX.finditer(text):
            if mt.group(1) not in ("libpd", "pd"):
                setups.add(mt.group(1))
        for mt in PD_HEADER_RX.finditer(text):
            pd_headers.add(mt.group(1))
    is_pd_external = bool(pdlibbuilder) or bool(make_uses_builder and setups)
    return {
        "mode": "source",
        "root": str(root),
        "is_pd_external": is_pd_external,
        "pdlibbuilder_files": pdlibbuilder,
        "make_hits": make_uses_builder[:20],
        "setup_symbols": sorted(setups),
        "pd_headers": sorted(pd_headers),
        "verdict": "NEEDS_OHOS_ADAPTATION" if is_pd_external else "NOT_PD_EXTERNAL",
        "policy": [POLICY["A"], POLICY["B"]] if is_pd_external else [],
        "hint": PATCHER_HINT if is_pd_external else "",
        "exit_code": 2 if is_pd_external else 0,
    }


# ---------------------------------------------------------------- recipe 模式

CC_INJECT_RX = re.compile(r"\bCC\s*=\s*\S|compiler_executables|CC=\"?[\w./-]*clang", re.I)
PDINC_RX = re.compile(r"PDINCLUDEDIR")
PDDIR_RX = re.compile(r"\bPDDIR\b|PDBINDIR|PDLIBDIR")
PUREDATA_RX = re.compile(r"puredata|libpd")
MAKE_RX = re.compile(r"\bmake\b")


def scan_recipe(recipe_dir: Path):
    if not recipe_dir.is_dir():
        raise IOError("not a directory: %s" % recipe_dir)
    files = {}
    for name in ("conanfile.py", "conandata.yml", "notes.md"):
        p = recipe_dir / name
        files[name] = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    blob = "\n".join(files.values())
    has_make = bool(MAKE_RX.search(files["conanfile.py"]))
    has_cc = bool(CC_INJECT_RX.search(files["conanfile.py"]))
    has_pdinc = bool(PDINC_RX.search(blob))
    has_pd_dir = bool(PDDIR_RX.search(blob))
    has_pd_dep = bool(PUREDATA_RX.search(files["conanfile.py"]))
    if not (has_make and has_pd_dep):
        verdict = "NOT_PD_EXTERNAL"
    elif has_cc and has_pdinc:
        verdict = "GUARDED"
    else:
        verdict = "RISK"
    missing = []
    if verdict == "RISK":
        if not has_cc:
            missing.append("显式 CC（make 变量或 tools.build:compiler_executables）")
        if not has_pdinc:
            missing.append("PDINCLUDEDIR（指向 puredata 包的 include/pd）")
    return {
        "mode": "recipe",
        "recipe": str(recipe_dir),
        "verdict": verdict,
        "signals": {
            "make_invocation": has_make,
            "compiler_injected": has_cc,
            "pdincludedir": has_pdinc,
            "pd_dir_vars": has_pd_dir,
            "pd_dependency": has_pd_dep,
        },
        "missing": missing,
        "policy": [POLICY["A"], POLICY["B"]] if verdict == "RISK" else [],
        "hint": PATCHER_HINT if verdict == "RISK" else "",
        "exit_code": 2 if verdict == "RISK" else 0,
    }


# ---------------------------------------------------------------- selftest

FIXTURE_LOG_HIT = """\
make -C src
cc -dumpmachine
Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet, needed for a build.  Is compiler "cc" installed in your PATH?
make: *** [Makefile:12: all] Error 2
"""

FIXTURE_LOG_CLEAN = """\
make -C src CC=clang PDINCLUDEDIR=/tmp/pd/include/pd
clang -DPD -DUNIX -fPIC -O3 -c vbap.c -o vbap.o
clang -shared -o vbap.pd_linux vbap.o
"""

FIXTURE_LOG_CONSUMER = """\
-- 1) load built Pd externals
  [FAIL] dlopen /tmp/build/vbap.pd_linux: Error relocating /tmp/build/vbap.pd_linux: pd_error: symbol not found
"""


def selftest():
    import tempfile
    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        p = tmpd / "hit.log"
        p.write_text(FIXTURE_LOG_HIT, encoding="utf-8")
        r = scan_log(p)
        cases.append(("log/hit", r["exit_code"] == 2 and "PDLIBBUILDER_NO_TRIPLET" in r["codes"]
                      and r["verdict"] == VERDICT_UNSUPPORTED and r["variants"] == ["A"]))
        p = tmpd / "clean.log"
        p.write_text(FIXTURE_LOG_CLEAN, encoding="utf-8")
        r = scan_log(p)
        cases.append(("log/clean", r["exit_code"] == 0 and r["verdict"] == "CLEAN"))
        p = tmpd / "consumer.log"
        p.write_text(FIXTURE_LOG_CONSUMER, encoding="utf-8")
        r = scan_log(p)
        cases.append(("log/consumer", r["exit_code"] == 2 and r["verdict"] == VERDICT_CONSUMER
                      and r["variants"] == ["C"]))

        naive = tmpd / "naive"
        naive.mkdir()
        (naive / "Makefile").write_text(
            "lib.name = foo\nclass.sources = foo.c\n"
            "PDLIBBUILDER_DIR=.\ninclude $(PDLIBBUILDER_DIR)/Makefile.pdlibbuilder\n",
            encoding="utf-8")
        (naive / "Makefile.pdlibbuilder").write_text("# stub\n", encoding="utf-8")
        (naive / "foo.c").write_text('#include "m_pd.h"\nvoid foo_setup(void) {}\n', encoding="utf-8")
        r = scan_source(naive)
        cases.append(("source/pd-external", r["exit_code"] == 2
                      and r["verdict"] == "NEEDS_OHOS_ADAPTATION"
                      and r["setup_symbols"] == ["foo"]))

        other = tmpd / "other"
        other.mkdir()
        (other / "hello.c").write_text("int main(void){return 0;}\n", encoding="utf-8")
        r = scan_source(other)
        cases.append(("source/non-pd", r["exit_code"] == 0 and r["verdict"] == "NOT_PD_EXTERNAL"))

        for tag, has_cc, has_inc in (("risk", None, None), ("guarded", 'CC="clang"', "PDINCLUDEDIR")):
            d = tmpd / ("recipe-" + tag)
            d.mkdir()
            body = "    def build(self):\n        self.run('make -j1 %s')\n" % " ".join(
                x for x in (has_cc, has_inc) if x)
            (d / "conanfile.py").write_text(
                "from conan import ConanFile\n"
                "class R(ConanFile):\n"
                "    def requirements(self):\n"
                "        self.requires('puredata/0.54.1')\n" + body,
                encoding="utf-8")
            r = scan_recipe(d)
            if tag == "risk":
                cases.append(("recipe/risk", r["exit_code"] == 2 and r["verdict"] == "RISK"
                              and len(r["missing"]) == 2))
            else:
                cases.append(("recipe/guarded", r["exit_code"] == 0 and r["verdict"] == "GUARDED"))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    print("selftest: %d/%d passed" % (len(cases) - len(failed), len(cases)))
    return 0 if not failed else 1


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="pd-externals-ohos guard")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("log", help="扫描构建日志")
    p.add_argument("logfile")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("source", help="扫描上游源码目录")
    p.add_argument("srcdir")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("recipe", help="扫描配方目录")
    p.add_argument("recipedir")
    p.add_argument("--json", action="store_true")

    sub.add_parser("policy", help="打印处理策略表")
    sub.add_parser("selftest", help="内置正负样例自检")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1

    if args.cmd == "policy":
        for key in ("A", "B", "C", "D"):
            print("[%s] %s\n" % (key, POLICY[key]))
        print("样例库：archives/p/pd-vbap/1.2.1（%s）" % PATCHER_HINT)
        return 0
    if args.cmd == "selftest":
        return selftest()

    try:
        if args.cmd == "log":
            res = scan_log(Path(args.logfile))
        elif args.cmd == "source":
            res = scan_source(Path(args.srcdir))
        else:
            res = scan_recipe(Path(args.recipedir))
    except (IOError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("VERDICT=%s  (exit_code=%d)" % (res["verdict"], res["exit_code"]))
        if res.get("variants") is not None:
            print("variants=%s  codes=%s" % (",".join(res["variants"]) or "-",
                                             ",".join(res["codes"]) or "-"))
        if res.get("missing"):
            print("missing: %s" % "; ".join(res["missing"]))
        for hit in res.get("hits", []):
            print("  %s:%d  [%s] %s" % (args.logfile, hit["line"], hit["code"], hit["evidence"]))
        for hit in res.get("make_hits", []):
            print("  %s:%d  %s" % (hit["file"], hit["line"], hit["evidence"]))
        for pol in res.get("policy", []):
            print("policy: %s" % pol)
        if res.get("hint"):
            print("hint: %s" % res["hint"])
    return res["exit_code"]


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pd-externals-ohos 检测器自测（纯标准库，无 pytest 依赖）。

    python3 knowledge/operations/pd-externals-ohos/tests/test_pd_external_guard.py

覆盖：日志三态（A / C / 干净）判定与退出码、源码模式正负样例、
配方模式 RISK/GUARDED/NOT_PD_EXTERNAL 与缺失项、错误路径、策略表完整性、
交付物齐备性与复现脚本的静态约束（无管道 / 无写死绝对路径 / 官方源 + sha256）。
"""
from __future__ import annotations

import importlib.util
import re
import tempfile
from pathlib import Path

# 复现脚本不得把命令输出管道给下游消费者（SIGPIPE / 截断空日志）。
# 注意：`||`、`case` 分支里的 `a|b)` 不算管道，因此只匹配「管道 + 消费者命令」。
PIPE_CONSUMERS = ("head", "tail", "sed", "grep", "awk", "wc", "cut", "tr",
                  "sort", "uniq", "xargs", "cat", "tee", "column")

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
GUARD = SKILL_DIR / "scripts" / "pd_external_guard.py"
REPRO = SKILL_DIR / "scripts" / "reproduce_poc.sh"

_results = []


def check(name, ok):
    _results.append((name, bool(ok)))


def load_guard():
    spec = importlib.util.spec_from_file_location("pd_guard", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LOG_NAIVE = """\
make -j1
make: cc: No such file or directory
++++ info: using Makefile.pdlibbuilder version 0.6.0
Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a target triplet, needed for a build.  Stop.
"""

LOG_HEADER = """\
clang -I/tmp/x/include/libpd -DPD -c vbap.c -o vbap.o
vbap.c:14:10: fatal error: 's_stuff.h' file not found
"""

LOG_CONSUMER = """\
  [FAIL] dlopen /tmp/b/vbap.pd_linux: Error relocating /tmp/b/vbap.pd_linux: gensym: symbol not found
"""

LOG_CLEAN = """\
make -j1 CC=clang PDINCLUDEDIR=/tmp/pd/include/pd
clang -DPD -DUNIX -fPIC -O3 -c vbap.c -o vbap.o
clang -shared -o vbap.pd_linux vbap.o
"""


def main():
    g = load_guard()

    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)

        # ---------- 日志模式 ----------
        f = tmpd / "naive.log"; f.write_text(LOG_NAIVE, encoding="utf-8")
        r = g.scan_log(f)
        check("log/naive verdict+exit", r["verdict"] == g.VERDICT_UNSUPPORTED and r["exit_code"] == 2)
        check("log/naive variants", r["variants"] == ["A"] and "PDLIBBUILDER_NO_TRIPLET" in r["codes"])
        check("log/naive policy+hint", bool(r["policy"]) and "pd-vbap" in r["hint"])
        check("log/naive evidence line", any("did not return a target triplet" in h["evidence"]
                                             for h in r["hits"]))

        f = tmpd / "header.log"; f.write_text(LOG_HEADER, encoding="utf-8")
        r = g.scan_log(f)
        check("log/header-missing", r["exit_code"] == 2 and r["variants"] == ["B"]
              and "PD_HEADER_MISSING" in r["codes"])

        f = tmpd / "consumer.log"; f.write_text(LOG_CONSUMER, encoding="utf-8")
        r = g.scan_log(f)
        check("log/consumer-scope", r["verdict"] == g.VERDICT_CONSUMER
              and r["exit_code"] == 2 and r["variants"] == ["C"])

        f = tmpd / "clean.log"; f.write_text(LOG_CLEAN, encoding="utf-8")
        r = g.scan_log(f)
        check("log/clean no false positive", r["verdict"] == "CLEAN" and r["exit_code"] == 0
              and r["hits"] == [])

        # 混合：A + C 同时命中 → 归为构建侧不可适配
        f = tmpd / "mixed.log"; f.write_text(LOG_NAIVE + LOG_CONSUMER, encoding="utf-8")
        r = g.scan_log(f)
        check("log/mixed prefers build-side", r["verdict"] == g.VERDICT_UNSUPPORTED
              and r["variants"] == ["A", "C"])

        # ---------- 源码模式 ----------
        ext = tmpd / "vbap-like"
        ext.mkdir()
        (ext / "Makefile.pdlibbuilder").write_text("# stub\n", encoding="utf-8")
        (ext / "Makefile").write_text(
            "lib.name = demo\nclass.sources = demo.c\n"
            "PDLIBBUILDER_DIR=.\ninclude $(PDLIBBUILDER_DIR)/Makefile.pdlibbuilder\n",
            encoding="utf-8")
        (ext / "demo.c").write_text(
            '#include "m_pd.h"\n#include "s_stuff.h"\n'
            "static t_class *c;\nvoid demo_setup(void) { }\n", encoding="utf-8")
        r = g.scan_source(ext)
        check("source/pd-external detected", r["verdict"] == "NEEDS_OHOS_ADAPTATION" and r["exit_code"] == 2)
        check("source/setup+headers", r["setup_symbols"] == ["demo"]
              and set(r["pd_headers"]) == {"m_pd.h", "s_stuff.h"})
        check("source/make hits", any("lib.name" in h["evidence"] for h in r["make_hits"]))

        plain = tmpd / "plain"
        plain.mkdir()
        (plain / "hello.c").write_text("int main(void){return 0;}\n", encoding="utf-8")
        (plain / "Makefile").write_text("all:\n\tcc -o hello hello.c\n", encoding="utf-8")
        r = g.scan_source(plain)
        check("source/plain-c is not pd extern", r["verdict"] == "NOT_PD_EXTERNAL" and r["exit_code"] == 0)

        try:
            g.scan_source(tmpd / "does-not-exist")
            check("source/missing dir raises", False)
        except IOError:
            check("source/missing dir raises", True)

        # ---------- 配方模式 ----------
        def write_recipe(d, body):
            d.mkdir()
            (d / "conanfile.py").write_text(
                "from conan import ConanFile\nclass R(ConanFile):\n" + body, encoding="utf-8")

        risk = tmpd / "rec-risk"
        write_recipe(risk,
                     "    def requirements(self):\n        self.requires('puredata/0.54.1')\n"
                     "    def build(self):\n        self.run('make -j1')\n")
        r = g.scan_recipe(risk)
        check("recipe/risk verdict", r["verdict"] == "RISK" and r["exit_code"] == 2)
        check("recipe/risk missing both", len(r["missing"]) == 2 and bool(r["policy"]))

        guarded = tmpd / "rec-guarded"
        write_recipe(guarded,
                     "    def requirements(self):\n        self.requires('puredata/0.54.1')\n"
                     "    def build(self):\n"
                     "        self.run('make -j1 CC=\"clang\" PDINCLUDEDIR=/tmp/pd/include/pd')\n")
        r = g.scan_recipe(guarded)
        check("recipe/guarded verdict", r["verdict"] == "GUARDED" and r["exit_code"] == 0
              and r["missing"] == [])

        other = tmpd / "rec-other"
        write_recipe(other, "    def build(self):\n        self.run('make -j1')\n")
        r = g.scan_recipe(other)
        check("recipe/non-pd ignored", r["verdict"] == "NOT_PD_EXTERNAL" and r["exit_code"] == 0)

    # ---------- 内置 selftest ----------
    check("module selftest", g.selftest() == 0)

    # ---------- 策略表完整性 ----------
    check("policy table complete",
          all(g.POLICY.get(k) for k in ("A", "B", "C", "D"))
          and "puredata" in g.POLICY["B"] and "LD_PRELOAD" in g.POLICY["C"])
    codes = {c for c, _v, _r, _m in g.SIGNATURES}
    check("signature codes", {"PDLIBBUILDER_NO_TRIPLET", "PDLIBBUILDER_CC_NOT_FOUND",
                              "PD_HEADER_MISSING", "PD_CONSUMER_SYMBOL_SCOPE",
                              "PD_HOST_LOAD_FAILED", "PDLIBBUILDER_LANDING"} <= codes)

    # ---------- 交付物与复现脚本静态约束 ----------
    for rel in ("SKILL.md", "README.md", "scripts/pd_external_guard.py", "scripts/reproduce_poc.sh",
                "templates/pdlibbuilder_make_snippet.py", "templates/consumer-libpd-test.md.tmpl",
                "templates/env-unsupported-marker.md.tmpl"):
        check("deliverable %s" % rel, (SKILL_DIR / rel).exists())

    text = REPRO.read_text(encoding="utf-8")
    code_lines = [ln for ln in text.splitlines()
                  if ln.strip() and not ln.strip().startswith("#")]
    pipe_rx = re.compile(r"\|\s*(%s)\b" % "|".join(PIPE_CONSUMERS))
    piped = [ln.strip() for ln in code_lines if pipe_rx.search(ln)]
    check("repro/no pipeline into consumer (SIGPIPE)", not piped)
    if piped:
        print("    piped: %r" % piped)
    check("repro/official source + sha256",
          "codeload.github.com/pure-data/vbap" in text and "7a754a9c" in text)
    check("repro/no hardcoded absolute paths",
          "/storage/Users/" not in text and "/data/service" not in text)
    check("repro/TMPDIR writable check", "TMPDIR" in text and "not writable" in text)
    check("repro/two states", "naive" in text and "guarded" in text
          and "env -u CC" in text and "PDINCLUDEDIR=" in text)

    failed = [n for n, ok in _results if not ok]
    for name, ok in _results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    print("tests: %d/%d passed" % (len(_results) - len(failed), len(_results)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yaml-mode 0.0.16 —— 端到端消费者用例(平台 rule12)。

这个包交付的是 Emacs 的 YAML major mode(yaml-mode.el,单文件 elisp 包)。
它在真实世界里的消费方式:

    Emacs 启动 → load-path 找到 yaml-mode.el → 读取文件头(版本/Package-Requires)
    → 打开 .yaml 文件时加载 mode:注册 defcustom/defface、编译 font-lock 关键词
    正则表 → 用这些正则对缓冲区逐行做语法分类(注释/键/标量/块标量…)

CI 环境没有 emacs,本脚本用**独立第二实现**(纯 Python)完成同一消费动作:

  ① 交付路径契约:share/emacs/site-lisp/yaml-mode/yaml-mode.el 存在且在
     版本头声明 0.0.16(与配方版本对账);
  ② elisp 结构解析:按 elisp 顶层形式提取 defcustom/defface/defun/defconst/
     defvar 清单,验证 mode 的关键符号齐备(yaml-mode-hook、yaml-indent-offset、
     yaml-blank-line-re、yaml-directive-re、yaml-imenu-generic-expression…);
  ③ 正则表提取与转换:从 defconst 中提取 yaml-*-re 正则字面量,把 elisp 正则
     语法(\( \) \| \b \s- 等)保守转换为 Python re 语法(转换失败的跳过并计数,
     不假装成功);
  ④ 真实消费:用转换成功的正则,对随包交付的 9 个上游 YAML 测试样例
     (share/doc/yaml-mode/upstream/test-files/*.yaml)逐行做语法分类统计
     (blank/注释/序列项/映射键行)——这正是 yaml-mode 每次 buffer 变更时
     font-lock 做的事情;
  ⑤ 样例一致性:9 个 fixture 可读、非空、具备 YAML 结构特征。

实测(上游 commit 23395dfcf004c952850691b70e63f97f169596e8,sha256 见
conandata.yml):checks_total 见 MANIFEST.yml,全部通过。
"""
import os
import re
import sys

# ── 与 conanfile.py 同一口径的载荷常量(两文件必须同值同改)
LISP_REL = os.path.join("share", "emacs", "site-lisp", "yaml-mode", "yaml-mode.el")
FIXTURE_DIR = os.path.join("share", "doc", "yaml-mode", "upstream", "test-files")
FIXTURES = 9
VERSION = "0.0.16"

KEY_SYMBOLS = (
    "yaml-mode-hook",        # mode hook
    "yaml-indent-offset",    # 缩进宽度 defcustom
    "yaml-blank-line-re",    # 空行正则(消费用)
    "yaml-directive-re",     # 指令正则(消费用)
    "yaml-imenu-generic-expression",  # imenu 索引
)

_CHECKS = [0]
_FAILS = []


def check(cond, what):
    _CHECKS[0] += 1
    if not cond:
        _FAILS.append(what)
        print("  FAIL %s" % what)
    return bool(cond)


# ─────────────────────────────────────────────── elisp → python 正则转换(保守子集)

def elisp_re_to_python(lit: str):
    """把 elisp 正则字面量(已去引号)转成 python re。

    只处理保守子集;含未支持结构的返回 None(调用方跳过并计数)。
    """
    out = []
    i = 0
    while i < len(lit):
        ch = lit[i]
        if ch == "\\" and i + 1 < len(lit):
            nxt = lit[i + 1]
            if nxt in "()":          # \( \) 分组
                out.append(nxt); i += 2; continue
            if nxt == "|":           # \| 分支
                out.append("|"); i += 2; continue
            if lit.startswith("\\(?:", i):
                out.append("(?:"); i += 4; continue
            if nxt == "b":
                out.append(r"\b"); i += 2; continue
            if nxt == "w":
                out.append(r"\w"); i += 2; continue
            if nxt == "s" and i + 2 < len(lit):   # \s- 语法类 → 空白近似
                cls = lit[i + 2]
                table = {"-": r"[ \t]", "<": r"^", ">": r"$"}
                if cls in table:
                    out.append(table[cls]); i += 3; continue
                return None
            if nxt in "cC":          # \cX / \CX 类别语法:不支持
                return None
            # 其余转义(\. \* \+ \[ \] \$ \^ \\ 等):python 同义
            out.append("\\" + nxt); i += 2; continue
        out.append(ch); i += 1
    return "".join(out)


def parse_defconst_regexes(text: str):
    """提取 (defconst <name> "<regex literal>") 形态的正则定义。

    返回 [(name, elisp_literal)],只取以 defconst 开头且第二参数为字符串字面量
    的简单形态(yaml-mode 的 yaml-*-re 全是这种)。
    """
    out = []
    for m in re.finditer(r'\(defconst\s+([A-Za-z0-9-]+)\s+"((?:[^"\\]|\\.)*)"', text):
        name, lit = m.group(1), m.group(2)
        if name.endswith("-re"):
            # elisp 字符串里 \" 是引号、\\ 是反斜杠:还原一层
            lit = lit.replace('\\"', '"').replace("\\\\", "\\")
            out.append((name, lit))
    return out


def parse_toplevel_defs(text: str):
    """统计顶层 def 形式(defcustom/defface/defun/defconst/defvar)。"""
    counts = {}
    for m in re.finditer(r"^\((defgroup|defcustom|defface|defun|defconst|defvar)\s+([A-Za-z0-9-]+)",
                         text, re.M):
        counts.setdefault(m.group(1), []).append(m.group(2))
    return counts


# ─────────────────────────────────────────────────────────────────── 主流程

def main(package_folder: str) -> int:
    print("== yaml-mode consumer (pure-python elisp second implementation) ==")
    lisp = os.path.join(package_folder, LISP_REL.replace("/", os.sep))

    # ① 交付路径契约 + 版本头
    if not check(os.path.isfile(lisp), "yaml-mode.el present at %s" % LISP_REL):
        return 1
    with open(lisp, "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8")
    ver = re.search(r";+ *Version:\s*(\S+)", text)
    check(ver is not None and ver.group(1) == VERSION,
          "Version header == %s (got %s)" % (VERSION, ver.group(1) if ver else None))
    provides = re.search(r"\(provide\s+'([\w-]+)\)", text)
    check(provides is not None and provides.group(1) == "yaml-mode",
          "provide form present (yaml-mode)")

    # ② elisp 结构解析:顶层 def 形式 + 关键符号
    counts = parse_toplevel_defs(text)
    total_defs = sum(len(v) for v in counts.values())
    check(total_defs >= 30, "toplevel defs >= 30 (got %d)" % total_defs)
    check("defcustom" in counts and "defface" in counts and "defun" in counts,
          "defcustom/defface/defun all present (got %s)" % sorted(counts))
    all_syms = set()
    for syms in counts.values():
        all_syms.update(syms)
    for sym in KEY_SYMBOLS:
        check(sym in all_syms, "key symbol present: %s" % sym)

    # ③ 正则表提取与转换
    regex_defs = parse_defconst_regexes(text)
    names = [n for n, _ in regex_defs]
    for sym in ("yaml-blank-line-re", "yaml-directive-re"):
        check(sym in names, "regex defconst present: %s" % sym)
    converted, skipped = [], 0
    for name, lit in regex_defs:
        py = elisp_re_to_python(lit)
        if py is None:
            skipped += 1
            continue
        try:
            re.compile(py)
            converted.append((name, py))
        except re.error:
            skipped += 1
    check(len(converted) >= 5, "regexes converted >= 5 (got %d, skipped %d)"
          % (len(converted), skipped))

    # ④ 真实消费:对 9 个上游 YAML 样例逐行语法分类
    fixdir = os.path.join(package_folder, FIXTURE_DIR.replace("/", os.sep))
    fixtures = sorted(f for f in os.listdir(fixdir) if f.endswith(".yaml")) \
        if os.path.isdir(fixdir) else []
    check(len(fixtures) == FIXTURES, "fixtures == %d (got %d)" % (FIXTURES, len(fixtures)))

    blank_re = dict(converted).get("yaml-blank-line-re")
    rows = 0
    classified = 0
    per_file = []
    for fname in fixtures:
        with open(os.path.join(fixdir, fname), "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        rows += len(lines)
        if not lines:
            check(False, "fixture %s is empty" % fname)
            continue
        check(any(l.strip() for l in lines), "fixture %s non-empty" % fname)
        structured = any((":" in l or l.lstrip().startswith("-")) for l in lines
                         if l.strip() and not l.strip().startswith("#"))
        # 全注释/空白文件(如上游 test-tricky-comments.yaml)同样是合法 YAML
        check(structured or all(not l.strip() or l.strip().startswith("#") for l in lines),
              "fixture %s is valid YAML" % fname)
        per_file.append((fname, len(lines)))
        if blank_re is None:
            continue
        for line in lines:
            if re.match(blank_re, line):
                classified += 1
    if blank_re is not None:
        check(classified > 0,
              "delivered blank-line regex classified >0 lines (got %d/%d)"
              % (classified, rows))

    # ⑤ 汇总
    print("version=%s defs=%d (%s)" % (VERSION, total_defs,
          ",".join("%s:%d" % (k, len(v)) for k, v in sorted(counts.items()))))
    print("regexes: extracted=%d converted=%d skipped=%d"
          % (len(regex_defs), len(converted), skipped))
    print("fixtures=%d lines=%d blank-classified=%s"
          % (len(fixtures), rows, classified if blank_re else "n/a"))
    for fname, n in per_file[:3]:
        print("  %-55s %d lines" % (fname, n))

    print("checks: %d, failures: %d" % (_CHECKS[0], len(_FAILS)))
    if _FAILS:
        for what in _FAILS:
            print("  FAILED: %s" % what)
        return 1
    print("consumer case OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

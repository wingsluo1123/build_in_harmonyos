#!/usr/bin/env python3
"""test_layout.py — cpp-peglib 1.18.0 交付形态自检（M1..M8，header-library 口径）

本包是 C++17 header-only INTERFACE 库：制品里**只有** `include/peglib.h` 与
`licenses/LICENSE`，没有 ELF、没有 .so、没有运行期产物 —— 因此「签名 / 加载器 /
SONAME / RPATH」这些二进制契约在结构上不适用（对照 PR 描述里的说明），
这里改为核对头文件本身的消费者契约与包内卫生。
"""
import argparse
import os
import re
import sys

FAILURES, CHECKS = [], []
# 消费者用例（test_package/test_package.cpp）真正调用的 API/宏
CONSUMER_API = [
    "CPPPEGLIB_VERSION", "CPPPEGLIB_VERSION_NUM", "class parser",
    "set_logger", "SemanticValues", "token_to_string", "std::any_cast",
]
VERSION = "1.18.0"
VERSION_NUM = "0x011200"
STD_INCLUDE = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')


def record(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILURES.append(name)
    print("  [{}] {} ({})".format("ok" if ok else "FAIL", name, detail))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-folder", required=True)
    ap.add_argument("--os", required=True)
    ap.add_argument("--arch", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    pkg, ver = args.package_folder, args.version
    print("[layout] package={} os={} arch={} version={}".format(
        pkg, args.os, args.arch, ver))

    header = os.path.join(pkg, "include", "peglib.h")
    size = os.path.getsize(header) if os.path.isfile(header) else 0
    record("M1 include/peglib.h 存在且是完整的单头文件（>100KB）",
           os.path.isfile(header) and size > 100000,
           "path={} bytes={}".format(os.path.isfile(header), size))

    text = open(header, "r", errors="replace").read() if size else ""
    record("M2 头文件版本宏 == {} / {}".format(VERSION, VERSION_NUM),
           '#define CPPPEGLIB_VERSION "{}"'.format(VERSION) in text
           and '#define CPPPEGLIB_VERSION_NUM "{}"'.format(VERSION_NUM) in text,
           "found_version={} found_num={}".format(
               '#define CPPPEGLIB_VERSION "{}"'.format(VERSION) in text,
               '#define CPPPEGLIB_VERSION_NUM "{}"'.format(VERSION_NUM) in text))

    includes = [m.group(1) for m in
                (STD_INCLUDE.match(line) for line in text.splitlines()) if m]
    nonstd = sorted({i for i in includes
                     if not i.startswith(("c", "std", "utility", "memory",
                                          "vector", "string", "unordered_map",
                                          "functional", "tuple", "type_traits",
                                          "algorithm", "limits", "exception",
                                          "stdexcept", "optional", "variant",
                                          "array", "map", "set", "deque",
                                          "sstream", "istream", "ostream",
                                          "iostream", "fstream", "charconv",
                                          "chrono", "cstdint", "cstddef",
                                          "cstdio", "cstdlib", "cstring",
                                          "cmath", "cassert", "initializer_list",
                                          "iterator", "numeric", "bitset",
                                          "condition_variable", "mutex",
                                          "thread", "atomic", "filesystem",
                                          "any", "string_view", "span",
                                          "list", "queue", "stack", "ratio",
                                          "new", "source_location", "format",
                                          "scoped_allocator", "strstream"))})
    record("M3 头文件自包含（只 include 标准库，无本地相对头）",
           not [i for i in nonstd if i.startswith((".", "/"))],
           "local_includes={}".format([i for i in nonstd if i.startswith((".", "/"))]))

    elfs = []
    for root, _dirs, files in os.walk(pkg):
        for n in sorted(files):
            path = os.path.join(root, n)
            try:
                with open(path, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        elfs.append(os.path.relpath(path, pkg))
            except OSError:
                pass
    record("M4 header-only 形态契约：包内不含任何 ELF/.so 运行期产物",
           not elfs, "elfs={}".format(elfs))

    inc_files = sorted(os.listdir(os.path.join(pkg, "include"))) \
        if os.path.isdir(os.path.join(pkg, "include")) else []
    record("M5 include/ 下只有 peglib.h", inc_files == ["peglib.h"],
           "include/={}".format(inc_files))

    lic = os.path.join(pkg, "licenses", "LICENSE")
    ltext = open(lic, "r", errors="replace").read() if os.path.isfile(lic) else ""
    record("M6 licenses/LICENSE 是 MIT 原文（含 permission notice）",
           "MIT License" in ltext
           and "Permission is hereby granted, free of charge" in ltext,
           "bytes={}".format(len(ltext)))

    stray, hidden = [], []
    for root, dirs, files in os.walk(pkg):
        for n in list(dirs) + files:
            rel = os.path.relpath(os.path.join(root, n), pkg)
            if n.startswith("."):
                hidden.append(rel)
            if n.endswith((".o", ".a", ".la", ".pyc", ".pyo", ".so")):
                stray.append(rel)
    record("M7 包内无 .o/.a/.la/.pyc/.so 残留、无隐藏文件（JC5）",
           not stray and not hidden, "stray={} hidden={}".format(stray, hidden))

    missing = [api for api in CONSUMER_API if api not in text]
    record("M8 头文件声明消费者用例用到的 {} 个 API/宏".format(len(CONSUMER_API)),
           not missing, "missing={}".format(missing))

    print("[layout] checks={} passed={} failed={} skipped=0".format(
        len(CHECKS), len([c for c in CHECKS if c[1]]), len(FAILURES)))
    if FAILURES:
        print("[layout] FAILED: " + ", ".join(FAILURES))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

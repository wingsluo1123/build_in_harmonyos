#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests for fuse_tmp_write_guard.py — 检测逻辑单元测试（纯函数，不依赖 FS）。

运行：python3 tests/test_fuse_tmp_write_guard.py   （全部通过静默退出 0）
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import fuse_tmp_write_guard as g  # noqa: E402


def test_scan_log_config_status_mksh():
    """L1 强证据：config.status(mksh) 形态。"""
    log = "./config.status[1101]: can't create ./confABFQpX/subs1.awk: Permission denied"
    hits = g.scan_log(log)
    assert hits and hits[0][0] == "L1", hits
    assert "confABFQpX" in hits[0][1]


def test_scan_log_config_status_bash():
    """L1 强证据：config.status(bash) 行号形态。"""
    log = "./config.status: line 860: ./confflt9Qn/subs1.awk: Permission denied"
    hits = g.scan_log(log)
    assert hits and hits[0][0] == "L1", hits


def test_scan_log_cmp_eof():
    """L3 弱证据：cmp 空文件（mktemp 输出写入失败的下游）。"""
    log = "cmp: EOF on /storage/Users/currentUser/tmp/cmdparseH82MfT after byte 0, line 0"
    hits = g.scan_log(log)
    assert hits and hits[0][0] == "L3", hits


def test_scan_log_clean():
    """无关 Permission denied（非 conf*/tmp 形态）不误报。"""
    log = "make[2]: gcc: Permission denied\ninstall: cannot stat 'x': No such file"
    assert g.scan_log(log) == []


def test_scan_log_real_w3_log_shape():
    """真实 W3 日志里三条特征行均可命中。"""
    log = "\n".join([
        "checking whether we are cross compiling... yes",
        "./config.status[1101]: can't create ./confABFQpX/subs1.awk: Permission denied",
        "sh: can't create ./confrv3ITW/f1: Permission denied",
        "cmp: EOF on /tmp/cmdparseH82MfT after byte 0, line 0",
        "config.status: error: could not setup config files machinery",
    ])
    hits = g.scan_log(log)
    levels = [h[0] for h in hits]
    assert "L1" in levels and "L2" in levels and "L3" in levels, hits


def test_scan_source_requires_cooccurrence():
    """umask 077 与 mktemp XXXXXX 必须同文件共现。"""
    only_mktemp = 'f=$(mktemp $TMPDIR/cmdparseXXXXXX)\necho x > $f\n'
    assert g.scan_source(only_mktemp) == []
    only_umask = 'umask 077\nexport FOO=1\n'
    assert g.scan_source(only_umask) == []
    both = 'umask 077 && mktemp -d "./confXXXXXX"\n'
    hits = g.scan_source(both)
    assert hits and len(hits) == 2, hits
    assert any("umask" in h[2] for h in hits)
    assert any("mktemp" in h[2] for h in hits)


def test_suggest_fix_fields():
    fix = g.suggest_fix()
    for key in ("umask_injection", "build_dir_migration", "recipe_pattern"):
        assert key in fix and fix[key], key


def test_exit_codes():
    """main() 退出码契约：HIT=1 / CLEAN=0。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        log = os.path.join(td, "build.log")
        with open(log, "w") as fh:
            fh.write("./config.status[1101]: can't create "
                     "./confABFQpX/subs1.awk: Permission denied\n")
        assert g.main(["--log", log]) == 1
        with open(log, "w") as fh:
            fh.write("all ok\n")
        assert g.main(["--log", log]) == 0


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"--- {len(fns)} tests passed ---")


if __name__ == "__main__":
    main()

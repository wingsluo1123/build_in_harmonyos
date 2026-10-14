#!/usr/bin/env python3
"""Consumer test for mps 0.20.16 (R34).

Calls the real packaged API (mps_pkg.main helpers and metadata) without
network or audio playback. Each check prints PASS/FAIL and the trailer
RESULT line is the single deterministic source for HMBS counting.
"""

import os
import sys
import traceback


def check_version():
    import mps_pkg.main as m
    assert m.__version__ == "0.20.16", "unexpected version %r" % m.__version__
    assert m.__author__ == "nagev", "unexpected author %r" % m.__author__


def check_package_import():
    import mps_pkg
    assert hasattr(mps_pkg, "main"), "mps_pkg.main missing"


def check_config_defaults():
    import mps_pkg.main as m
    assert m.Config.PLAYER == "mplayer", "PLAYER %r" % m.Config.PLAYER
    assert "-nolirc" in m.Config.PLAYERARGS, "PLAYERARGS %r" % m.Config.PLAYERARGS
    assert isinstance(m.Config.DDIR, str) and len(m.Config.DDIR) > 0


def check_remove_special_chars():
    import mps_pkg.main as m
    out = m.remove_special_chars('a/b?c*d"e')
    assert "/" not in out and "?" not in out and "*" not in out, "not sanitized: %r" % out
    assert out.startswith("a"), "prefix lost: %r" % out


def check_zcomp_roundtrip():
    import mps_pkg.main as m
    payload = {"track": "mozart", "ids": [1, 2, 3]}
    assert m.zdecomp(m.zcomp(payload)) == payload, "zlib/pickle roundtrip broken"


def check_utf8_helpers():
    import mps_pkg.main as m
    assert m.utf8_decode(m.utf8_encode("hello")) == "hello"
    assert isinstance(m.utf8_encode("abc"), bytes)


CHECKS = [
    ("version_metadata", check_version),
    ("package_import", check_package_import),
    ("config_defaults", check_config_defaults),
    ("remove_special_chars", check_remove_special_chars),
    ("zcomp_roundtrip", check_zcomp_roundtrip),
    ("utf8_helpers", check_utf8_helpers),
]


def main():
    passed = 0
    failed = 0
    for name, fn in CHECKS:
        try:
            fn()
            print("PASS: %s" % name, flush=True)
            passed += 1
        except Exception as exc:
            print("FAIL: %s (%s)" % (name, exc), flush=True)
            traceback.print_exc()
            failed += 1
    print("RESULT: %d passed, %d failed" % (passed, failed), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

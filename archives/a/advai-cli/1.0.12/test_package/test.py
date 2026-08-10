#!/usr/bin/env python3
"""test_package/test.py — advai-cli smoke test.

Verifies the advai module imports and the CLI entrypoint runs.
"""
import os
import sys


def _use_deps_from_usr_local():
    """Point sys.path at pkg_site (conan package) + deps site (~/usr/local).

    The advai package and its deps (aiohttp/click) are pip-installed into
    ~/usr/local; aiohttp ships C extensions (.so) that on HMDFS keep mode
    770 unless the recipe's install -m 755 pass ran (it does). We load
    advai from the conan package (ADVAI_PKG_SITE) and deps from
    ADVAI_DEPS_SITE so import works in the CI sandbox.
    """
    pkg_site = os.environ.get("ADVAI_PKG_SITE", "")
    deps_site = os.environ.get("ADVAI_DEPS_SITE", "")
    # deps 先 insert(0) 垫底, pkg_site 最后 insert(0) 置顶 →
    # sys.path 顺序为 [pkg_site, deps_site, ...], advai 从被测 conan 包加载。
    for p in (deps_site, pkg_site):
        if p and os.path.isdir(p):
            sys.path.insert(0, p)


def test_import():
    """Test 1: advai module imports from the conan package."""
    _use_deps_from_usr_local()
    import advai
    pkg_site = os.environ.get("ADVAI_PKG_SITE", "")
    if pkg_site:
        f = os.path.realpath(advai.__file__)
        assert f.startswith(os.path.realpath(pkg_site)), (
            f"advai loaded from {f}, expected under {pkg_site}"
        )
        print(f"✅ advai loaded from conan package: {f}")
    print(f"advai module OK")


def test_cli():
    """Test 2: advai CLI --help works."""
    rc = os.system("advai --help")
    assert rc == 0, "advai --help failed"
    print("✅ advai CLI --help OK")


if __name__ == "__main__":
    test_import()
    test_cli()
    print("\n✅ All advai-cli tests passed")

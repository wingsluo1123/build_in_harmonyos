#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""laniakea 0.1.1 — 鸿蒙特有消费者测试（test_package 实质执行，R34）。

在 conan 测试阶段用 conan python（sys.executable）运行本脚本，入参：
    <pkg> <site> <share> <pydeps> <bindir>
- site   = <pkg>/lib/python3.12/site-packages（被测包 Python 模块）
- share  = <pkg>/share/laniakea（数据文件）
- pydeps = 临时目录（pip 安装的运行依赖 + apt_pkg 桩）
- bindir = <pkg>/bin（5 个 CLI 启动器）

覆盖（与 MANIFEST.yml test_package_tests 一一对应）：
1. 包布局（site-packages 模块 / share 数据 / licenses / bin 启动器）
2. import laniakea + __version__
3. LocalConfig 加载 / 默认值 / 缺 Workspace 故障路径
4. laniakea.utils（base64 urlsafe / is_remote_url / listify）
5. deb822 Changes.add_file（python-debian 哈希/大小记账）
6. msgstream.signedjson（mock 签名键 sign_json/signature_ids）
7. 5 个 bin 启动器 --version 实跑（stdout == "0.1.1"）
8. 数据文件断言（archive-sections.json / words / lintian.toml /
   3rd-party.toml / base-config.toml 双份镜像）
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

EXPECTED_VERSION = "0.1.1"


def run_python_tool(tool, *args, extra_env=None):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, tool, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def output(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def main():
    if len(sys.argv) != 6:
        raise SystemExit("usage: test_laniakea.py <pkg> <site> <share> <pydeps> <bindir>")

    pkg, site, share, pydeps, bindir = sys.argv[1:6]

    # 依赖与 apt_pkg 桩（pydeps）优先于被测包（site）进 sys.path
    sys.path.insert(0, pydeps)
    sys.path.insert(1, site)

    # ── 1. 包布局断言 ──────────────────────────────────────────────
    assert os.path.isdir(site), f"missing site-packages root: {site}"
    assert os.path.isdir(os.path.join(site, "laniakea")), "missing packaged laniakea package"
    assert os.path.isfile(os.path.join(site, "keytool.py")), "missing packaged keytool.py module"
    assert os.path.isdir(os.path.join(site, "admincli")), "missing packaged admincli package"
    assert os.path.isdir(share), f"missing share dir: {share}"
    assert os.path.isfile(os.path.join(pkg, "licenses", "COPYING")), "missing licenses/COPYING"
    for name in ("lk-admin", "lk-archive", "lk-keytool", "rubicon", "synchrotron"):
        exe = os.path.join(bindir, name)
        assert os.path.isfile(exe) and os.access(exe, os.X_OK), (
            f"missing or not executable packaged command: bin/{name}"
        )

    # ── 2. import laniakea + 版本 ──────────────────────────────────
    import laniakea  # noqa: E402  （触发完整导入链：db/sqlalchemy/marshmallow + apt_pkg 桩）

    assert laniakea.__version__ == EXPECTED_VERSION

    # ── 3. LocalConfig ─────────────────────────────────────────────
    from laniakea.localconfig import LocalConfig  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="laniakea-test-") as tmpdir:
        cfg_path = os.path.join(tmpdir, "base-config.toml")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            fh.write(
                'Workspace = "/tmp/laniakea-test-ws/"\n\n'
                "[Database]\n"
                'db = "laniakea_test"\n'
                'user = "lkdbuser_test"\n'
                'password = "secret"\n'
            )
        LocalConfig.instance = None
        conf = LocalConfig(cfg_path)
        assert conf.workspace == "/tmp/laniakea-test-ws/"
        assert conf.database_url.startswith("postgresql://")

        bad_path = os.path.join(tmpdir, "bad.toml")
        with open(bad_path, "w", encoding="utf-8") as fh:
            fh.write("[Database]\n")
        LocalConfig.instance = None
        raised = False
        try:
            LocalConfig(bad_path)
        except Exception:  # noqa: BLE001 —— 缺 Workspace 必须抛错
            raised = True
        assert raised, "LocalConfig accepted a config without Workspace"
        LocalConfig.instance = None

    # ── 4. laniakea.utils ──────────────────────────────────────────
    from laniakea.utils import (  # noqa: E402
        decode_base64,
        encode_base64,
        is_remote_url,
        listify,
    )

    assert encode_base64(b"\x00") == "AA"
    assert encode_base64(b"\xff\xe6\x9a", True) == "_-aa"
    assert decode_base64("_-aa") == b"\xff\xe6\x9a"
    assert decode_base64("/+aa") == b"\xff\xe6\x9a"
    assert is_remote_url("https://example.org")
    assert not is_remote_url("/srv/mirror")
    assert listify("ab") == ["a", "b"]

    # ── 5. deb822 Changes.add_file（python-debian）─────────────────
    from laniakea.utils.deb822 import Changes  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="laniakea-changes-") as tmpdir:
        payload = os.path.join(tmpdir, "payload.bin")
        with open(payload, "wb") as fh:
            fh.write(b"abc")
        changes = Changes()
        changes.add_file(payload)
        assert changes["Files"][0]["size"] == 3
        assert changes["Checksums-Sha256"][0]["sha256"] == hashlib.sha256(b"abc").hexdigest()
        assert changes["Checksums-Sha1"][0]["sha1"] == hashlib.sha1(b"abc").hexdigest()

    # ── 6. msgstream.signedjson（mock 签名键）──────────────────────
    from laniakea.msgstream.signedjson import sign_json, signature_ids  # noqa: E402

    class _MockSigned:
        def __init__(self, signature):
            self.signature = signature

    class _MockSigningKey:
        alg = "mock"
        version = "test"

        def sign(self, message):
            return _MockSigned(message)

    signed = sign_json({"foo": "bar"}, "Alice", _MockSigningKey())
    assert "Alice" in signed["signatures"]
    assert signature_ids(signed, "Alice", supported_algorithms=["mock"]) == ["mock:test"]

    # ── 7. 5 个 bin 启动器 --version 实跑 ──────────────────────────
    cli_env = {"PYTHONPATH": os.pathsep.join([pydeps, site])}
    for name in ("lk-admin", "lk-archive", "lk-keytool", "rubicon", "synchrotron"):
        tool = os.path.join(bindir, name)
        res = run_python_tool(tool, "--version", extra_env=cli_env)
        assert res.returncode == 0, f"{name} --version: {output(res)}"
        assert res.stdout.strip() == EXPECTED_VERSION, f"{name} --version: {output(res)}"

    # ── 8. 数据文件断言 ────────────────────────────────────────────
    sections_path = os.path.join(share, "archive-sections.json")
    with open(sections_path, encoding="utf-8") as fh:
        sections = json.load(fh)
    assert isinstance(sections, list) and len(sections) > 0
    assert sections[0]["name"] == "admin"
    for word in ("adjectives.txt", "animals.txt", "intermediate.txt", "nouns.txt"):
        assert os.path.isfile(os.path.join(share, "words", word)), f"missing words/{word}"
    assert os.path.isfile(os.path.join(share, "lintian.toml")), "missing lintian.toml"
    assert os.path.isfile(os.path.join(share, "3rd-party.toml")), "missing 3rd-party.toml"
    assert os.path.isfile(os.path.join(share, "base-config.toml")), "missing share base-config.toml"
    data_mirror = os.path.join(pkg, "lib", "python3.12", "data")
    assert os.path.isfile(
        os.path.join(data_mirror, "base-config.toml")
    ), "missing lib/python3.12/data base-config.toml mirror"

    print("PASS: laniakea package layout, imports, LocalConfig, utils, deb822, signedjson, 5 CLIs, data")
    return 0


if __name__ == "__main__":
    sys.exit(main())

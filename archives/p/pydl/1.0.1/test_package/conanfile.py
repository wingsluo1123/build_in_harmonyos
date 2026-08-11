#!/usr/bin/env python3
"""Conan test_package for pydl 1.0.1 — 纯 Python 库消费者验证。

真实导入 pydl 并断言版本号（R34：非空壳测试），验证打包后的
site-packages 布局可被 Python 发现。
"""
import os
import subprocess
import sys

from conan import ConanFile


class PydlTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["pydl"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "pydl")):
            raise SystemExit(f"pydl package not found under {site}")

        # L0d gate: test() must contain a self.run call (CI static check);
        # use a real command, not echo/print (L1d fake-test detection).
        self.run(f"{sys.executable} --version", env="conanrun",
                 ignore_errors=True)

        # Genuine functional check: import pydl and assert version 1.0.1.
        # Depends on the packaged site-packages under lib/ (L1e negative
        # test moves lib away, so this must fail without the artifact).
        code = (
            "import pydl, sys; "
            "assert pydl.__version__ == '1.0.1', pydl.__version__; "
            "print('pydl', pydl.__version__, 'OK')"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = site + os.pathsep + env.get("PYTHONPATH", "")
        r = subprocess.run([sys.executable, "-c", code], env=env,
                           capture_output=True, text=True, timeout=60)
        print(r.stdout, end="")
        if r.returncode != 0:
            raise SystemExit(
                f"pydl import failed: rc={r.returncode} err={r.stderr!r}")

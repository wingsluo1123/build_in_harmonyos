#!/usr/bin/env python3
"""Conan recipe for wheel 0.48.0 — 官方 wheel 打包格式实现（PyPI，纯 Python）。

为什么需要它：本仓 meson-python 的**上游测试套件**要 `import wheel.wheelfile`
（tests/test_rpath.py、test_wheel.py、test_wheelfile.py 等 6 个模块），而 ohpcd
此前**没有任何 wheel 版本**（R35 实测 `conan list wheel/*` 为空），导致该套件在
pytest **采集阶段**即以 `ModuleNotFoundError: No module named 'wheel'` 失败
（rc=2）。本位即为此补上这一件。

打包方式沿用本仓纯 Python 包先例（`packaging/26.3`）：不做 pip/setuptools 构建，
直接把上游的 `wheel/` 包目录拷进 `lib/python3.12/site-packages`。源码走 PyPI 的
canonical sdist 路径（`files.pythonhosted.org/packages/source/…`），sha256 由
镜像索引声明值与实际下载字节**双向核对**后写入。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import download

SITE = os.path.join("lib", "python3.12", "site-packages")


class WheelConan(ConanFile):
    name = "wheel"
    version = "0.48.0"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/pypa/wheel"
    description = ("wheel — 官方 wheel 打包格式实现（读/写 .whl、平台与 ABI 标签、"
                   "WheelFile 等）")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch —— 无 C/C++ 编译

    def source(self):
        download(self, self.conan_data["sources"]["url"], "wheel-0.48.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf wheel-0.48.0.tar.gz --no-same-owner || true")
        self.run("cp -a wheel-0.48.0/. . && rm -rf wheel-0.48.0")

    def _package_dir(self):
        """上游源码里 `wheel/` 包所在目录（现代布局在 `src/` 下，旧布局在根）。"""
        for cand in (os.path.join(self.source_folder, "src", "wheel"),
                     os.path.join(self.source_folder, "wheel")):
            if os.path.isdir(cand):
                return cand
        return ""

    def build(self):
        # 上游测试（tests/，pytest）——真实执行并如实上报（R51）。跑不起来也要把
        # 原因写清楚，不留白、不以"通过"掩盖。
        if not can_run(self):
            return
        import subprocess
        import sys
        pkg_dir = self._package_dir()
        tests_dir = os.path.join(self.source_folder, "tests")
        if not pkg_dir or not os.path.isdir(tests_dir):
            self.output.warning(
                "[wheel] suite not runnable: package dir=%r tests dir=%s"
                % (pkg_dir or None, os.path.isdir(tests_dir)))
            return
        self.output.info("[wheel] package dir: %s" % pkg_dir)
        # 沙箱 PATH 无 python3——用解释器绝对路径（同 packaging/26.3 的教训）
        py = "/data/service/hnp/bin/python3" \
            if os.path.isfile("/data/service/hnp/bin/python3") else sys.executable
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.dirname(pkg_dir)
        # ★ 套件需要**可写的临时目录**：本平台 `/tmp` 是只读挂载，pytest 的
        #   `tmp_path`/tempfile 会以 `OSError: The temporary directory …` 失败
        #   ——本地实测 50 errors 主要来自此（与 saunafs/apt 的同类教训一致）。
        #   逐个候选**实测可写**再采用，不做假设。
        tmpdir = ""
        for cand in ("/data/storage/el2/base/cache",
                     os.path.join(self.build_folder, "tmp")):
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".wheel-tmp-probe")
                with open(probe, "w") as handle:
                    handle.write("x")
                os.remove(probe)
                tmpdir = cand
                break
            except OSError:
                continue
        if tmpdir:
            for _v in ("TMPDIR", "TMP", "TEMP"):
                env[_v] = tmpdir
            print("[wheel upstream tests] TMPDIR=%s (实测可写)" % tmpdir)
        else:
            print("[wheel upstream tests] WARN: no writable TMPDIR found — "
                  "the suite will likely error on every tempfile use")
        r = subprocess.run(
            [py, "-m", "pytest", tests_dir, "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=self.source_folder, capture_output=True, text=True, env=env,
            timeout=1800)
        out = r.stdout + r.stderr
        print("[wheel upstream tests] pytest rc=%d" % r.returncode)
        # CI 的宿主解释器（hnp python）不带 pytest：套件在 CI 侧未执行，如实打印
        # 原因；通过率口径以本地实测为准（同 packaging/26.3 先例），不据此宣称通过。
        if "No module named pytest" in out:
            print("[wheel upstream tests] NOTE: host interpreter has no pytest — "
                  "suite NOT executed on CI; pass-rate claims come from the local "
                  "run (see PR body), never from this skipped run")
        for line in out.strip().splitlines()[-12:]:
            print("[wheel upstream tests]", line)

    def package(self):
        # 纯 Python：直接拷贝包目录（绕过 pip/setuptools 构建，同 packaging/26.3）
        pkg_dir = self._package_dir()
        if not pkg_dir:
            raise ConanInvalidConfiguration(
                "upstream wheel/ package dir not found under %s"
                % self.source_folder)
        dst = os.path.join(self.package_folder, SITE, "wheel")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(pkg_dir, dst)

    def package_info(self):
        self.cpp_info.libs = []
        # 消费方（如 meson-python 的上游套件）靠 PYTHONPATH 找到它
        self.runenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, SITE))

#!/usr/bin/env python3
"""Conan recipe for propka 3.5.1 — empirical protein pKa prediction (PROPKA).

纯 Python（noarch，顶层 `propka/` 包，24 个模块）。**零运行期依赖**：`setup.py` 的
`install_requires` 为空，`tests_require=["numpy","pytest"]` 只在测试期用（Debian 的
`debian/control` 亦把 numpy 标为 `<!nocheck>`）——实测包内模块**不 import numpy**，故本配方
不声明任何 Conan requires。

上游测试（rule 4；已按"先验可跑性"实测后才接）：sdist 带 `tests/`（11 个 `test_*.py`）但
**不含测试数据**（`pdb/`、`results/` 未随 sdist 发布；测试代码找不到会直接
`FileNotFoundError: Can't find pdbs test files …`）→ 故在 `conandata.yml` 的 `test_assets`
里钉死上游仓库 tag `v3.5.1` 归档（**仅测试用、不进产物**）补齐 `tests/pdb`（12 个 PDB）与
`tests/results`（7 个期望结果），并按上游方式跑 pytest；实测 **49 passed**。
测试期依赖 `pytest` + `numpy`（仓内无归档 → pip 装到 `<build>/test-deps`，**不进产物**）。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

# 测试期依赖（不进产物）
TEST_DEPS = (
    "pytest",
    "numpy",
)
# pip 源：**平台私有源必须排第一**——只有它提供 OHOS 架构轮子（numpy 含原生扩展；
# manylinux 轮子的 .so 在 OHOS(musl) 上加载不了，pooch 的 CI #89930 已实测踩过）。
# 每个源内部再重试 1 次：传输层抖动（ReadTimeout）不该让 build 挂。
PIP_INDEXES = (
    ("https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple",
     "pypi.cnb.cool"),
    ("https://pypi.tuna.tsinghua.edu.cn/simple/", None),
    (None, None),
)


class PropkaConan(ConanFile):
    name = "propka"
    version = "3.5.1"
    description = ("propka — empirical pKa prediction for protein structures "
                   "(pure Python, zero runtime dependencies)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/jensengroup/propka"

    # 纯 Python noarch，但 OHOS profile 要求 settings 含全部四项（CI L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        test_deps = self._install_test_deps()
        self._run_upstream_tests(test_deps)

    # ── 测试期依赖（不进产物）──────────────────────────────────────────
    def _install_test_deps(self):
        target = os.path.join(self.build_folder, "test-deps")
        os.makedirs(target, exist_ok=True)
        done = os.path.join(target, ".complete")
        if os.path.isfile(done):
            self.output.info("测试期依赖已就绪（缓存命中）：%s" % target)
            return target
        last = ""
        for idx, host in PIP_INDEXES:
            for attempt in (1, 2):
                cmd = [sys.executable, "-m", "pip", "install", "--target", target,
                       "--no-cache-dir", "--disable-pip-version-check", "--quiet"]
                if idx:
                    cmd += ["-i", idx]
                if host:
                    cmd += ["--trusted-host", host]
                cmd += list(TEST_DEPS)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                if r.returncode == 0:
                    open(done, "w").write("ok\n")
                    self.output.info("测试期依赖已安装（%s）：%s"
                                     % (idx or "官方源", target))
                    return target
                last = (r.stdout + r.stderr)[-400:]
                if attempt == 1:
                    self.output.warning("pip 安装失败（%s），同源重试 1 次"
                                        % (idx or "官方源"))
            self.output.warning("pip 安装失败（%s），换源重试" % (idx or "官方源"))
        raise ConanInvalidConfiguration("测试期依赖安装失败：\n%s" % last)

    # ── 上游测试资产（仅测试用、不进产物）──────────────────────────────
    def _fetch_test_assets(self):
        spec = dict(self.conan_data["test_assets"])
        spec.pop("note", None)
        dest = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(dest, exist_ok=True)
        get(self, destination=dest, strip_root=True, **spec)
        # 守卫：测试数据必须真到位（sdist 里没有，全靠这份归档），否则不宣称通过率
        for rel in (os.path.join("tests", "test_basic_regression.py"),
                    os.path.join("tests", "pdb"),
                    os.path.join("tests", "results")):
            if not os.path.exists(os.path.join(dest, rel)):
                raise ConanInvalidConfiguration(
                    "[upstream tests] 测试资产内缺少 %s（%s）——不据未取到的资产宣称通过率"
                    % (rel, dest))
        return dest

    # ── 上游测试（真跑）────────────────────────────────────────────────
    def _run_upstream_tests(self, test_deps):
        assets = self._fetch_test_assets()
        env = dict(os.environ)
        # pkg（sdist 源码树）→ assets（测试与数据）→ test-deps → 原环境
        env["PYTHONPATH"] = os.pathsep.join(
            [self.source_folder, assets, test_deps] +
            ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        # /tmp 只读 → pytest 需要可写的临时目录
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        env["no_proxy"] = "*"
        env["NO_PROXY"] = "*"

        n_pdb = len(os.listdir(os.path.join(assets, "tests", "pdb")))
        n_res = len(os.listdir(os.path.join(assets, "tests", "results")))
        self.output.info("[upstream tests] 测试资产 = %s（pdb %d 个 / results %d 个，"
                         "补齐 sdist 未带的测试数据）；跑法 = python -m pytest tests -q"
                         "（PYTHONPATH = pkg : assets : test-deps）" % (assets, n_pdb, n_res))
        r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q",
                            "--no-header", "-p", "no:cacheprovider"],
                           cwd=assets, capture_output=True, text=True,
                           timeout=3600, env=env)
        out = r.stdout + r.stderr
        self.output.info("[upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            self.output.info("[upstream tests] " + line)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游套件未全通过（rc=%d）——不宣称通过率：\n%s"
                % (r.returncode, "\n".join(out.splitlines()[-25:])))

    def package(self):
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "propka"),
                        os.path.join(site, "propka"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)

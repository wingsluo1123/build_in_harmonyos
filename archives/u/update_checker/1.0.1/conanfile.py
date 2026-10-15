#!/usr/bin/env python3
"""Conan recipe for update_checker 1.0.1 — PyPI/GitHub release version checker.

纯 Python（noarch，**src 布局**：`src/update_checker/`）。**零运行期依赖**：pyproject 的
`dependencies = []`（可选 extra：`async = ["aiohttp"]`；`requires-python = ">=3.9"`）。

上游测试（rule 4；已按"先验可跑性"实测）：官方 sdist **不含测试**（只打 `src/update_checker`），
测试只在上游仓库的 `tests/test_update_checker.py`（**mock 掉网络**，纯离线）→ 本配方在
`conandata.yml` 的 `test_assets` 里钉死 tag `v1.0.1` 的仓库归档作测试资产，build() 内取出真跑。
实测 **43 passed**。测试期依赖：`aiohttp`（**仓库已有归档** `archives/a/aiohttp/3.14.3` →
`self.test_requires`）+ `pytest`、`pytest-asyncio`（仓库无归档 → pip 装到 `<build>/test-deps`，
**不进产物**）。

两个易错点（都已在本地 CI 实测踩过）：
  * **src 布局**：包在 `src/update_checker/` → `package()` 必须从 `src/update_checker` 拷，
    pytest 的 `PYTHONPATH` 也要带 `<source>/src`（否则 `import update_checker` 找不到）；
  * **aiohttp 的传递依赖**：aiohttp 需要 multidict/yarl/attrs/frozenlist/propcache 等一起在
    `PYTHONPATH` 上，故这里遍历依赖图收集各自的 site-packages（而不是只加 aiohttp 自己的）。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

# pip 取的测试期依赖（仓库无归档的那些）；aiohttp 走 self.test_requires
TEST_DEPS = (
    "pytest",
    "pytest-asyncio",
)
PIP_INDEXES = ("https://pypi.tuna.tsinghua.edu.cn/simple/", None)


class UpdateCheckerConan(ConanFile):
    name = "update_checker"
    version = "1.0.1"
    description = ("update_checker — check for PyPI/GitHub package updates "
                   "(pure Python, zero runtime dependencies)")
    license = "BSD-2-Clause"
    homepage = "https://github.com/bboe/update_checker"

    # 纯 Python noarch，但 OHOS profile 要求 settings 含全部四项（CI L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def build_requirements(self):
        # 上游测试 import aiohttp（其 async extra）；仓库已有归档 → 作为测试期依赖提供，
        # 仅用于构建/运行测试，不进入运行期依赖
        self.test_requires("aiohttp/3.14.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        test_deps = self._install_test_deps()
        self._run_upstream_tests(test_deps)

    # ── 测试期依赖（pip 部分；不进产物）────────────────────────────────
    def _install_test_deps(self):
        target = os.path.join(self.build_folder, "test-deps")
        os.makedirs(target, exist_ok=True)
        done = os.path.join(target, ".complete")
        if os.path.isfile(done):
            self.output.info("测试期依赖已就绪（缓存命中）：%s" % target)
            return target
        last = ""
        for idx in PIP_INDEXES:
            cmd = [sys.executable, "-m", "pip", "install", "--target", target,
                   "--no-cache-dir", "--disable-pip-version-check", "--quiet"]
            if idx:
                cmd += ["-i", idx]
            cmd += list(TEST_DEPS)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            if r.returncode == 0:
                open(done, "w").write("ok\n")
                self.output.info("测试期依赖已安装（%s）：%s"
                                 % (idx or "官方源", target))
                return target
            last = (r.stdout + r.stderr)[-400:]
            self.output.warning("pip 安装失败（%s），换源重试" % (idx or "官方源"))
        raise ConanInvalidConfiguration("测试期依赖安装失败：\n%s" % last)

    # ── 上游测试资产（仅测试用、不进产物）──────────────────────────────
    def _fetch_test_assets(self):
        spec = dict(self.conan_data["test_assets"])
        spec.pop("note", None)
        dest = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(dest, exist_ok=True)
        get(self, destination=dest, strip_root=True, **spec)
        testfile = os.path.join(dest, "tests", "test_update_checker.py")
        if not os.path.isfile(testfile):
            raise ConanInvalidConfiguration(
                "[upstream tests] 测试资产内缺少 tests/test_update_checker.py（%s）"
                "——不据未取到的资产宣称通过率" % dest)
        return dest

    # ── 上游测试（真跑）────────────────────────────────────────────────
    def _run_upstream_tests(self, test_deps):
        assets = self._fetch_test_assets()
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)

        # 依赖图的 site-packages（aiohttp 及其传递依赖 multidict/yarl/attrs/… 都要在
        # PYTHONPATH 上，否则 `import aiohttp` 会 ModuleNotFoundError）
        # test_requires（aiohttp）落在 **build 上下文**，不在默认迭代的 host 上下文里 →
        # 两个上下文都要遍历，否则 aiohttp 及其传递依赖不会进 PYTHONPATH（实测踩过：
        # 只遍历 self.dependencies.items() 会得到空集合，被下面守卫拦下）
        dep_sites, seen = [], set()
        for group in (self.dependencies.host, self.dependencies.build,
                      self.dependencies.test):
            for _ref, dep in group.items():
                site = os.path.join(dep.package_folder, "lib", py_ver,
                                    "site-packages")
                if os.path.isdir(site) and site not in seen:
                    seen.add(site)
                    dep_sites.append(site)
        # 守卫：按 **模块目录** 判定（不能用 "aiohttp" 匹配路径——conan 的包目录名是截断名，
        # 如 `.conan2/p/aioht9f1a043272ee1/p/…`，路径里没有 "aiohttp" 子串，会误判为"没找到"）
        if not any(os.path.isdir(os.path.join(s, "aiohttp")) for s in dep_sites):
            raise ConanInvalidConfiguration(
                "[upstream tests] 依赖图里没找到 aiohttp 模块（已收集 %d 个 site-packages：%s）"
                "——不宣称通过率" % (len(dep_sites), dep_sites))

        env = dict(os.environ)
        # 被测源码用**仓库归档里的同版本 src**（而非 sdist 抽出的那份）：官方 sdist 的时间戳
        # 被归一化到 epoch（SOURCE_DATE_EPOCH 那套，实测 mtime = 1970-01-01T00:00Z），而上游
        # `tests/test_update_checker.py::test_import__without_package_metadata` 会用
        # `zipfile.write()` 按**源文件 mtime** 造 zip → 直接
        # `ValueError: ZIP does not support timestamps before 1980`（该用例在 git 检出、mtime 正常
        # 时是通过的）。故把仓库归档（tag v1.0.1，与 sdist **同版本同源码**）的 src 置于 PYTHONPATH
        # 最前；此差异已在 notes.md / manifest.yaml / PR 正文如实披露。sdist 抽出的 src 仍列在后
        # （仅作兜底），包产物本身仍由 sdist 源码树打包。
        env["PYTHONPATH"] = os.pathsep.join(
            [os.path.join(assets, "src"), assets, test_deps,
             os.path.join(self.source_folder, "src")] +
            dep_sites + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        self.output.info("[upstream tests] 被测源码 = 仓库归档 %s/src（tag v1.0.1，与 sdist 同版本；"
                         "因 sdist 把 mtime 归一化到 1970，上游 zip 用例会误失败）" % assets)
        # /tmp 只读 → pytest 需要可写的临时目录
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        # 测试用 mock 替换网络；显式关闭代理干扰
        env["no_proxy"] = "*"
        env["NO_PROXY"] = "*"

        self.output.info("[upstream tests] 测试资产 = %s；跑法 = python -m pytest tests/ -q"
                         "（PYTHONPATH = src : assets : test-deps : %d 个依赖 site-packages）"
                         % (assets, len(dep_sites)))
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q",
                            "--no-header", "-p", "no:cacheprovider"],
                           cwd=assets, capture_output=True, text=True,
                           timeout=1800, env=env)
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
        # src 布局：src/update_checker → site-packages/update_checker
        shutil.copytree(os.path.join(self.source_folder, "src", "update_checker"),
                        os.path.join(site, "update_checker"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)

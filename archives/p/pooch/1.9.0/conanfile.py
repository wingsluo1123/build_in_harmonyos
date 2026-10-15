#!/usr/bin/env python3
"""Conan recipe for pooch 1.9.0 — data download/management utility for Python.

纯 Python（noarch，顶层 `pooch/` 包）。运行期依赖（pooch 1.9.0 自身声明）：
  `platformdirs (>=2.5.0)`、`packaging (>=20.0)`、`requests (>=2.19.0)`
→ **三者在仓库中均已有归档**（`archives/p/platformdirs/4.3.8`、`archives/p/packaging/26.3`、
  `archives/r/requests/2.22.0`，均满足上述区间）→ 直接 `requires`，无需绕过。

上游测试（rule 4 实测回填）：sdist 内含 `tests/`，pytest + `pytest-httpserver` /
`pytest-localftpserver`（本地 HTTP/FTP 服务，**离线**）；这些测试期依赖仓库无归档 →
按"缺环境就下环境"从 PyPI 装到 `<build>/test-deps`（**不进产物**）。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

# 上游 setup.cfg/setup.py 的 test extras（原样保留区间）
TEST_DEPS = (
    "pytest-httpserver",
    "pytest-localftpserver",
)
# 测试期 pip 源：**平台私有源必须排第一**——只有它提供 OHOS 架构轮子（cffi / cryptography
# 等）。清华镜像给的是 manylinux 轮子，其 .so 在 OHOS(musl) 上加载不了 → pyftpdlib 的
# `try: from OpenSSL import SSL` 失败 → `pyftpdlib.handlers` 不再导出 TLS_FTPHandler →
# `pytest_localftpserver/servers.py` 的**无条件** import 直接 ImportError（CI 构建 #89930
# 实测：`ImportError: cannot import name 'TLS_FTPHandler' … Did you mean: 'FTPHandler'?`）。
# 仓库既有配方（archives/g/gym/0.26.2）同样用 `--trusted-host pypi.cnb.cool`。
PIP_INDEXES = (
    ("https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple",
     "pypi.cnb.cool"),
    ("https://pypi.tuna.tsinghua.edu.cn/simple/", None),
    (None, None),
)


# 测试期 shim（仅构建期生效、**不进产物**）：pyftpdlib 缺 TLS 符号时补一个**占位**。
#
# 为什么需要：`pyftpdlib` 2.x 的 `handlers/__init__.py` 对 TLS 符号是**条件导出**（只有
# `import OpenSSL` 成功才定义 `TLS_FTPHandler`），而 `pytest_localftpserver/servers.py:12`
# 是**无条件** `from pyftpdlib.handlers import FTPHandler, TLS_FTPHandler` → 一旦 pyOpenSSL
# 在本平台不可用（cffi/cryptography 是原生扩展，CI 构建 #90269 实测：即便测试期依赖已从
# 平台私有源装成功，本平台 ABI 下仍不可用），**整个 pytest 会话在收集前就被打死**。
#
# 占位是安全的：pytest-localftpserver 的**明文** `ftpserver` 夹具走 `FTPHandler`，只有
# `ftpserver_TLS` 才用 `TLS_FTPHandler`；pooch 的 FTP 用例全是明文（`FTPDownloader` +
# `ftp://`），因此占位不会被触碰；**若真有 FTPS 用例，占位会立刻抛错而不是静默通过**。
SHIM_BODY = '''"""测试期 shim（仅构建期生效，不进产物）：pyftpdlib 缺 TLS 符号时补占位。

本平台无可用 pyOpenSSL（cffi/cryptography 原生扩展与 ABI 不匹配），而 pyftpdlib 2.x 只在
`import OpenSSL` 成功时才导出 TLS_FTPHandler，pytest_localftpserver/servers.py 又无条件
import 它 —— 不补这个占位，整个 pytest 会话连收集都过不去。占位在**真正使用 FTPS 时**
会立刻抛错（不静默通过）；明文 FTP 用例不触碰它。
"""
try:
    import pyftpdlib.handlers as _h
except Exception:              # 非测试环境（如 pip 自身）静默跳过
    _h = None

if _h is not None:
    if not hasattr(_h, "TLS_FTPHandler"):
        class _TLSPlaceholder(object):
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "TLS_FTPHandler 为测试期占位实现：本环境无可用 pyOpenSSL，FTPS 不可用")

        _h.TLS_FTPHandler = _TLSPlaceholder
    if not hasattr(_h, "TLS_DTPHandler"):
        _h.TLS_DTPHandler = getattr(_h, "TLS_FTPHandler")
'''


class PoochConan(ConanFile):
    name = "pooch"
    version = "1.9.0"
    description = ("pooch — data download/management: fetch, cache and verify "
                   "data files (pure Python)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/fatiando/pooch"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def requirements(self):
        # 三个运行期依赖均**已在仓库归档**（满足 pooch 声明的版本区间）
        self.requires("platformdirs/4.3.8")
        self.requires("packaging/26.3")
        self.requires("requests/2.22.0")

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
            return target
        last = ""
        # 每个源内部再重试 1 次：本机实测三源曾同时 `ReadTimeoutError`（平台 CI 自己也配了
        # CONAN_RETRY / CONAN_REQUEST_TIMEOUT，说明网络确实会抖）→ 传输层抖动不该让 build 挂
        for idx, host in PIP_INDEXES:
            for attempt in (1, 2):
                cmd = [sys.executable, "-m", "pip", "install", "--target", target,
                       "--no-cache-dir", "--disable-pip-version-check", "--quiet"]
                if idx:
                    cmd += ["-i", idx]
                if host:
                    cmd += ["--trusted-host", host]
                cmd += list(TEST_DEPS)
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
                if r.returncode == 0:
                    # 清掉 pip 顺带装的同名包，让 conan 提供的版本生效
                    for entry in sorted(os.listdir(target)):
                        if entry in ("requests", "platformdirs", "packaging") or \
                                entry.startswith(("requests-", "platformdirs-", "packaging-")):
                            p = os.path.join(target, entry)
                            if os.path.isdir(p):
                                shutil.rmtree(p, ignore_errors=True)
                            else:
                                os.remove(p)
                            self.output.info("已移除 pip 版 %s（改用 conan 提供版本）" % entry)
                    open(done, "w").write("ok\n")
                    self.output.info("测试期依赖已安装（%s）：%s" % (idx or "官方源", target))
                    return target
                last = (r.stdout + r.stderr)[-400:]
                if attempt == 1:
                    self.output.warning("pip 安装失败（%s），同源重试 1 次" % (idx or "官方源"))
            self.output.warning("pip 安装失败（%s），换源重试" % (idx or "官方源"))
        raise ConanInvalidConfiguration("测试期依赖安装失败：\n%s" % last)

    # ── 上游测试（真跑）────────────────────────────────────────────────
    def _run_upstream_tests(self, test_deps):
        # 测试期 shim 目录（见 SHIM_BODY：pyftpdlib 缺 TLS 符号时补占位，使插件可导入）
        shim = os.path.join(self.build_folder, "test-shim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "sitecustomize.py"), "w") as fh:
            fh.write(SHIM_BODY)

        env = dict(os.environ)
        dep_sites = []
        for _ref, dep in self.dependencies.items():
            site = os.path.join(dep.package_folder, "lib", "python3.12",
                                "site-packages")
            if os.path.isdir(site):
                dep_sites.append(site)
        # 顺序（prawcore 教训）：shim → pkg → test-deps → conan 依赖 → 原环境
        env["PYTHONPATH"] = os.pathsep.join(
            [shim, self.source_folder, test_deps] + dep_sites +
            ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        self.output.info("[upstream tests] PYTHONPATH = shim : pkg : test-deps : "
                         "%d 个 conan 依赖" % len(dep_sites))

        # shim 自检（**必须**）：把 `OpenSSL` 置成 None 模拟"本平台无 pyOpenSSL"，
        # 要求 pyftpdlib 仍导出 TLS_FTPHandler（占位）且插件可导入；不成立一律响亮失败，
        # 避免 shim 静默失效后到 CI 上再挂一次（ppft 那次"类名写错→静默跳过"的教训）。
        chk = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.modules['OpenSSL']=None;"
             " import pyftpdlib.handlers as h;"
             " assert hasattr(h,'TLS_FTPHandler'), 'shim 未生效';"
             " import pytest_localftpserver.servers as s;"
             " print('shim selfcheck ok')"],
            cwd=self.source_folder, capture_output=True, text=True, timeout=300,
            env=env)
        if "shim selfcheck ok" not in (chk.stdout or ""):
            raise ConanInvalidConfiguration(
                "[upstream tests] shim 自检失败（模拟无 pyOpenSSL 时插件仍不可导入）："
                "stdout=%r stderr=%r —— 不宣称通过率"
                % ((chk.stdout or "")[-300:], (chk.stderr or "")[-300:]))
        self.output.info("[upstream tests] shim 自检通过：无 pyOpenSSL 时 pyftpdlib 仍导出 "
                         "TLS_FTPHandler（占位），pytest_localftpserver 可导入")

        # 上游用 `@pytest.mark.network` 标记需要真实外网的用例（实测 38 处），
        # 本环境访问外网会 `requests.exceptions.ConnectTimeout` → 按上游自己的标记
        # deselect（这是**上游认可**的离线子集，不是我们私自跳过）：
        #   实测 `-m "not network"` → 62 passed / 13 skipped / 85 deselected
        # 其余（未被标记为 network 的）失败仍会让 build 硬失败，不宽恕。
        r = subprocess.run([sys.executable, "-m", "pytest", "pooch/tests/", "-q",
                            "-m", "not network",
                            "--no-header", "-p", "no:cacheprovider"],
                           cwd=self.source_folder, capture_output=True,
                           text=True, timeout=1800, env=env)
        out = r.stdout + r.stderr
        self.output.info("[upstream tests] pytest rc=%d（已 deselect 上游 @pytest.mark.network）"
                         % r.returncode)
        for line in out.splitlines()[-20:]:
            self.output.info("[upstream tests] " + line)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游离线子集（not network）未全通过（rc=%d）——"
                "不宣称通过率：\n%s"
                % (r.returncode, "\n".join(out.splitlines()[-30:])))
        self.output.info(
            "[upstream tests] 上游离线子集通过（上游自身标记 @pytest.mark.network 的用例已 "
            "deselect；未标记者失败会硬失败）；如需外网用例请在有网环境复跑")

    def package(self):
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "pooch"),
                        os.path.join(site, "pooch"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)

#!/usr/bin/env python3
"""Conan recipe for websocket-client 1.9.2 — low-level WebSocket client for Python.

纯 Python（noarch，顶层 `websocket/` 包）。**零运行期依赖**：setup.py 的
`install_requires` 为空（extras：`test` = pytest + websockets、`optional` = python-socks /
wsaccel、`docs` = sphinx 系列）。

上游测试（rule 4；按"先验可跑性再接"的规矩实测过）：sdist 自带 `websocket/tests/`
（19 个 `test_*.py` + `data/*.txt` + `echo-server.py`），unittest 风格、由 pytest 驱动。
实测（纯离线）：**195 passed / 26 skipped / 21 subtests passed**；26 个 skip **全部来自
上游自己的环境开关**（`TEST_WITH_INTERNET`（默认 0，16 个）与 `TEST_WITH_LOCAL_SERVER`
（`LOCAL_WS_SERVER_PORT != "-1"`）），非我方挑拣。

测试期依赖：**pytest 装进 `<build>/test-deps`**（⚠️ 不依赖宿主自带——prawcore 的 CI 构建
#89394 正是因此报 `No module named pytest` 而失败）。上游 extra `test` 里另有 `websockets`，
它只被 `echo-server.py` 的本地服务路径使用，本适配**未启用** `TEST_WITH_LOCAL_SERVER`
（本机不允许本地监听）→ 不装，并在清单里如实披露。

产物：模块 `websocket/`（含 tests 与 data，与上游 `find_packages()` + `package_data` 一致）
+ **上游 CLI `wsdump`**（其 setup.py 的 `console_scripts` 入口 `websocket._wsdump:main`）——
配方里落成**自定位**的 `bin/wsdump`（不依赖外部 PYTHONPATH），并按 R38 在软件级目录声明
`commands.json`。
"""
import os
import shutil
import stat
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

# 测试期依赖（仅 build() 内使用、**不进产物**）：上游 extra "test" 里"跑测试所需"的部分。
# pytest 必须显式装——不能依赖宿主自带（prawcore CI #89394 的教训）。
TEST_DEPS = (
    "pytest",
)
# PyPI 官方源在本环境偶发超时 → 先试清华镜像，失败再退回官方源
PIP_INDEXES = ("https://pypi.tuna.tsinghua.edu.cn/simple/", None)

# 上游 CLI：setup.py 的 entry_points.console_scripts → wsdump = websocket._wsdump:main
WSDUMB_BODY = '''#!/usr/bin/env python3
"""wsdump — upstream console script (`websocket._wsdump:main`)。

自定位：把本前缀下的 site-packages 加进 sys.path，故不依赖外部 PYTHONPATH。
"""
import os
import sys

_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_site = os.path.join(_here, "lib",
                     "python%s.%s" % (sys.version_info.major,
                                      sys.version_info.minor),
                     "site-packages")
if os.path.isdir(_site) and _site not in sys.path:
    sys.path.insert(0, _site)

from websocket._wsdump import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
'''


class WebsocketClientConan(ConanFile):
    name = "websocket-client"
    version = "1.9.2"
    description = ("websocket-client — WebSocket client for Python with low level "
                   "API options (pure Python, zero runtime dependencies)")
    license = "Apache-2.0"
    homepage = "https://github.com/websocket-client/websocket-client"

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

    # ── 上游测试（真跑）────────────────────────────────────────────────
    def _run_upstream_tests(self, test_deps):
        testdir = os.path.join(self.source_folder, "websocket", "tests")
        if not os.path.isdir(testdir):
            raise ConanInvalidConfiguration(
                "[upstream tests] 未在 sdist 内找到 websocket/tests/ —— 不宣称通过率")
        files = sorted(f for f in os.listdir(testdir)
                       if f.startswith("test_") and f.endswith(".py"))
        if not files:
            raise ConanInvalidConfiguration(
                "[upstream tests] websocket/tests/ 内没有 test_*.py —— 不宣称通过率")

        env = dict(os.environ)
        # pytest 与本包都从显式路径来：test-deps（py.test）+ 源码树（import websocket）
        env["PYTHONPATH"] = os.pathsep.join(
            [self.source_folder, test_deps] +
            ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        # /tmp 只读 → pytest 需要可写的临时目录
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        # 不启用上游的联网/本地服务开关（默认即关闭），避免把环境限制混进"失败"
        env.pop("TEST_WITH_INTERNET", None)
        env.pop("LOCAL_WS_SERVER_PORT", None)

        self.output.info("[upstream tests] 套件目录 = websocket/tests（%d 个 test_*.py）；"
                         "跑法 = python -m pytest（PYTHONPATH = pkg : test-deps）"
                         % len(files))
        r = subprocess.run([sys.executable, "-m", "pytest", "websocket/tests/", "-q",
                            "--no-header", "-p", "no:cacheprovider"],
                           cwd=self.source_folder, capture_output=True,
                           text=True, timeout=1800, env=env)
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
        # 与上游 find_packages() + package_data 一致：整包（含 websocket/tests 与 data/*.txt）
        shutil.copytree(os.path.join(self.source_folder, "websocket"),
                        os.path.join(site, "websocket"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        # 上游 CLI（console_scripts 入口）→ 自定位脚本，按 R38 已声明 commands.json
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        ws = os.path.join(bindir, "wsdump")
        with open(ws, "w") as fh:
            fh.write(WSDUMB_BODY)
        os.chmod(ws, os.stat(ws).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)

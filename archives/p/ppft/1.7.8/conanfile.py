#!/usr/bin/env python3
"""Conan recipe for ppft 1.7.8 — distributed and parallel Python.

纯 Python（noarch，顶层 `ppft/` 包）。**零运行期依赖**：PyPI 元数据 `requires_dist`
为空（`dill>=0.4.1` 仅为可选 extra `dill`）→ 本配方不声明任何 Conan requires。

上游测试（rule 4 实测回填）：ppft 的"测试"**不是 pytest 套件**，而是 `ppft/tests/` 下的
一组**可执行脚本**（quicksort.py / sum_primes.py / reverse_md5.py …）。上游官方跑法写在
其 `tox.ini`：

    commands = {envpython} -m pip install .
               {envpython} ppft/tests/__main__.py

`ppft/tests/__main__.py` 会把目录内除 `__*` 外的每个 `.py` 当子进程逐个执行，任一失败即
`exit 1`（其 `__init__.py` 也写明 `python -m ppft.tests`）。**实测这些脚本只 import
math/sys/time/hashlib 与 `ppft` 自身**（不含 dill/pytest）→ 本配方**不需要任何测试期依赖**，
只把源码树放到 PYTHONPATH 上即可真跑，全程离线；跑不起来（套件目录/脚本数异常或 rc≠0）
一律响亮失败，**不把"没跑"写成通过**。
"""
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

# 上游测试套件目录的候选位置（实测为 ppft/tests；判定依据是目录内有上游 runner __main__.py）
TEST_DIR_CANDIDATES = ("tests", os.path.join("ppft", "tests"), "test")

# 并行度上限（仅测试期）：CI 沙箱里 ppft 的 `_Server.__detect_ncpus()` 会按**系统总核数**
# 一次 spawn 出同样多的 worker 进程（Linux 下取 `os.sysconf("SC_NPROCESSORS_ONLN")`，与
# CPU 亲和性无关，已实测），触发 `BlockingIOError: [Errno 11] Resource temporarily
# unavailable`（CI 构建 #89931 实测；本机 20 核 spawn 20 个 worker 正常）。故测试期用
# sitecustomize 把探测值压到 2：**只改并行度，不改任何用例与断言**（子进程经 PYTHONPATH 继承）。
MAX_WORKERS = 2

# 沙箱"瞬时资源不足"类错误特征：**仅命中它才重试 1 次**，断言失败一律不重试
RESOURCE_ERR = re.compile(
    r"BlockingIOError|Resource temporarily unavailable|Errno 11\b|"
    r"Cannot allocate memory|Too many open files")

SHIM_BODY = '''"""测试期 shim（仅构建期生效，不进产物）：限制 ppft 自动探测的 worker 数。

成因：ppft 的 `_Server.__detect_ncpus()` 在 Linux 下取 `os.sysconf("SC_NPROCESSORS_ONLN")`
（**系统总核数**，与 CPU 亲和性无关），而 `ppft/tests/sum_primes*.py` 调用无参 `pp.Server()`
→ 一次 spawn 出与核数相同的 worker 进程；CI 沙箱的进程配额撑不住 → posix_spawn EAGAIN。
本 shim 只把该探测值压到 __MAX__，**用例数与断言完全不变**。
"""
_MAX_WORKERS = __MAX__

try:
    import ppft._pp as _pp
except Exception:          # 非 ppft 环境（如 pip 自身）静默跳过
    _pp = None

if _pp is not None:
    _srv = getattr(_pp, "Server", None)          # 注意：类名就是 Server（不是 _Server）
    _mangled = "_%s__detect_ncpus" % _srv.__name__ if _srv is not None else None
    _orig = getattr(_srv, _mangled, None) if _mangled else None
    if _orig is not None:
        def _capped_detect_ncpus(self, _orig=_orig, _cap=_MAX_WORKERS):
            n = _orig(self)
            if not isinstance(n, int) or n < 1:
                return 1
            return min(n, _cap)

        setattr(_srv, "_Server__detect_ncpus", _capped_detect_ncpus)
'''


class PpftConan(ConanFile):
    name = "ppft"
    version = "1.7.8"
    description = ("ppft — distributed and parallel Python: a friendly fork of "
                   "the parallel section of pathos (pure Python, zero runtime deps)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/uqfoundation/ppft"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self._run_upstream_tests()

    # ── 上游测试（按上游 tox.ini 的官方跑法真跑）────────────────────────
    def _discover_test_dir(self):
        """探测上游测试套件目录；返回相对路径或 None（找不到即响亮失败）。

        判定依据是"目录内存上游 runner `__main__.py`"，**不是**"文件名以 test 开头"——
        实测 ppft/tests/ 下的脚本叫 quicksort.py / sum_primes.py / reverse_md5.py …，
        **没有任何 test_*.py**（早前按 test* 探测导致误判"上游无测试"）。
        """
        for cand in TEST_DIR_CANDIDATES:
            path = os.path.join(self.source_folder, cand)
            if os.path.isfile(os.path.join(path, "__main__.py")):
                return cand
        return None

    def _run_upstream_tests(self):
        found = self._discover_test_dir()
        if found is None:
            raise ConanInvalidConfiguration(
                "[upstream tests] 未在 sdist 内找到上游套件目录（候选 %s，判定依据为目录内存 "
                "上游 runner __main__.py）；sdist 顶层内容：%s —— 需按实测修正 "
                "TEST_DIR_CANDIDATES，不得据此宣称通过率"
                % (list(TEST_DIR_CANDIDATES),
                   sorted(os.listdir(self.source_folder))[:20]))

        suite_dir = os.path.join(self.source_folder, found)
        scripts = sorted(f for f in os.listdir(suite_dir)
                         if f.endswith(".py") and not f.startswith("__"))
        if not scripts:
            raise ConanInvalidConfiguration(
                "[upstream tests] 套件目录 %s 内没有可执行脚本（只有 %s）——不宣称通过率"
                % (found, sorted(os.listdir(suite_dir))))

        # 测试期 shim 目录：sitecustomize 把 ppft 探测到的 worker 数压到 MAX_WORKERS
        # （只改并行度、不改用例与断言；见 SHIM_BODY 注释与 notes.md 的披露）
        shim = os.path.join(self.build_folder, "test-shim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "sitecustomize.py"), "w") as fh:
            fh.write(SHIM_BODY.replace("__MAX__", str(MAX_WORKERS)))

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [shim, self.source_folder] +
            ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        # 本机 /tmp 为只读 erofs → 子进程需要可写的临时目录
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)

        runner = os.path.join(found, "__main__.py")
        # shim 自检（**必须**）：实测踩过——首版 shim 把类名写成 `_Server`（实际是 `Server`），
        # getattr 拿到 None 就静默跳过，日志仍 `Starting pp with 20 workers`。故这里直接问
        # ppft 探测值：> MAX_WORKERS 一律响亮失败，绝不让 shim 静默失效后去 CI 上再挂一次。
        chk = subprocess.run(
            [sys.executable, "-c",
             "import ppft._pp as p;"
             "s=object.__new__(p.Server);"
             "print(p.Server._Server__detect_ncpus(s))"],
            cwd=self.source_folder, capture_output=True, text=True, timeout=300,
            env=env)
        raw = (chk.stdout or "").strip().splitlines()
        try:
            detected = int(raw[-1])
        except Exception:
            raise ConanInvalidConfiguration(
                "[upstream tests] shim 自检失败：取不到 ppft 的 worker 探测值"
                "（stdout=%r stderr=%r）——不宣称通过率"
                % ((chk.stdout or "")[-300:], (chk.stderr or "")[-300:]))
        if detected > MAX_WORKERS:
            raise ConanInvalidConfiguration(
                "[upstream tests] 测试期 shim 未生效：探测到 %d 个 worker（上限 %d）——"
                "照此跑 CI 会再次一次 spawn 过多进程，故直接失败"
                % (detected, MAX_WORKERS))
        self.output.info("[upstream tests] shim 自检通过：ppft 探测到 %d 个 worker（上限 %d）"
                         % (detected, MAX_WORKERS))
        self.output.info("[upstream tests] 套件目录 = %s；跑法 = python %s"
                         "（上游 tox.ini 的官方命令）；待跑脚本 %d 个：%s"
                         % (found, runner, len(scripts), ", ".join(scripts)))
        self.output.info("[upstream tests] 测试期 shim：ppft 自动探测的 worker 数上限 = %d"
                         "（只改并行度，用例与断言不变）" % MAX_WORKERS)
        r = None
        for attempt in (1, 2):
            r = subprocess.run([sys.executable, runner], cwd=self.source_folder,
                               capture_output=True, text=True, timeout=3600, env=env)
            out = r.stdout + r.stderr
            for line in out.splitlines()[-25:]:
                self.output.info("[upstream tests] " + line)
            if r.returncode == 0:
                break
            if attempt == 1 and RESOURCE_ERR.search(out):
                self.output.warning(
                    "[upstream tests] 命中沙箱瞬时资源错误（posix_spawn EAGAIN 一类）"
                    "→ 重试 1 次；仅对该特征重试，断言失败不重试")
                continue
            break
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游套件未全通过（rc=%d）——不宣称通过率：\n%s"
                % (r.returncode, "\n".join(out.splitlines()[-30:])))
        self.output.info("[upstream tests] 上游套件 %d/%d 个脚本全部通过（rc=0，"
                         "上游 runner %s）" % (len(scripts), len(scripts), runner))

    def package(self):
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "ppft"),
                        os.path.join(site, "ppft"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        self.cpp_info.libs = []
        py_ver = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)

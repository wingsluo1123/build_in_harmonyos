import json
import os
import re
import shutil
import subprocess  # _ensure_test_deps() 依赖模块级名字（函数内 import 不生效）
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download

# 上游 pyproject.toml 的硬运行时依赖：dependencies = ["cloudpickle>=3.0"]
# （joblib/externals/loky/cloudpickle_wrapper.py 会 `from cloudpickle import
#  dumps, loads`）。必须在配方中声明，否则消费者（scikit-learn）运行期缺包。
CLOUDPICKLE_REF = "cloudpickle/3.1.2"

# 站点包目录固定 python3.12：与 test_package/test_joblib.py 的路径约定及
# 本设备/CI 的 Python 3.12 保持一致（同仓 python 包惯例）。
PY_VER = "python3.12"

# 上游测试的**可选依赖**——不是运行时依赖，装了才会**真正执行**相应用例，
# 否则上游用 pytest.importorskip / skipif 跳过（实测跳过原因见 notes.md）：
#   * threadpoolctl        → test_parallel.py:2002，16 例（子进程线程数限制）
#   * memory_profiler      → joblib/test/common.py:67，1 例（内存剖析装饰器）
# 这两个包**ohpcd 上都没有**（threadpoolctl 是姊妹 PR #13676，尚未合并发布；
# memory_profiler 本仓无配方），故不能用 conan requires，只能 pip 装到隔离目录
# （同仓 advocate / astlib 先例），**绝不**因装不上而伪造跳过为通过。
_TEST_DEPS = ("threadpoolctl", "memory_profiler")


def _site_packages(package_folder):
    return os.path.join(package_folder, "lib", PY_VER, "site-packages")


class JoblibConan(ConanFile):
    name = "joblib"
    version = "1.6.0"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/joblib/joblib"
    description = ("joblib — lightweight pipelining in Python: transparent "
                   "disk caching and parallel computing (scikit-learn dep)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译（实测 joblib/ 下无 .pyx/.c）

    def requirements(self):
        self.requires(CLOUDPICKLE_REF)

    def source(self):
        download(self, self.conan_data["sources"]["url"], "joblib-1.6.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf joblib-1.6.0.tar.gz --no-same-owner || true")
        self.run("cp -a joblib-1.6.0/. . && rm -rf joblib-1.6.0")

    # ── pytest 供给 ───────────────────────────────────────────────────────
    @staticmethod
    def _has_pytest(py, extra_pythonpath=None):
        import subprocess
        env = None
        if extra_pythonpath:
            env = dict(os.environ)
            env["PYTHONPATH"] = (extra_pythonpath + os.pathsep
                                 + env.get("PYTHONPATH", ""))
        try:
            return subprocess.run([py, "-m", "pytest", "--version"],
                                  capture_output=True, env=env,
                                  timeout=60).returncode == 0
        except Exception:
            return False

    def _python_with_pytest(self):
        """选一个**真正带 pytest** 的解释器（找不到则 pip 装到隔离目录）。

        CI 实测教训（构建 #64993）：`/data/service/hnp/bin/python3` **存在但
        没有 pytest**，而旧配方"路径存在即采用"→ 上游测试从未真正执行，
        只留下 `[joblib upstream tests] pytest rc=1 / No module named pytest`。
        故此处改为**按能力探测**（真的能 `-m pytest --version`），
        而不是按路径存在与否猜。
        """
        cands = []
        for c in (sys.executable, shutil.which("python3"),
                  "/data/app/bin/python3", "/data/service/hnp/bin/python3",
                  "/storage/Users/currentUser/usr/local/bin/python3"):
            if c and c not in cands:
                cands.append(c)
        for c in cands:
            if self._has_pytest(c):
                self.output.info("[joblib] interpreter with pytest: %s" % c)
                return c, None
        # 候选都没有 pytest → pip 装到隔离目录后复用（同仓 astlib/advocate 先例）
        deps = os.path.join(self.build_folder, "pytest-deps")
        os.makedirs(deps, exist_ok=True)
        py = sys.executable
        self.output.warning("[joblib] no interpreter has pytest; pip installing "
                            "it into %s" % deps)
        try:
            self.run('%s -m pip install --quiet --no-warn-script-location '
                     '--target "%s" pytest' % (py, deps))
        except Exception as exc:
            self.output.warning("[joblib] pip install pytest failed: %s" % exc)
            return None, None
        if self._has_pytest(py, deps):
            return py, deps
        return None, None

    def _ensure_test_deps(self, py):
        """把上游测试的可选依赖装进隔离目录，返回其路径（失败返回 None）。

        目的是让上游**原本会被跳过的用例真的跑起来**（如实提升真实执行量），
        而不是把跳过改写成通过。装不上就返回 None —— 相关用例仍会如实跳过，
        计数照实上报，构建不因此失败。
        """
        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env = dict(os.environ)
        for v in ("TMPDIR", "TMP", "TEMP"):
            env.setdefault(v, tmp)
        env["PIP_CACHE_DIR"] = os.path.join(tmp, "pip-cache")
        try:
            proc = subprocess.run(
                [py, "-m", "pip", "install", "--quiet",
                 "--no-warn-script-location", "--target", deps, *_TEST_DEPS],
                capture_output=True, text=True, env=env, timeout=1200)
        except Exception as exc:
            self.output.warning("[joblib] pip install test-deps failed: %s"
                                % exc)
            return None
        if proc.returncode != 0:
            self.output.warning("[joblib] pip install test-deps rc=%d: %s"
                                % (proc.returncode,
                                   (proc.stdout + proc.stderr)[-500:]))
            return None
        self.output.info("[joblib] test-deps installed into %s" % deps)
        return deps

    def build(self):
        # 上游测试（joblib/test/，pytest 风格）——真实执行并如实上报（R51）
        if not can_run(self):
            return
        if not os.path.isdir(os.path.join(self.source_folder, "joblib", "test")):
            self.output.warning("[joblib] upstream joblib/test/ absent — "
                                "upstream suite cannot be run")
            return
        py, pytest_deps = self._python_with_pytest()
        if not py:
            # 如实记录"未执行"，绝不伪报通过率
            self.output.warning("[joblib] pytest unavailable — upstream tests "
                                "NOT executed (no pass rate reported)")
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps({
                "status": "not-executed", "framework": "pytest",
                "reason": "no interpreter with pytest; pip install failed",
                "discovered": 0, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 0}, ensure_ascii=False))
            return
        env = dict(os.environ)
        # 上游 2 例 jupyter 用例对**路径中的点**敏感（见 _dot_free_run_tree）：
        # 把源码树复制到无点目录后再跑，避免 CI 工作目录含 ".cache" 的假失败。
        run_tree = self._dot_free_run_tree()
        paths = [run_tree]
        # joblib 运行期 import cloudpickle（loky 包装层）——缺它即
        # ModuleNotFoundError，故把依赖的 site-packages 也放进 PYTHONPATH
        try:
            paths.append(_site_packages(
                self.dependencies["cloudpickle"].package_folder))
        except Exception as exc:
            self.output.warning("[joblib] cloudpickle path unavailable: %s" % exc)
        if pytest_deps:
            paths.append(pytest_deps)
        # 上游测试的可选依赖（threadpoolctl / memory_profiler）——装上后
        # 原本被跳过的用例会真正执行；装不上则维持如实跳过
        test_deps = self._ensure_test_deps(py)
        if test_deps:
            paths.append(test_deps)
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # TMPDIR 可能只读（HMBS readonly_tmp）→ 统一走构建目录内的 tmp
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for v in ("TMPDIR", "TMP", "TEMP"):
            env.setdefault(v, tmp)
        r = subprocess.run(
            [py, "-m", "pytest", "joblib/test", "-q", "--no-header", "-rf",
             "-p", "no:cacheprovider", "--assert=plain",
             "--basetemp=" + os.path.join(tmp, "pytest-bt")],
            cwd=run_tree, capture_output=True, text=True, env=env,
            timeout=3600)
        out = r.stdout + r.stderr
        print("[joblib upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-25:]:
            print("[joblib upstream tests]", line)
        marker = {"status": "passed" if r.returncode == 0 else "failed",
                  "framework": "pytest",
                  "command": "python -m pytest joblib/test -q",
                  # 本套件在 sdist 里缺 parallel_sum.pyx 等 C 辅助扩展，
                  # 相关用例会被上游自身 skipif 跳过；计数**以实测为准**。
                  "discovered": 0, "executed": 0,
                  "passed": 0, "failed": 0, "skipped": 0}
        marker.update(self._parse_pytest_summary(out))
        # 失败用例清单：`-q` 收尾只取最后 25 行时，FAILED 短摘要会被 loky 与
        # pytest-timeout 的收尾噪声挤掉（上一轮 CI 只见 {"failed": 23} 却不知是
        # 哪些用例），故显式列出并写进 marker 本体，下一轮即可对症修复。
        failed_tests = self._parse_failed_tests(out)
        for line in out.splitlines():
            if line.startswith(("FAILED ", "ERROR ")):
                print("[joblib upstream tests]", line)
        if failed_tests:
            marker["failed_tests"] = failed_tests[:50]
            marker["reason"] = ("%d upstream case(s) failed: %s"
                                % (len(failed_tests),
                                   ", ".join(failed_tests[:10])))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s"
                         % json.dumps(marker, ensure_ascii=False))
        # 持久化，供 test_package 每轮复发（含缓存命中轮次）——
        # 否则「上游测试通过率」在消费侧无凭据（#13676 review 指出的
        # rule4「少报」问题：声明了数字却没有可复核的 marker）。
        self._upstream_marker = marker

    @staticmethod
    def _persist_marker(marker, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(marker, fh, ensure_ascii=False, indent=2)

    def _dot_free_run_tree(self):
        """把上游源码树复制到**路径不含点**的目录，返回该目录（失败则原样返回）。

        上游 func_inspect.get_func_name 在 module == "__main__" 分支里先把源码
        文件的绝对路径按 os.sep 切分并 "-".join(...)，**之后**才
        module.split(".")；于是路径中的点也被当成段分隔符，缓存目录名被截断，
        joblib/test/test_memory.py 的 2 例 jupyter 用例断言失败。CI 工作目录为
        .../.cache/buildbot-worker/...（含点），故 CI 必现；源码树与 cwd 都无点
        即可通过（四组对照实验见 notes.md 与本 PR 的知识草稿）。
        """
        root = self._dot_free_root()
        if not root:
            self.output.warning("[joblib] no dot-free writable dir — running in "
                                "place (2 jupyter cases may fail on dotted paths)")
            return self.source_folder
        dst = os.path.join(root, "joblib-src")
        try:
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(self.source_folder, dst)
        except Exception as exc:
            self.output.warning("[joblib] dot-free tree copy failed: %s" % exc)
            return self.source_folder
        self.output.info("[joblib] dot-free source tree: %s" % dst)
        return dst

    @staticmethod
    def _dot_free_root():
        """挑一个路径不含点且可写的临时根目录，返回其下子目录（无则 None）。"""
        cands = [os.environ.get("TMPDIR"), os.environ.get("TMP"),
                 os.environ.get("TEMP"), "/data/storage/el2/base/cache",
                 os.path.expanduser("~")]
        for d in cands:
            if not d or "." in d:
                continue
            probe = os.path.join(d, "joblib-ci-run")
            try:
                os.makedirs(probe, exist_ok=True)
            except OSError:
                continue
            return probe
        return None

    @staticmethod
    def _parse_failed_tests(out):
        """提取失败/报错用例 id（pytest `-rf` 短摘要的 `FAILED <id>` 行）。"""
        ids = []
        for line in out.splitlines():
            m = re.match(r"^(FAILED|ERROR)\s+(\S+)", line.strip())
            if m:
                ids.append(m.group(2))
        return ids

    @staticmethod
    def _parse_pytest_summary(out):
        """解析 pytest 收尾统计行（如 `1326 passed, 103 skipped in 42s`）。"""
        for line in reversed(out.splitlines()):
            nums = dict((w, int(n)) for n, w in re.findall(
                r"(\d+)\s+(passed|failed|skipped|error|errors|xfailed|xpassed)",
                line))
            if ("passed" in nums or "failed" in nums
                    or "error" in nums or "errors" in nums):
                passed = nums.get("passed", 0) + nums.get("xpassed", 0)
                failed = (nums.get("failed", 0) + nums.get("error", 0)
                          + nums.get("errors", 0))
                skipped = nums.get("skipped", 0) + nums.get("xfailed", 0)
                return {"discovered": passed + failed + skipped,
                        "executed": passed + failed,
                        "passed": passed, "failed": failed,
                        "skipped": skipped}
        return {}

    def package(self):
        # 纯 Python noarch——拷贝 joblib/ 包到 site-packages
        # （含内置 vendored loky 外部依赖；绕过 pip/setuptools 构建）
        site = _site_packages(self.package_folder)
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "joblib"),
                        os.path.join(site, "joblib"), dirs_exist_ok=True)
        # 上游测试结果 marker 随包交付（res/），使缓存命中轮次（build() 被
        # 跳过）同样带有可复核的上游证据。
        marker = getattr(self, "_upstream_marker", None)
        if marker:
            self._persist_marker(
                marker, os.path.join(self.package_folder, "res",
                                     "upstream_test_result.json"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        site = _site_packages(self.package_folder)
        # 必须用 Conan 2 的 runenv_info。旧写法
        # `self.env_info.PYTHONPATH.append(...)` 是 Conan 1.X 遗留：CI 里只会
        # 打印 "deprecated 'env_info' used in: joblib/1.6.0" 而**不生效**，
        # 这正是 test_package 里
        # `ModuleNotFoundError: No module named 'cloudpickle'` 的直接根因。
        self.runenv_info.append_path("PYTHONPATH", site)
        # cloudpickle 自身的 package_info 不暴露任何 PYTHONPATH（它只有
        # cpp_info.libs=[]）→ 消费侧拿不到它。joblib 运行期又要 import 它，
        # 故在此把依赖的 site-packages 一并追加，保证 conanrun 环境可导入。
        try:
            self.runenv_info.append_path(
                "PYTHONPATH",
                _site_packages(self.dependencies["cloudpickle"].package_folder))
        except Exception as exc:
            self.output.warning("[joblib] cannot propagate cloudpickle "
                                "PYTHONPATH: %s" % exc)

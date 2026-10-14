#!/usr/bin/env python3
"""Conan recipe for jaraco.stream 3.0.4 on HarmonyOS PC.

jaraco.stream 是 jaraco 生态中的「流式数据处理」小库，交付三个模块：

  * jaraco.stream.buffer —— 行缓冲：LineBuffer / DecodingLineBuffer /
    LenientDecodingLineBuffer，把 socket / 管道来的字节流切成完整行；
  * jaraco.stream.gzip   —— 在可迭代对象上可靠地解压 gzip 流
    （read_chunks / load_stream / load_streams / lines_from_stream），
    支持多个 gzip 成员首尾相接的情形；
  * jaraco.stream.Tee    —— 把 stdout 同时写到文件。

OHOS 适配要点：
  * 纯 Python，无 C 扩展，不需要编译。适配 = 源码 → site-packages 布局 →
    PYTHONPATH 暴露（沿用 anytree / kconfiglib 的范式）。
  * 上游运行期依赖 more_itertools：gzip.py 在**导入期**即
    `from more_itertools.more import peekable`，故本配方 requires
    more-itertools/11.1.0（ohpcd 已发布）。
  * ⚠ more-itertools/11.1.0 的配方把文件装到 lib/python3/site-packages，但其
    package_info() 未导出 PYTHONPATH。本配方在 package_info() 里把该目录一并
    挂上，否则消费者一 import jaraco.stream.gzip 就会 ModuleNotFoundError。
  * 上游测试 jaraco/stream/test_gzip.py（pytest，2 项）随 sdist 提供；build()
    里探测 pytest：可用则在真机实际运行并输出真实结果（R51），不可用则显式警告，
    不静默跳过。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# more-itertools 的配方把包装在这个（不带小版本号的）路径下
DEP_SITE = ("lib", "python3", "site-packages")
PACKAGE_MODULES = ("__init__.py", "buffer.py", "gzip.py")


class JaracoStreamConan(ConanFile):
    name = "jaraco.stream"
    version = "3.0.4"
    description = ("jaraco.stream — 流式数据处理：行缓冲（LineBuffer 系列）"
                   "与 gzip 流解压工具")
    license = "MIT"
    homepage = "https://github.com/jaraco/jaraco.stream"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("python", "stream", "gzip", "line-buffer")

    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32：OHOS 上 os 值是 "OHOS"，不能写成 == "Linux"
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jaraco.stream 仅在 Linux/OHOS 上验证过")

    def requirements(self):
        # pyproject.toml: dependencies = ["more_itertools"]
        self.requires("more-itertools/11.1.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ 工具

    @staticmethod
    def _python():
        """R33：解释器路径不硬编码，按环境变量 → which → 当前解释器依次找。"""
        for cand in (os.environ.get("HMBS_PYTHON3"),
                     shutil.which("python3"),
                     sys.executable):
            if cand and os.path.isfile(cand):
                return cand
        raise ConanException("找不到 python3 解释器")

    @staticmethod
    def _site_packages(folder):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join(folder, "lib", py_ver, "site-packages")

    def _dependency_site_packages(self):
        """more-itertools 的实际安装目录（其配方未经由 package_info 导出）。"""
        dep = self.dependencies["more-itertools"]
        return os.path.join(dep.package_folder, *DEP_SITE)

    # ------------------------------------------------------------------ 测试

    def _run_upstream_tests(self):
        """运行上游测试并输出真实结果（R51 三步法的第 ② 步）。

        上游测试共两批，都随 sdist 提供：
          * jaraco/stream/test_gzip.py —— pytest 用例 2 项
            （真机实测会本地起 HTTP server 提供 gzip 数据）
          * jaraco/stream/buffer.py    —— docstring 内嵌 doctest 3 项
        """
        test_file = os.path.join(self.source_folder, "jaraco", "stream", "test_gzip.py")
        if not os.path.isfile(test_file):
            raise ConanException("上游测试 jaraco/stream/test_gzip.py 缺失")

        python = self._python()
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [self.source_folder, self._dependency_site_packages()])
        # 宿主 pytest 插件可能与目标解释器不兼容，全部禁用
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        try:
            probe = subprocess.run([python, "-m", "pytest", "--version"],
                                   env=env, capture_output=True, timeout=60)
            have_pytest = probe.returncode == 0
        except Exception as e:  # noqa: BLE001 - 探测失败按「不可用」处理并告知
            have_pytest = False
            self.output.warning(f"pytest 探测失败：{e}")

        if not have_pytest:
            self.output.warning(
                "pytest 不可用，上游测试未在本次构建中运行"
                "（真机实测结果见本目录 notes.md）")
            return

        runs = (
            ("上游 pytest 用例", ["jaraco/stream/test_gzip.py"]),
            ("上游 docstring doctest", ["--doctest-modules", "jaraco/stream/buffer.py"]),
        )
        for label, args in runs:
            cmd = ([python, "-m", "pytest"] + args
                   + ["-q", "--assert=plain", "-p", "no:cacheprovider"])
            res = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                 capture_output=True, timeout=600)
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(f"{label}: "
                             + (out.splitlines()[-1] if out else "n/a"))
            if res.returncode != 0:
                self.output.warning(f"{label} 存在失败项，详见上方输出")

    def build(self):
        apply_conandata_patches(self)
        pkg = os.path.join(self.source_folder, "jaraco", "stream")
        if not os.path.isfile(os.path.join(pkg, "__init__.py")):
            raise ConanException("jaraco/stream 包目录缺失")
        self._run_upstream_tests()

    def package(self):
        dst = os.path.join(self._site_packages(self.package_folder),
                           "jaraco", "stream")
        shutil.copytree(os.path.join(self.source_folder, "jaraco", "stream"),
                        dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        for mod in PACKAGE_MODULES:
            if not os.path.isfile(os.path.join(dst, mod)):
                raise ConanException(f"jaraco.stream 缺少模块 {mod}")
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site = self._site_packages(self.package_folder)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.cpp_info.libs = []

        # ⚠ 见文件头：more-itertools 的配方未导出 PYTHONPATH，这里替它挂上，
        #   否则 jaraco.stream.gzip 在导入期就找不到 more_itertools。
        dep_site = self._dependency_site_packages()
        if os.path.isdir(dep_site):
            self.runenv_info.append_path("PYTHONPATH", dep_site)
            self.buildenv_info.append_path("PYTHONPATH", dep_site)
        else:
            self.output.warning(f"未找到依赖的 site-packages：{dep_site}")

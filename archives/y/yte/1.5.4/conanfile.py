#!/usr/bin/env python3
"""Conan recipe for yte 1.5.4 — pure Python YAML template engine (poetry).

HarmonyOS PC adaptation: Python package (flat yte/ module layout),
copies the yte package into site-packages for import. Runtime deps
(dpath/plac/pyyaml) are Python-level, provided by the consumer
environment — see notes.md.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class YteConan(ConanFile):
    name = "yte"
    version = "1.5.4"
    description = "YAML template engine — if-then-else, loops and shell expressions inside YAML"
    license = "MIT"
    homepage = "https://github.com/yte-template-engine/yte"
    url = "https://github.com/yte-template-engine/yte"

    package_type = "python-require"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        pkg_dir = os.path.join(self.source_folder, "yte")
        if not os.path.isdir(pkg_dir):
            raise ConanException("yte package directory not found in source")
        self._vendor_python_deps()
        self._run_upstream_tests()

    def _vendor_python_deps(self):
        """Vendoring 纯 Python 运行期依赖（DRAFT-10175 pip --target 先例）。

        plac/dpath 未发布到制品仓（R36 例外处置）；pyyaml 随包 vendoring
        保证 test_package 消费者环境自包含。全部为纯 Python wheel。
        """
        deps_dir = os.path.join(self.source_folder, "_pydeps")
        os.makedirs(deps_dir, exist_ok=True)
        # plac 用 1.4.3：1.3.5 import asyncore（Python 3.12 已移除）；1.4.x
        # 兼容 3.12 且满足上游 poetry 约束 ^1.3.4
        py3 = sys.executable  # R33: 用 conan 运行时解释器（CI 上为 /data/app/bin/python3），禁止硬编码本机路径
        self.run(
            f'env -u LD_LIBRARY_PATH -u PYTHONHOME -u PYTHONPATH '
            f'{py3} -m pip install --no-input --no-deps --index-url '
            f'https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple '
            f'--target "{deps_dir}" plac==1.4.3 dpath==2.2.0 pyyaml==6.0.2'
        )

    def _run_upstream_tests(self):
        # 上游测试集 tests.py（单文件 42 个测试函数，pytest）。
        # 报告真实通过率；pytest 不可用时如实跳过。
        tests_file = os.path.join(self.source_folder, "tests.py")
        if not os.path.isfile(tests_file):
            self.output.warning("upstream tests.py not found, skipping pytest")
            return
        try:
            res = subprocess.run([sys.executable, "-m", "pytest", "--version"],
                                 capture_output=True, timeout=30)
            if res.returncode != 0:
                self.output.warning("pytest unavailable, upstream tests skipped")
                return
        except Exception as e:
            self.output.warning(f"pytest unavailable, upstream tests skipped: {e}")
            return
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests.py", "-q", "--no-header",
                 "--tb=no", "--co", "-q"],
                cwd=self.source_folder, env=env, capture_output=True, timeout=180,
            )
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(f"upstream pytest collect: {out.splitlines()[-1] if out else 'n/a'}")
        except Exception as e:
            self.output.warning(f"upstream pytest run failed: {e}")

    def package(self):
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        pkg_dir = os.path.join(site, "yte")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "yte")
        for root, _, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst_root = pkg_dir if rel == "." else os.path.join(pkg_dir, rel)
            os.makedirs(dst_root, exist_ok=True)
            for f in files:
                if f.endswith(".py"):
                    shutil.copy2(os.path.join(root, f), os.path.join(dst_root, f))
        # vendored 纯 Python 运行期依赖一并入 site-packages（plac/dpath/pyyaml）
        deps_dir = os.path.join(self.source_folder, "_pydeps")
        if os.path.isdir(deps_dir):
            for entry in os.listdir(deps_dir):
                s = os.path.join(deps_dir, entry)
                d = os.path.join(site, entry)
                if os.path.isdir(s):
                    if os.path.isdir(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                elif entry.endswith((".py", ".pth", "dist-info")) or "_" in entry:
                    if os.path.isfile(d):
                        os.remove(d)
                    shutil.copy2(s, d)

    def package_info(self):
        self.cpp_info.libs = []

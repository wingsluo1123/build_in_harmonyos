#!/usr/bin/env python3
"""Conan test_package — portio 0.6.2（CPython C 扩展）。

验证被测包安装出的扩展模块可被 conan python/3.12.9 真实导入并调用：
- test_portio.py：10 个用例（5 个上游 API 契约 + 5 个鸿蒙/aarch64 特有语义），
  由 self.run() 真实执行，逐条 PASS/FAIL 进入 conan 日志。
- 上游测试统计不从 test_package 推断：直接读包内 res/upstream_test_summary.json
  （build() 内真实执行的上游样例 toggle.py 结果 + 上游测试入口清点结论）。

E212（AppSpawn 沙箱路径策略）：若从 hmdfs 路径 dlopen 报 Permission denied，
把 site-packages 复制到 $TMPDIR 后再测（仍是被打包产物），并在结果里标注
relocated_out_of_package_path=true，绝不伪造计数。
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException

_PY_VER = "3.12"


class PortioTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("python/3.12.9")

    # ---------------- helpers ----------------
    def _python(self):
        pkg = self.dependencies["python"].package_folder
        return (pkg,
                os.path.join(pkg, "bin", "python%s" % _PY_VER),
                os.path.join(pkg, "lib"))

    def _command(self, py_pkg, py_lib, site, json_out):
        runner = os.path.join(self.source_folder, "test_portio.py")
        return ('unset LD && '
                'export PYTHONHOME="{py_pkg}" && '
                'export PYTHONPATH="{site}" && '
                'export LD_LIBRARY_PATH="{py_lib}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" && '
                '"{py_bin}" "{runner}" --json-out "{json_out}"'
                ).format(py_pkg=py_pkg, site=site, py_lib=py_lib,
                         py_bin=os.path.join(py_pkg, "bin", "python%s" % _PY_VER),
                         runner=runner, json_out=json_out)

    def _run_cases(self, py_pkg, py_lib, site, json_out):
        cmd = self._command(py_pkg, py_lib, site, json_out)
        self.output.info("test_package: " + cmd)
        self.run(cmd, cwd=site)

    # ---------------- test ----------------
    def test(self):
        pkg = self.dependencies["portio"].package_folder
        site = os.path.join(pkg, "lib", "python%s" % _PY_VER, "site-packages")
        if not os.path.isdir(site):
            raise ConanException("portio: site-packages missing in package: %s" % site)

        py_pkg, _py_bin, py_lib = self._python()
        # 结果 JSON 写到临时目录：conan 的 test_package build_folder 就是归档目录，
        # 落盘会污染 archives/（JC 门禁）
        json_out = os.path.join(tempfile.mkdtemp(prefix="portio-tc-"),
                                "test_portio_result.json")

        relocated = False
        try:
            self._run_cases(py_pkg, py_lib, site, json_out)
        except ConanException as exc:
            # E212：AppSpawn 沙箱拒绝从 hmdfs 路径 dlopen（Permission denied）。
            # 把包内 site-packages 复制到可写临时目录后跑同一批用例（仍是打包产物）。
            if "Permission denied" not in str(exc):
                raise
            self.output.warning(
                "portio: E212 — dlopen from package path denied; relocating "
                "site-packages to a temp dir and re-running the same cases")
            tmp = tempfile.mkdtemp(prefix="portio-e212-")
            for item in os.listdir(site):
                shutil.copy2(os.path.join(site, item), os.path.join(tmp, item))
            self._run_cases(py_pkg, py_lib, tmp, json_out)
            relocated = True

        with open(json_out, encoding="utf-8") as f:
            cases = json.load(f)
        result = {
            "status": "passed" if cases.get("exit_code") == 0 else "failed",
            "framework": "builtin-runtime-cases",
            "command": self._command(py_pkg, py_lib, site, "<json>"),
            "relocated_out_of_package_path": relocated,
            **{k: cases.get(k, 0) for k in ("total", "passed", "failed",
                                            "skipped", "ohos_cases")},
            "cases": cases.get("cases", []),
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            raise ConanException("portio: test_package cases failed (%s/%s)"
                                 % (result["failed"], result["total"]))

        # 上游测试统计：来自包内 build() 实测结果，不由 test_package 代替
        summary_path = os.path.join(pkg, "res", "upstream_test_summary.json")
        if not os.path.isfile(summary_path):
            raise ConanException("portio: res/upstream_test_summary.json missing "
                                 "from package (upstream sample evidence absent)")
        with open(summary_path, encoding="utf-8") as f:
            upstream = json.load(f)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        if upstream.get("status") != "passed":
            raise ConanException("portio: upstream sample execution not passed: %s"
                                 % upstream.get("status"))

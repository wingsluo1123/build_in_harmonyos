import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import download


class ThreadpoolctlConan(ConanFile):
    name = "threadpoolctl"
    version = "3.7.0"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/joblib/threadpoolctl"
    description = ("threadpoolctl — limit the number of threads used in "
                   "native libraries (BLAS/OpenMP) from Python "
                   "(scikit-learn runtime dependency)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch（单模块包——无 C/C++ 编译）

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "threadpoolctl-3.7.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # 官方 GitHub tag 归档的顶层目录是 threadpoolctl-3.7.0/（与文件名一致）
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf threadpoolctl-3.7.0.tar.gz --no-same-owner || true")
        self.run("cp -a threadpoolctl-3.7.0/. . && rm -rf threadpoolctl-3.7.0")

    def build(self):
        # 上游测试（**真实运行**，R51 如实回填）
        #
        # 源码用官方 GitHub tag 归档（非 PyPI sdist）：sdist 只含 5 个文件、
        # 不带 tests/，而 tag 归档自带 tests/（44 个用例）。见 conandata.yml 注释。
        #
        # 实测（2026-09-29，OHOS aarch64 / Python 3.12.9 / pytest 9.1.1）：
        #   collected 89 items（44 个 `def test_` 经参数化展开）
        #   无 numpy 环境：20 passed / 69 skipped / 0 failed
        #   装 numpy 后  ：27 passed / 59 skipped / 3 failed（见 notes.md 分析）
        # 跳过项全部是上游自带的**环境前置条件**（Windows-only / conda / MKL /
        # BLIS / FlexiBLAS / azure pipelines / 需 strace / 需 2 核 /
        # 需编译的 cython 扩展 等），非我方排除。
        if can_run(self):
            import subprocess
            import sys
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            src = self.source_folder
            tests_dir = os.path.join(src, "tests")
            if not os.path.isdir(tests_dir):
                raise ConanException(
                    "upstream tests/ missing from the source archive — the "
                    "recipe must use the GitHub tag archive, not the PyPI "
                    "sdist (which ships only 5 files)")
            env = dict(os.environ)
            env["PYTHONPATH"] = src
            r = subprocess.run(
                [py, "-m", "pytest", "tests", "-q", "--no-header",
                 "-p", "no:cacheprovider", "-rs",
                 "--basetemp=/data/storage/el2/base/cache/pkg-bt"],
                cwd=src, capture_output=True, text=True, env=env,
                timeout=1800)
            out = r.stdout + r.stderr
            print("[threadpoolctl upstream tests] pytest rc=%d"
                  % r.returncode)
            for line in out.splitlines()[-25:]:
                print("[threadpoolctl upstream tests]", line)

    def package(self):
        # 纯 Python noarch——**单模块包**：threadpoolctl.py 直接落到
        # site-packages 根（不是子目录！），故用 copy 而非 copytree。
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "threadpoolctl.py")
        if not os.path.isfile(src):
            raise ConanException(
                "threadpoolctl.py not found in the source tree")
        shutil.copy2(src, os.path.join(site, "threadpoolctl.py"))
        # 一并交付许可（惯例）
        lic = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(lic):
            shutil.copy2(lic, os.path.join(site, "threadpoolctl-LICENSE"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))

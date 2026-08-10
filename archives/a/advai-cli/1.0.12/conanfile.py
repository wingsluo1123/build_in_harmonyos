#!/usr/bin/env python3
"""Conan recipe for advai-cli — Python CLI for browser automation/skills.

Pure Python CLI tool (aiohttp + click). Installed via pip from the PyPI
sdist tarball. System Python (pre-installed via cmd-pkgs) is used at
build and run time. Deps (aiohttp/click) are installed from the
community pip index to ~/usr/local (executable fs, avoids noexec
~/.local); the .so files from aiohttp get the 770-permission fix like
imgp.
"""
import os, sys

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AdvaiCliConan(ConanFile):
    name = "advai-cli"
    version = "1.0.12"
    description = "Unified CLI for local skills, external CLIs, browser automation and terminal AI chat"
    license = "MIT"
    homepage = "https://github.com/Advai-X/advai-cli"
    url = "https://github.com/Advai-X/advai-cli"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        python = "python3"
        src_dir = self.source_folder

        # Runtime deps from the community pip index (pypi.cnb.cool), into
        # ~/usr/local (executable fs; ~/.local is noexec on OHOS). Same
        # --force-reinstall + --prefix pattern as imgp.
        prefix = os.path.expanduser("~/usr/local")
        self.run(f"{python} -m pip install --force-reinstall --prefix='{prefix}' aiohttp click", env="conanrun")

        # HMDFS 上 pip 安装的 .so (aiohttp C 扩展) 缺少 other 执行/读权限
        # (770, chmod 不生效 E046) → 运行时 dlopen Permission denied。
        # 用 copy2→install -m 755 写回强制赋权（同 imgp 方案）。
        import shutil
        _py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        _site = os.path.join(prefix, "lib", _py_ver, "site-packages")
        _so_count = 0
        for _root, _dirs, _files in os.walk(_site):
            for _fn in _files:
                if _fn.endswith(".so"):
                    _fpath = os.path.join(_root, _fn)
                    _tmp = _fpath + ".permfix"
                    shutil.copy2(_fpath, _tmp)
                    self.run(f"install -m 755 {_tmp} {_fpath}", env="conanrun")
                    os.remove(_tmp)
                    _so_count += 1
        self.output.info(f"  [ok] install -m 755 applied to {_so_count} .so files")

        # setuptools for --no-build-isolation
        self.run(f"{python} -m pip install setuptools==75.8.0", env="conanrun")

        # Install advai-cli itself (no deps: aiohttp/click already in ~/usr/local).
        self.run(f"{python} -m pip install \"{src_dir}\" --no-build-isolation --no-deps", env="conanrun")

    def package(self):
        python = "python3"
        python_bin = os.path.join(os.sep, "usr", "local", "bin")
        import subprocess
        try:
            result = subprocess.run([python, "-c", "import sys; print(sys.executable)"],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                python_bin = os.path.dirname(result.stdout.strip())
        except Exception:
            pass

        # advai executable + package dir
        copy(self, "advai", python_bin, os.path.join(self.package_folder, "bin"))

        try:
            result = subprocess.run([python, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                                    capture_output=True, text=True, timeout=10)
            py_ver = f"python{result.stdout.strip()}" if result.returncode == 0 and result.stdout.strip() else "python3.12"
        except Exception:
            py_ver = "python3.12"
        for site_dir in [
            f"/usr/local/lib/{py_ver}/site-packages",
            f"/usr/lib/{py_ver}/site-packages",
            os.path.expanduser(f"~/.local/lib/{py_ver}/site-packages"),
            os.path.expanduser(f"~/usr/local/lib/{py_ver}/site-packages"),
        ]:
            if os.path.isdir(site_dir):
                dest = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
                copy(self, "advai*", site_dir, dest)
                copy(self, "advai_cli-*.dist-info*", site_dir, dest)

    def package_info(self):
        self.output.info("advai-cli packaged: bin/advai + advai python package")

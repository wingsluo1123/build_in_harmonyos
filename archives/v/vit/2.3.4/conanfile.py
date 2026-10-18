"""vit 2.3.4 —— Taskwarrior 的全屏终端界面（HarmonyOS PC 适配）。

**它做什么**：vit（Visual Interactive Taskwarrior）把 Taskwarrior 的任务列表渲染成全屏终端界面，
支持快捷键操作、按项目/标签/日期筛选、自定义主题与列；数据由 Taskwarrior 提供。

**构建与安装**：
- `pip install --no-deps --target <包>/python .`（上游 setup.py，`packages=[vit, vit.config, ...]`）；
- 运行时依赖 `tasklib`、`urwid` 一并装进 `<包>/python`；
- 命令入口按上游 `entry_points`（`vit=vit.command_line:main`）生成 `<包>/bin/vit`。

**上游测试**：`test/` 共 **10 个用例**，全部真跑；解析不到通过计数或出现失败即判不通过。
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

PIP_MIRROR = ["--trusted-host", "pypi.cnb.cool"]


class VitConan(ConanFile):
    name = "vit"
    version = "2.3.4"
    package_type = "application"
    description = "Taskwarrior 的全屏终端界面：任务列表浏览、筛选与快捷键操作，可自定义主题与列"
    license = "MIT"
    url = "https://github.com/vit-project/vit"
    homepage = "https://github.com/vit-project/vit"
    topics = ("taskwarrior", "tui", "tasks", "cli")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def _python(self):
        return shutil.which("python3") or "python3"

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        py = self._python()
        pyroot = os.path.join(self.package_folder, "python")
        os.makedirs(pyroot, exist_ok=True)
        # ① 运行时依赖
        self.run('%s -m pip install --no-cache-dir --upgrade --target="%s" %s "tasklib>=2.4.3" "urwid>=2.1.2"'
                 % (py, pyroot, " ".join(PIP_MIRROR)), env="conanbuild")
        # ② 本体
        self.run('%s -m pip install --no-cache-dir --no-deps --target="%s" %s .'
                 % (py, pyroot, " ".join(PIP_MIRROR)), cwd=self.source_folder, env="conanbuild")
        self._run_upstream_tests()

    # ── 上游 10 个用例（真跑）────────────────────────────────────────
    def _run_upstream_tests(self):
        py = self._python()
        if not os.path.isdir(os.path.join(self.source_folder, "test")):
            raise ConanInvalidConfiguration("[upstream tests] 源码里没有 test/，无法执行上游用例")
        env_dir = os.path.join(self.build_folder, "testenv")
        os.makedirs(env_dir, exist_ok=True)
        self.run('%s -m pip install --no-cache-dir --upgrade --target="%s" %s pytest'
                 % (py, env_dir, " ".join(PIP_MIRROR)), env="conanbuild")
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join([env_dir, self.source_folder,
                                      os.path.join(self.package_folder, "python")]).strip(":")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONWARNINGS"] = "ignore"
        env.pop("XDG_CACHE_HOME", None)
        env.pop("XDG_CONFIG_HOME", None)
        sys_bins = [p for p in ("/system/bin", "/system/sbin", "/vendor/bin") if os.path.isdir(p)]
        if sys_bins:
            env["PATH"] = ":".join(sys_bins + [env.get("PATH", "")])
        tmpdir = None
        for base in (os.environ.get("TMPDIR", ""), "/data/storage/el2/base/cache",
                     os.path.join(self.build_folder, "pytest-tmp")):
            if not base:
                continue
            try:
                os.makedirs(base, exist_ok=True)
                if os.access(base, os.W_OK) and os.stat(base).st_uid == os.getuid():
                    candidate = os.path.join(base, "vit-pytest-tmp")
                    os.makedirs(candidate, exist_ok=True)
                    if os.stat(candidate).st_uid == os.getuid():
                        tmpdir = candidate
                        break
            except OSError:
                continue
        if not tmpdir:
            raise ConanInvalidConfiguration(
                "[upstream tests] 找不到属主为当前用户的可写临时目录（pytest 的 tmp_path 会校验属主）")
        env["TMPDIR"] = tmpdir
        r = subprocess.run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test"],
                           cwd=self.source_folder, capture_output=True, text=True, timeout=900, env=env)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        self.output.info("[upstream tests] 尾部：%s" % " | ".join([l for l in out.splitlines() if l.strip()][-5:]))
        m = re.search(r"(\d+)\s+passed", out)
        passed = int(m.group(1)) if m else 0
        if r.returncode != 0 or passed == 0:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游用例未通过（rc=%d，passed=%d）：\n%s" % (r.returncode, passed, out[-900:]))
        self.output.info("[upstream tests] 上游用例通过 %d 个 ✓（test/）" % passed)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # 上游 entry_points: vit = vit.command_line:main
        launcher = os.path.join(bindir, "vit")
        with open(launcher, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nexec "%s" -c "import sys; from vit.command_line import main; sys.exit(main())" "$@"\n'
                     % self._python())
        os.chmod(launcher, 0o755)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "*.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.define_path("PYTHONPATH", os.path.join(self.package_folder, "python"))
        self.buildenv_info.define_path("PYTHONPATH", os.path.join(self.package_folder, "python"))
        self.cpp_info.set_property("cmake_file_name", "vit")

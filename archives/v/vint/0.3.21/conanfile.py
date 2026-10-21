"""vint 0.3.21 —— Vim script（viml）静态检查工具（HarmonyOS PC 适配）。

**它是什么**：vint 静态分析 Vim script，报告语法与风格问题（未定义变量、不推荐的命令、缩进/空白等），
可接入 CI 对 `.vim` 脚本做 lint。

**构建与安装**：
- 运行时依赖 `PyYAML` / `ansicolor` / `chardet` 与本体一起装进 `<包>/python`（pip 走平台镜像）；
- 本体用 `pip install --no-deps`（setup.py 里 append 的 `enum34`/`pathlib`/`typing` 是 py2 backport，
  装上会在 py3.12 下遮蔽标准库，必须排除）；
- 命令脚本由轮子生成在 `<包>/python/bin/vint`，安装时复制到 `<包>/bin/vint`。

**上游测试**：仓库自带 **49 个 `test_*.py`**（unit / integration / acceptance），用 pytest 运行。
上游 `tox.ini` 把 pytest 钉在 **3.3.2**（2018 年的版本，py3.12 上无法安装），因此这里用**现代 pytest**
跑**同一套用例**，并在 PR 正文与 notes 中如实说明该偏离。
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

PIP_MIRROR = ["--trusted-host", "pypi.cnb.cool"]


class VintConan(ConanFile):
    name = "vint"
    version = "0.3.21"
    package_type = "application"
    description = "Vim script（viml）静态检查工具：报告语法与风格问题，可接入 CI 对 .vim 脚本做 lint"
    license = "MIT"
    url = "https://github.com/Vimjas/vint"
    homepage = "https://github.com/Vimjas/vint"
    topics = ("vim", "vimscript", "lint", "static-analysis", "cli")
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def _python(self):
        return shutil.which("python3") or "python3"

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def build(self):
        py = self._python()
        pyroot = os.path.join(self.package_folder, "python")
        os.makedirs(pyroot, exist_ok=True)
        # ① 运行时依赖（纯 Python 轮子）
        # ⚠️ 必须带 **`setuptools<81`**：vint 在 `vint/linting/cli.py:4` 直接 `import pkg_resources`
        #    （用它读自身版本），却**没有把 setuptools 声明**在 requirements 里；
        #    而新版 setuptools（实测 84.0.0）**已移除 `pkg_resources`** → 装最新版仍报
        #    `ModuleNotFoundError: No module named 'pkg_resources'`，连 `import vint` 都失败。
        #    钉到 80.x 后实测 `import pkg_resources, vint` 成功、上游用例 210 passed。
        self.run('%s -m pip install --no-cache-dir --upgrade --target="%s" %s '
                 'PyYAML ansicolor chardet "setuptools<81"'
                 % (py, pyroot, " ".join(PIP_MIRROR)), cwd=self.source_folder, env="conanbuild")
        # ② 本体：--no-deps（排除 setup.py 里那批 py2 backport）
        self.run('%s -m pip install --no-cache-dir --no-deps --target="%s" .' % (py, pyroot),
                 cwd=self.source_folder, env="conanbuild")
        # ③ 上游验收测试直接调用**仓库内的 `bin/vint`** 启动脚本（`test/acceptance/test_cli.py`
        #    里写死 `['bin/vint', …]`，相对 cwd=源码根）。归档里该文件是 775，但经下载/解包后
        #    **可执行位可能丢失** → 这里显式补回；否则 8 个验收用例会因无法执行而失败（实测）。
        for rel in ("bin/vint", "bin/vint.exe"):
            p = os.path.join(self.source_folder, rel)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
                break
        self._run_upstream_tests()

    # ── 跑上游自带的 49 个用例（现代 pytest）────────────────────────────
    def _run_upstream_tests(self):
        py = self._python()
        env_dir = os.path.join(self.build_folder, "testenv")
        os.makedirs(env_dir, exist_ok=True)
        self.run('%s -m pip install --no-cache-dir --upgrade --target="%s" %s "pytest>=7" mock'
                 % (py, env_dir, " ".join(PIP_MIRROR)), env="conanbuild")
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join([
            env_dir,
            os.path.join(self.package_folder, "python"),
            env.get("PYTHONPATH", ""),
        ]).strip(":")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # ④ 上游验收测试调用的 `bin/vint` 的 shebang 是 `#!/usr/bin/env python`，而本环境只有
        #    `python3`、没有 `python` 这个名字 → 实测 `env: exec python: No such file or directory`，
        #    8 个验收用例全部失败。这里造一个 `python` shim 并把其目录前置到 PATH（不改上游文件）。
        shim_bin = os.path.join(env_dir, "shim-bin")
        os.makedirs(shim_bin, exist_ok=True)
        shim = os.path.join(shim_bin, "python")
        if not os.path.exists(shim):
            try:
                os.symlink(py, shim)
            except OSError:
                pass
        env["PATH"] = shim_bin + ":" + env.get("PATH", "")
        # ⑤ 关掉 Python 警告：验收测试断言被测命令的输出**以 `vint ERROR:/DEBUG:` 开头**，而现代
        #    Python 会把警告打到同样的输出流里 —— 实测两类噪声：
        #    ① setuptools 80.x 的 `UserWarning: pkg_resources is deprecated as an API`；
        #    ② py3.12 对老代码的 `SyntaxWarning: invalid escape sequence` / `"is not" with 'int'`。
        #    这些与被测行为无关，属于解释器/依赖版本带来的环境噪声 → 测试环境统一静音。
        env["PYTHONWARNINGS"] = "ignore"
        r = subprocess.run([py, "-m", "pytest", "-q", "test"], cwd=self.source_folder,
                           capture_output=True, text=True, timeout=1800, env=env)
        out = (r.stdout or "") + (r.stderr or "")
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        self.output.info("[upstream tests] 尾部：%s" % " | ".join(lines[-6:]))
        m = re.search(r"(\d+)\s+passed", out)
        passed = int(m.group(1)) if m else 0
        if r.returncode != 0 or passed == 0:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游 pytest 未通过（rc=%d，passed=%d）：\n%s"
                % (r.returncode, passed, out[-900:]))
        self.output.info("[upstream tests] 上游用例通过 %d 个 ✓（现代 pytest 跑上游同一套用例）" % passed)

    def package(self):
        pyroot = os.path.join(self.package_folder, "python")
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        # ⚠️ 不能依赖 pip 生成的 console script：`pip install --target` 会把脚本写到目标根目录，
        #    而那里已经有同名的 `vint/` 包目录 → 脚本**静默未生成**（实测 `<pkg>/python` 下只有
        #    `chardetect` 等其它脚本，没有 `vint`）。也注意 `vint` 没有 `__main__`，
        #    所以 `python -m vint` 同样不可用。这里按上游 setup.py 的入口
        #    `console_scripts: vint = vint:main` 自己生成 `<包>/bin/vint`。
        launcher = os.path.join(self.package_folder, "bin", "vint")
        with open(launcher, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nexec "%s" -c "import sys; from vint import main; sys.exit(main())" "$@"\n'
                     % self._python())
        os.chmod(launcher, 0o755)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.define_path("PYTHONPATH", os.path.join(self.package_folder, "python"))
        self.buildenv_info.define_path("PYTHONPATH", os.path.join(self.package_folder, "python"))
        self.cpp_info.set_property("cmake_file_name", "vint")

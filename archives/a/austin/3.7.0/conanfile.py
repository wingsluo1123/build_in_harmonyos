#!/usr/bin/env python3
"""Conan recipe for austin 3.7.0 — a CPython frame stack sampler (C, autotools).

**依赖（都已在仓库归档 → 按"算依赖先扣掉仓库已有"的口径不算阻塞）**：
- `argp-standalone/1.5.0`：musl/OHOS 没有 glibc 的 argp，而上游 `src/argparse.c` 直接
  `#include <argp.h>` → 由它提供（仓库 `archives/a/argp-standalone` ✓，制品仓有二进制 ✓）
- `libunwind/1.6.2`：`austinp`（原生采样器）需要 `libunwind-ptrace.h`；上游在缺它时会自行
  `not building austinp: missing libunwind` 继续构建 CLI（仓库 `archives/l/libunwind` ✓）

**构建**：autotools（源码里只有 `configure.ac`，须 autoreconf 自举）→ `automake`/`libtool` 走
`tool_requires`，**与仓库里 `argp-standalone` 的做法完全一致**。另需复刻它那条经验：
OHOS/HMDFS 上 `configure` 里的 `umask 077` 建临时目录会 `Permission denied` →
**必须在 autoreconf 之后**把 configure 里的 `umask 077` 改成 `umask 022`（放在前面会被重新生成覆盖）。

**上游测试（如实记录）**：austin 自带测试套件，但 `test/run.sh` **写死了作者本机路径**：
`source /tmp/austin-test/bin/activate`（/tmp 在本机只读）+ `LD_LIBRARY_PATH=/Users/gabriele/Projects/
libunwind/src/.libs/`；用例为 pytest + ptrace 型，还需 `austin-python`/`pytest-xdist`/`psutil`
→ **本机与 CI 都跑不起来**。故与 rp 同法：**在配方里补能真跑的功能级测试**并把构成摊开，不冒充
"上游测试全过"。
"""
import glob
import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# ptrace 受限的特征（沙箱/CI 里可能不允许 attach → 如实记录，不硬判为失败）
PTRACE_DENIED = ("Operation not permitted", "ptrace", "Permission denied")


class AustinConan(ConanFile):
    name = "austin"
    version = "3.7.0"
    description = ("austin — a CPython frame stack sampler with a native "
                   "sampler (austinp); C, autotools")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/P403n1x87/austin"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("argp-standalone/1.5.0")
        self.requires("libunwind/1.6.2")

    def build_requirements(self):
        # 仓库里 argp-standalone 同款：只有 configure.ac，须 autoreconf 自举；设备缺 automake/libtool
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # 依赖的 include/lib **必须显式带上**：实测只靠 AutotoolsToolchain 自动收集，
        # austin 的编译行里不会出现 argp 的 include（于是 args.c:186 `#include <argp.h>` 找不到）。
        for ref in ("argp-standalone", "libunwind"):
            try:
                dep = self.dependencies[ref]
            except Exception:
                continue
            inc = os.path.join(dep.package_folder, "include")
            lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(inc):
                tc.extra_cflags.append("-I" + inc)
                tc.extra_cxxflags.append("-I" + inc)
            if os.path.isdir(lib):
                tc.extra_ldflags.append("-L" + lib)
        # 上游 `src/Makefile.am` 是 `austin_LDADD = -lm`（**没有 argp**）→ 链接期需要 -largp。
        # 用 autoconf 惯例的 `LIBS=` 传：它会落在链接行**末尾**（静态库必须在目标文件之后才生效）；
        # 放进 LDFLAGS 会跑到目标文件之前，静默漏符号。
        tc.configure_args.append("LIBS=-largp")
        tc.generate()

    def build(self):
        at = Autotools(self)
        # ⚠️ CI 上 `autoreconf` 报 `autoreconf: error: …/aclocal failed with exit status: 1`：
        #    根因是 conan 注入的 PERL5LIB/PERL5OPT 指向依赖包 perl 里的库目录，宿主的 aclocal/automake
        #    加载到半套 Pod::*/Cwd 就崩（仓库知识库里已记录：宿主 perl + 包内 PERL5LIB 必冲突）。
        #    自举前清掉，让 aclocal 用宿主 perl 自己的模块（不改上游任何东西）。
        for _v in ("PERL5LIB", "PERL5OPT", "PERL_MM_OPT", "PERL_LOCAL_LIB_ROOT"):
            os.environ.pop(_v, None)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            # ⚠️ 受限 Worker 上 autoreconf 的**第一个 fork** 就可能失败（CI #94811 实测：
            #    `/system/bin/sh: …conautotoolstoolchain.sh[13]: can't fork - try again`
            #    → `autoreconf: error: …/aclocal failed with exit status: 1` → 构建停在自举第一步）。
            #    这是 Worker 侧 fork/exec 配额被同批构建打满，不是源码或配方问题。
            #    配方侧能做的有限缓解：**退避重试**（并发高峰过去通常就能过），
            #    最终仍失败则给出明确诊断，避免被误读成"代码不兼容"。
            #    （已核实：上游没有自带已生成 configure 的源可换 —— GitHub release 只提供**预编译
            #      二进制**，PyPI 上的同名 austin 是另一个 Python 包，故无法用"换源免自举"这条路。）
            last_exc = None
            for attempt in range(1, 4):
                try:
                    at.autoreconf()
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    self.output.warning("[build] autoreconf 第 %d/3 次失败（%s）→ 退避 %d 秒后重试"
                                        % (attempt, str(exc)[:110], 15 * attempt))
                    time.sleep(15 * attempt)
            if last_exc is not None:
                raise ConanInvalidConfiguration(
                    "[build] autoreconf 连续 3 次失败。本工程源码树没有预生成的 configure，必须自举；"
                    "若错误含 can't fork / Resource temporarily unavailable，属 Worker 侧 fork 配额耗尽"
                    "（同批多个构建并发所致），换 Worker 或降低并发后重跑即可，与源码兼容性无关。"
                    "原始错误：%s" % str(last_exc)[:200])
        # ⚠️ 对 configure 的修补必须在 autoreconf 之后：自举会重新生成 configure
        patched = 0
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                text = open(cfg, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write(text.replace("umask 077", "umask 022"))
                patched += 1
        self.output.info("[build] 已把 %d 个 configure 的 umask 077 改为 022（HMDFS 目录权限）" % patched)
        at.configure()
        at.make(args=["-j1"])
        self._run_added_tests()
        self._run_upstream_tests()

    # ── 补的功能级测试（上游 pytest 套件在本机/CI 跑不起来，见 docstring）──
    def _find_exes(self):
        out = {}
        for p in glob.glob(os.path.join(self.build_folder, "**", "*"), recursive=True):
            base = os.path.basename(p)
            if base not in ("austin", "austinp") or not os.path.isfile(p) or not os.access(p, os.X_OK):
                continue
            try:
                with open(p, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        out[base] = p
            except OSError:
                continue
        return out

    def _run_added_tests(self):
        exes = self._find_exes()
        if "austin" not in exes:
            raise ConanInvalidConfiguration(
                "[added tests] 构建目录里没找到 ELF 可执行的 austin（找到：%s）" % sorted(exes))
        self.output.info("[added tests] 产物：%s" % ", ".join(
            "%s(%d 字节)" % (k, os.path.getsize(v)) for k, v in sorted(exes.items())))

        # ① --help：硬判
        r = subprocess.run([exes["austin"], "--help"], capture_output=True, text=True, timeout=300)
        out = r.stdout + r.stderr
        if r.returncode != 0 or ("Usage" not in out and "-h" not in out):
            raise ConanInvalidConfiguration(
                "[added tests] `austin --help` 不成立（rc=%d）：\n%s" % (r.returncode, out[-500:]))
        self.output.info("[added tests] ① `austin --help` rc=0 且打印用法 ✓")

        # ② 真实采样一次：**尽力而为并如实记录**，不据此让 build 失败（本环境相关：
        #   仓库的 libunwind 不含 libunwind-ptrace.h → 上游 configure 跳过 austinp；
        #   且构建环境里目标解释器未必可达）。成功则打印 ✓，失败则打印原因并注明"不计为通过"。
        import shutil
        py = shutil.which("python3") or "/data/service/hnp/bin/python3"
        proc = subprocess.run(
            [exes["austin"], "-i", "1000", "-o", "/dev/null", "--", py, "-c",
             "import time; time.sleep(3)"],
            capture_output=True, text=True, timeout=600)
        blob = proc.stdout + proc.stderr
        if proc.returncode == 0:
            self.output.info("[added tests] ② 真实采样：rc=0（对 %s 进程采样并写出）✓" % py)
        else:
            self.output.warning(
                "[added tests] ② 真实采样未成功（rc=%d，目标 %s）——**如实记录，不计为通过**：\n%s"
                % (proc.returncode, py, blob.strip()[-400:]))

    # ── 上游用例：N=55（cunit 17 + functional 33 + integrity 3 + support 2）───
    def _run_upstream_tests(self):
        """如实记录上游 55 个用例在本平台的**可执行性**，并给出可复现的技术原因。

        ⚠️ 实测**上游测试框架自身拒绝 HarmonyOS**：`test/utils.py` 里的 `python(version)` 只接受
        `Windows` / `Darwin` / `Linux` 三种 `platform.system()`，其余一律
        `raise RuntimeError(f"Unsupported platform: {platform.system()}")`。
        在本机跑上游套件（`pytest test/integrity` 等）实测得到：
            RuntimeError: Unsupported platform: HarmonyOS      （test/utils.py:89）
        这属于**上游硬编码的平台限制**（不是缺依赖、不是人为跳过），因此本包声明
        「上游 N=55；可执行 0/55；原因＝上游 harness 不支持 HarmonyOS」，并把上述报错原文附在
        PR 正文作为证据。

        下面两处断言都是**能失败**的：一旦上游放开平台门（或我们改在 Linux 上构建），
        构建就会失败并提示应改为真实执行 —— 避免"悄悄不跑还声称通过"。
        """
        utils_py = os.path.join(self.source_folder, "test", "utils.py")
        text = ""
        if os.path.isfile(utils_py):
            try:
                text = open(utils_py, encoding="utf-8", errors="ignore").read()
            except OSError:
                text = ""
        if 'raise RuntimeError(f"Unsupported platform:' not in text:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游 test/utils.py 的平台门已变化，请重新评估上游 55 个用例的可执行性")
        import platform as _platform
        if _platform.system() in ("Windows", "Darwin", "Linux"):
            raise ConanInvalidConfiguration(
                "[upstream tests] 当前 platform.system()=%r 已被上游平台门接受 → 应改为真实执行上游 55 个用例"
                % _platform.system())
        self.output.info(
            "[upstream tests] 上游 N=55（cunit 17 + functional 33 + integrity 3 + support 2）；可执行 0/55。"
            "原因（可复现）：上游 harness 硬编码平台门 —— test/utils.py 的 python() 仅接受 "
            "Windows/Darwin/Linux，本机 platform.system()=%r → 实跑即 "
            "`RuntimeError: Unsupported platform: HarmonyOS`（test/utils.py:89，已在 integrity 子集上实测）"
            % _platform.system())

    def package(self):
        # ⚠️ 不用 at.install()：它按 `tools.build:jobs` 发 `-jN`，CI 上实测是 `make install … -j20`
        #    （构建 #94215）——受限 Worker 上安装到一半就
        #    `/data/service/hnp/bin/bash: fork: retry: Resource temporarily unavailable` ×8
        #    → `make[2]: *** [Makefile:417: install-binPROGRAMS] Error 254`。
        #    安装本身不需要并行，故自己调用安装命令并锁 `-j1`（与 rp/mfgtools 的构建侧处置一致）。
        self.run('make install -j1 DESTDIR="%s"' % self.package_folder, cwd=self.build_folder)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

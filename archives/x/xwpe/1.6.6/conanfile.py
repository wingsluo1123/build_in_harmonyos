#!/usr/bin/env python3
"""Conan recipe for xwpe 1.6.6 — 面向程序员的终端编辑器/IDE（C / autotools）。

**上游**：codeberg `mendezr/xwpe`；源取 **Debian 源包 orig**（xwpe_1.6.6.orig.tar.xz，版本一致）。
**依赖**（上游 `configure.ac` 实测）：
  必需 —— `ncursesw`（`PKG_CHECK_MODULES([NCURSESW], [ncursesw])`，仓库 ncurses 6.6 的包里有
  **ncursesw.pc** ✓）+ `json-c`（DAP 调试客户端的线格式，仓库/制品仓有 `json-c/0.18` ✓）。
  可选 —— X11 / Xft+fontconfig / cairo / pango / libvterm / gpm。按"依赖先扣仓库已有"的口径，
  这里**关掉全部可选层**（`--without-x`、`--without-gpm`），只做文本版 `we`：X/Xft/cairo/pango 都不在
  该库的依赖清单里，开了反而引入清单外依赖。
**构建**：autotools（源码无 `configure`，须 autoreconf；`automake`/`libtool` 走 `tool_requires`，
照仓库 `argp-standalone` 范式）；`configure` 里的 `umask 077` 必须在 autoreconf **之后**改成 022。

**上游测试**：**有** ✓ —— 分三层（`tests/run-tests.sh`）：
  ①C 单元测试 `make check`（不需要 pyte/pytest ✓）
  ②pyte/pytest 的 TUI 场景（需要 pyte+pytest，缺则会尝试建 venv=需要网络 ✗）
  ③X11 GUI 层（缺 headless X 栈会**自动跳过** ✓，不会判失败）
本配方把**①`make check` 作为硬门禁**（真跑上游自带单元测试），②③尽力而为并如实记录。
"""
import glob
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XwpeConan(ConanFile):
    name = "xwpe"
    version = "1.6.6"
    description = ("xwpe — a programmer's editor/IDE for the terminal "
                   "(C, autotools; LSP/DAP capable)")
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/mendezr/xwpe"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("json-c/0.18")

    def build_requirements(self):
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
        # 可选层全部关掉：X/Xft/cairo/pango 都不在该库的依赖清单里，开了会引入清单外依赖
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--without-gpm")
        # ncursesw / json-c 都走 pkg-config → 必须生成 .pc
        PkgConfigDeps(self).generate()
        tc.generate()

    # ── 测试临时目录的可移植性修正（不改判定逻辑）──────────────────
    def _patch_tests_tmpdir(self):
        """上游部分用例把临时目录**写死**成 /tmp/...（如 test_checkheader.c 的
        `#define TDIR "/tmp/xwpe_chktest"`）。本构建沙箱 /tmp 是只读 erofs，mkdir/fopen 会失败 →
        用例直接 abort（实测 rc=-6）。这里只做**可移植性修正**：把 `"/tmp/` 换成相对路径 `"./`，
        目录就建在 cwd（= 源码根，可写）下，**判定逻辑一字未改**。
        """
        changed = 0
        for c in glob.glob(os.path.join(self.source_folder, "tests", "*.c")):
            try:
                t = open(c, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            new = re.sub(r'"/tmp/', '"./', t)
            if new != t:
                with open(c, "w", encoding="utf-8") as fh:
                    fh.write(new)
                changed += 1
        if changed:
            self.output.info("[patch] 已把 %d 个测试文件里写死的 /tmp/ 路径改成相对路径"
                             "（可移植性修正，判定逻辑未改）" % changed)

    def build(self):
        self._patch_tests_tmpdir()
        at = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（Debian orig 常见），先 autoreconf 自举")
            at.autoreconf()
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                text = open(cfg, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write(text.replace("umask 077", "umask 022"))
        at.configure()
        # 上游的 info 文档规则会调用 texinfo 的 makeinfo；本环境没有它（实测
        # build-aux/missing: makeinfo: command not found 直接中断 make）。传 MAKEINFO=true 让
        # info 文档规则变成空操作——文档不是适配必需品，也不改上游 Makefile.am。
        at.make(args=["-j1", "MAKEINFO=true"])
        self._run_upstream_tests()

    # ── 上游自带测试：C 单元测试逐个直跑（硬门禁）──────────────
    def _run_upstream_tests(self):
        # ① 上游自带 C 单元测试（顶层 Makefile.am:187 `check_PROGRAMS = …`）——硬门禁。
        #    两处环境坑，都是实测出来的：
        #    a) 必须在**构建目录**里跑（out-of-source；源码目录没有 Makefile）
        #       ——首版在源码目录跑，得到 "No rule to make target 'check'"。
        #    b) **不走 automake 的 `make check` / check-TESTS 驱动**：那套驱动在本沙箱的文件系统上会失败
        #       `shell-init: error retrieving current directory: getcwd: cannot access parent
        #        directories: Not supported`（环境限制，不是测试本身失败）。
        #    → 改为：解析出 check_PROGRAMS 列表，构建后**逐个直接执行**，逐个判返回码。
        mf = os.path.join(self.build_folder, "Makefile")
        names = []
        if os.path.isfile(mf):
            txt = open(mf, encoding="utf-8", errors="ignore").read()
            m = re.search(r"^check_PROGRAMS\s*=\s*(.+)$", txt, re.M)
            if m:
                # 名单可能跨多行（续行以 `\` 结尾，且下一行以 TAB 开头）→ 一直读到没有续行为止。
                # ⚠️ 必须先滤掉空行：m.end() 之后第一项就是空串，否则第一轮就结束（首版 18 个只拿到 2 个）。
                lines = [m.group(1)]
                rest = [l for l in txt[m.end():].splitlines() if l.strip()]
                i = 0
                while lines[-1].rstrip().endswith("\\") and i < len(rest):
                    lines.append(rest[i])
                    i += 1
                raw = " ".join(l.rstrip().rstrip("\\") for l in lines).split()
                # 生成的 Makefile 里名字可能带未展开的变量（如 `test_checkheader$(EXEEXT)`）→ 去掉
                names = [re.sub(r"\$\([A-Za-z_]+\)", "", n).strip() for n in raw]
                names = [n for n in names if n]
        if not names:
            raise ConanInvalidConfiguration(
                "[upstream tests] 没能从构建目录 Makefile 里解析出 check_PROGRAMS（期望有上游 C 单元测试）")

        r = subprocess.run(["make", "-j1", "MAKEINFO=true"] + names, cwd=self.build_folder,
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                "[upstream tests] 构建上游单元测试程序失败（rc=%d）：\n%s"
                % (r.returncode, ((r.stdout or "") + (r.stderr or ""))[-600:]))

        passed, skipped, failed, logs, skipped_logs = 0, [], [], [], []
        # automake 在 `make check` 时会导出 srcdir/builddir 等变量，上游测试用它们定位数据文件；
        # 直跑时缺失 → 首版实测两个用例分别 SIGABRT(-6) 与 rc=1。这里显式补齐。
        tenv = dict(os.environ)
        # ⚠️ 必须带上 conan 依赖的运行时库路径：直跑首版没带，测试二进制跑到了环境里那个不完整的
        #    json-c，报 `json_tokener_get_error: symbol not found`（rc=127）——不是测试本身的问题。
        tenv["LD_LIBRARY_PATH"] = ":".join(
            os.path.join(self.dependencies[r].package_folder, "lib")
            for r in ("ncurses", "json-c")) + ":" + tenv.get("LD_LIBRARY_PATH", "")
        # ⚠️ TMPDIR：本沙箱 /tmp 只读，多个用例用 mkdtemp() 建临时目录 → 实测直接 "FAIL: mkdtemp"。
        #    指到构建目录下一个可写目录。
        _tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(_tmp, exist_ok=True)
        tenv["TMPDIR"] = _tmp
        tenv.update({
            "srcdir": self.source_folder, "abs_srcdir": self.source_folder,
            "top_srcdir": self.source_folder, "abs_top_srcdir": self.source_folder,
            "builddir": self.build_folder, "abs_builddir": self.build_folder,
            "top_builddir": self.build_folder, "abs_top_builddir": self.build_folder,
        })
        for n in names:
            exe = os.path.join(self.build_folder, n)
            if not os.path.isfile(exe):
                failed.append("%s(未生成)" % n)
                continue
            try:
                # 在**源码根目录**里跑：上游用例用相对路径打开数据文件（如 test_syntax_def.c 的
                # `path = "syntax_def"`，该文件在源码根 ✓；在构建目录里跑会 "cannot open syntax_def"）。
                p = subprocess.run([exe], cwd=self.source_folder, capture_output=True,
                                   text=True, timeout=600, env=tenv)
            except Exception as exc:                     # noqa: BLE001
                failed.append("%s(%s)" % (n, str(exc)[:40]))
                continue
            if p.returncode == 0:
                passed += 1
            elif p.returncode == 77:
                # 77 = automake 约定的 SKIP（上游在缺外部工具时主动跳过）。这里**不当作通过**，
                # 而是把该用例自己的说明打出来，便于确认到底缺什么、能不能补装。
                skipped.append(n)
                skipped_logs.append("%s: %s" % (n, (((p.stdout or "") + (p.stderr or "")).strip()
                                                    .splitlines() or ["(无输出)"])[-1][:120]))
            else:
                failed.append("%s(rc=%d)" % (n, p.returncode))
                logs.append((((p.stdout or "") + (p.stderr or "")).strip())[-250:])
        self.output.info("[upstream tests] ① 上游自带 C 单元测试逐个直跑：通过 %d / 跳过 %d / 共 %d ✓"
                         % (passed, len(skipped), len(names)))
        if skipped:
            self.output.info("[upstream tests]    跳过（rc=77）原因：\n      %s"
                             % "\n      ".join(skipped_logs))
        if failed:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游单元测试未通过 %d 个：%s\n%s"
                % (len(failed), ", ".join(failed[:8]), "\n".join(logs)[-700:]))

        # ② 上游 tests/run-tests.sh（pyte 层需 pyte+pytest，X11 层缺栈自动跳过）：该脚本自己 `cd` 到
        #    **源码目录**再跑 make，假设 in-source 构建 → 在 conan 的 out-of-source 布局下用不了。
        #    如实记录，不纳入门禁（不把"跑不了"说成"跑过"；C 单元测试已由 ① 覆盖）。
        if os.path.isfile(os.path.join(self.source_folder, "tests", "run-tests.sh")):
            self.output.warning(
                "[upstream tests] ② tests/run-tests.sh 假设 in-source 构建（脚本自行 cd 源码目录跑 make），"
                "与 conan 的 out-of-source 布局不兼容 → 本配方不执行它")

    def package(self):
        at = Autotools(self)
        # install 目标同样会触碰 info 文档规则（实测 install-recursive → docs/xwpe.info → makeinfo 缺失，
        # Error 127）→ 与 build 一致，传 MAKEINFO=true 让文档步骤空转。
        at.install(args=["MAKEINFO=true"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

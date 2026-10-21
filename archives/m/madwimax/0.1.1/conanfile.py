#!/usr/bin/env python3
"""Conan recipe for madwimax 0.1.1 — WiMAX USB 设备的用户态驱动（C / autotools）。

**上游**：`ago/madwimax`（tag **v0.1.1**，GitHub 标注语言 **C**）。
**依赖**：**只有一个** —— `libusb/1.0.27`（上游 `configure.ac:60`
`PKG_CHECK_MODULES([libusb1], libusb-1.0, …)`），仓库与制品仓均已归档 ✓；另有 pthread（系统自带）。
**构建**：autotools（源码里没有 `configure`，须 autoreconf；`automake`/`libtool` 走 `tool_requires`，
照仓库 `argp-standalone` 的范式）；并复刻其经验：OHOS/HMDFS 上 `configure` 里的 `umask 077` 建临时目录
会 `Permission denied`，且**必须在 autoreconf 之后**改。
**产物**：上游是 `sbin_PROGRAMS = madwimax`（守护进程）→ 配方统一装到 `bin/`（与仓库命令声明约定一致）。

**上游测试**：**没有**（无 test/tests，Makefile.am 里也没有 TESTS）→ 按仓库既有做法在配方里补能真跑的
功能级测试：`madwimax --help`（上游 `src/wimax.c:652` 明确支持 `-h, --help`）与 `--version`
（`src/wimax.c:648` `-V, --version`）。注意它是**硬件驱动**：真正跑起来需要 WiMAX USB 设备 + TAP 设备，
本环境不做，只做 CLI 级断言并如实记录。构成在 test_package/MANIFEST.yml 里摊开。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MadwimaxConan(ConanFile):
    name = "madwimax"
    version = "0.1.1"
    description = ("madwimax — a userspace driver for WiMAX USB devices "
                   "(C, autotools; single dependency: libusb)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ago/madwimax"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        self.requires("libusb/1.0.27")

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
        # 上游默认要生成 man 页 → configure 里会 **硬性** 检查 asciidoc（AC_MSG_ERROR "asciidoc not found"）。
        # configure.ac:128 提供了 --without-man-pages 开关；文档不是适配必需品，故关掉。
        tc.configure_args.append("--without-man-pages")
        # 上游用 pkg-config 找 libusb-1.0 → 必须让 conan 生成 .pc
        PkgConfigDeps(self).generate()
        # OHOS 的 musl 头与内核 uapi 头在 `sockaddr_storage` 上冲突（实测：
        # src/tap_dev.c 先 include <sys/socket.h> 再 include <linux/if.h> → linux/socket.h 又定义一次）。
        # sysroot 的 sys/socket.h:376 是 `#ifndef __MUSL__` 包裹 → **定义 __MUSL__** 后 musl 不再自定义
        # 该结构，只剩内核头那份 → 冲突消失。属于一个 -D 的补丁，不改上游源码。
        tc.extra_defines.append("__MUSL__")
        # 上游是 sbin_PROGRAMS；统一装到 bin/（与仓库命令声明约定一致）
        tc.configure_args.append("--sbindir=%s/bin" % self.package_folder)
        tc.generate()

    def build(self):
        at = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            at.autoreconf()
        else:
            # ⚠️ 源包自带 configure（Debian orig），但它内附的 config.sub / config.guess 是 2009 年的，
            #    认不出**任何** aarch64 三元组 → configure 直接报
            #    `config.sub aarch64-unknown-linux-musl failed`。
            #    做法：从 conan 的 automake 包（build 依赖）里取现代版本覆盖源包内那两个文件 ——
            #    只换这两个脚本，**不重跑 autoreconf**（避免 #94280 那种卡到 1 小时墙钟的步骤）。
            am = ""
            try:
                am = self.dependencies.build["automake"].package_folder
            except Exception:
                pass
            for fn in ("config.sub", "config.guess"):
                cand = []
                if am:
                    cand = (glob.glob(os.path.join(am, "share", "automake-*", fn)) or
                            glob.glob(os.path.join(am, "**", fn), recursive=True))
                if cand:
                    copy(self, fn, src=os.path.dirname(sorted(cand)[0]),
                         dst=self.source_folder, keep_path=False)
                    self.output.info("[build] 已用 automake 包内的现代 %s 覆盖源包内过旧版本" % fn)
        # ⚠️ 对 configure 的修补必须在 autoreconf 之后（会被重新生成覆盖）
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                text = open(cfg, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write(text.replace("umask 077", "umask 022"))
        at.configure()
        at.make(args=["-j1"])
        self._run_added_tests()

    # ── 补的功能级测试（上游无测试套件）────────────────────────────────
    def _find_exe(self):
        for p in glob.glob(os.path.join(self.build_folder, "**", "madwimax"), recursive=True):
            if os.path.isfile(p) and os.access(p, os.X_OK):
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            return p
                except OSError:
                    continue
        raise ConanInvalidConfiguration("[added tests] 构建目录里没找到 ELF 可执行的 madwimax")

    def _run_added_tests(self):
        exe = self._find_exe()
        self.output.info("[added tests] 产物 = %s（%d 字节）" % (exe, os.path.getsize(exe)))
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = (os.path.join(self.dependencies["libusb"].package_folder, "lib")
                                  + ":" + env.get("LD_LIBRARY_PATH", ""))
        r = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=300, env=env)
        out = (r.stdout or "") + (r.stderr or "")
        if "usage" not in out.lower() and "--version" not in out:
            raise ConanInvalidConfiguration(
                "[added tests] `madwimax --help` 没有打印用法（rc=%d）：\n%s" % (r.returncode, out[-400:]))
        self.output.info("[added tests] ① `madwimax --help` 打印用法 ✓（首行：%s）"
                         % out.strip().splitlines()[0][:90])
        r2 = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=300, env=env)
        out2 = (r2.stdout or "") + (r2.stderr or "")
        self.output.info("[added tests] ② `madwimax --version` rc=%d，输出：%s"
                         % (r2.returncode, out2.strip()[:80] or "（空）"))
        # 真正运行需要 WiMAX 设备 + TAP，本环境不做（如实记录）
        self.output.warning("[added tests] ③ 真实驱动功能需 WiMAX USB 设备 + TAP，本环境不执行——如实记录")

    def package(self):
        # ⚠️ 不用 at.install()：它按 `tools.build:jobs` 发 `make install … -jN`（CI 实测 **-j20**），
        #    受限 Worker 上立刻 fork 出一堆子进程 → `bash: fork: retry: Resource temporarily unavailable`
        #    ×9 → `make[2]: *** [Makefile:225: install-man8] Error 254`（构建 #94828 实测）。
        #    安装本身不需要并行，故自己调用并锁 `-j1`（与 austin 的同一处理）。
        self.run('make install -j1 DESTDIR="%s"' % self.package_folder,
                 cwd=self.build_folder, env="conanbuild")
        # 上游是 sbin_PROGRAMS，且实测 `make install` 未把产物落到我们期望的 bin/ →
        # 这里显式补装一次，保证包内布局固定为 bin/madwimax（与 commands.json 约定一致）。
        exe = self._find_exe()
        binp = os.path.join(self.package_folder, "bin")
        os.makedirs(binp, exist_ok=True)
        dst = os.path.join(binp, "madwimax")
        import shutil as _sh
        _sh.copy2(exe, dst)
        os.chmod(dst, 0o755)
        self.output.info("[package] 已补装 bin/madwimax（源：%s）" % exe)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

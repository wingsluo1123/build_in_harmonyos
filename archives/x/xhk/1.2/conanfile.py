#!/usr/bin/env python3
"""Conan recipe — xhk 1.2 (X11 XKB half-keyboard interpreter)

上游: kbingham/xhk — XLib HalfKeyboard implementation（单手打字：空格键作为
修饰键镜像键盘另一半；README 记录作者 2014 年肘部手术后为此而写）。
构建系统: GNU autotools (configure.ac + Makefile.am + src/Makefile.am)
许可证: GPL-2.0-or-later（xhk.c 头部声明 "version 2 ... or any later version"）
主页: https://github.com/kbingham/xhk

OHOS (aarch64-linux-ohos) 适配要点:
  - GitHub tag archive (xhk-v1.2) 不含预生成的 configure（autoreconf 产物
    不进版本库），build() 先 `autoreconf -fi` 自举；构建机缺 automake/
    aclocal 时由 tool_requires automake/1.18 经 build profile 解析
    （同 archives/x/xsel/1.2.1、afuse）。
  - configure.ac 依次 PKG_CHECK_MODULES x11>=1.6 / xi>=1.6 / xtst>=1：
    aclocal 阶段需要 pkg.m4，configure 阶段需要 x11.pc / xi.pc / xtst.pc。
    .pc 由 conan 依赖 libx11/6.4.0 + libxi/6.1.0 + libxtst/1.2.5 经
    PkgConfigDeps 生成（三者的 OHOS armv8 binary 均已发布，W0 预检通过）。
  - 制品仓 X11 家族按 .so 主版本命名（libX11.so.6.4.0 → libx11/6.4.0）。
    libxtst/1.2.5 自身 pin libxi/6.1.0，而 libxi/1.8.3 会拉入另一条线，
    两条线不能同图，故统一取 6.x 版本线（同 archives/x/xmacro、
    archives/x/xclicker 的既有结论）。
  - OHOS 下对 bin/xhk 自签名（E549），未签名 ELF 不可执行；本机/本地 WSL
    交叉编译环境无 binary-sign-tool 时跳过并告警（用 qemu 做运行验证）。

平台限制（规则 7）: OHOS 无 X server，xhk 的运行期功能（XInput2 抓键、
XTest 注入）需真实 X 环境，归入真机验证；headless 环境只做确定性冒烟。
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XhkConan(ConanFile):
    name = "xhk"
    version = "1.2"
    description = ("XLib HalfKeyboard interpreter — one-handed typing where the "
                   "space bar mirrors the opposite half of the keyboard")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kbingham/xhk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须兼容 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xhk supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # 上游 src/Makefile.am 的 xhk_LDADD = @X11_LIBS@ @XI_LIBS@ @XTST_LIBS@
        # 逐条映射到制品仓已发布的同名 conan 包（R36: CI worker 无本机 X11）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxi/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxtst/1.2.5", transitive_headers=True, transitive_libs=True)
        # X11/keysymdef.h、X11/XKBlib.h 及 X11/extensions 协议头来自 xorgproto
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        # tag archive 无预生成 configure，须 autoreconf 自举；真机缺
        # automake/aclocal（E178），经 tool_requires 用 build profile 解析。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 把 libx11/libxi/libxtst 的 x11.pc / xi.pc / xtst.pc
        # （及其传递依赖 .pc）生成到 generators 目录，供 configure 的
        # PKG_CHECK_MODULES 使用。
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # autoreconf 生成的 config.guess 认不出 HarmonyOS（uname -s 输出
        # "HarmonyOS"）时会报 'cannot guess build type'；显式指定 triplet
        # 绕过（同 archives/x/xsel/1.2.1、a52dec、xcb-util-renderutil）。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        # HMFS/HMDFS 不支持 getcwd：把进程 cwd 切到 build_folder 并预置 PWD，
        # 让子进程 shell 的 pwd 内建在 getcwd 失败时走逻辑路径 $PWD
        # （同 xsel/aribb24/1.0.4）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder

        os.umask(0)
        apply_conandata_patches(self)
        self._prepare_aclocal_path()
        # tag archive 无 configure（autoreconf 产物不进版本库），先自举
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        self._patch_configure()

        # 真机 conan 2.x 的 tc.environment()/PkgConfigDeps 注入 PKG_CONFIG_PATH
        # 实测不生效（pidgin/xsel 同款坑），改为 build() 内作用域注入；
        # try/finally 保证返回前恢复环境变量。
        _pc_paths = [self.generators_folder]
        for _dep in self.dependencies.values():
            _pc_paths.append(os.path.join(_dep.package_folder, "lib", "pkgconfig"))
        _prior = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = ":".join(_pc_paths)
        self.output.info(f"PKG_CONFIG_PATH (scoped) = {os.environ['PKG_CONFIG_PATH']}")
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            if _prior:
                os.environ["PKG_CONFIG_PATH"] = _prior
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

    def _patch_configure(self):
        """autoreconf 后改写生成的 configure（同 xsel/1.2.1）：
        - E114: config.status 用 umask 077 建临时目录，HMDFS 下不可写 → 改 022；
        - HMFS 下 getcwd 不可达致 configure 报 'working directory cannot be
          determined'：按 autoconf 版本改写 pwd 判定——2.70+ 的
          `ac_pwd=`pwd`` 追加 `2>/dev/null || ac_pwd="$PWD"` 兜底；
          2.69 的 `if (pwd) >/dev/null 2>&1` 追加 `|| test -n "$PWD"`。"""
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8") as f:
            text = f.read()
        if "umask 077" in text:
            text = text.replace("umask 077", "umask 022")
        if ('ac_pwd=`pwd`' in text
                and 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"' not in text):
            text = text.replace('ac_pwd=`pwd`',
                                'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
        text = re.sub(
            r'if \(pwd\) >/dev/null 2>&1( && test -d "`pwd`")?; then :; else',
            r'if (pwd) >/dev/null 2>&1\1 || test -n "$PWD"; then :; else',
            text,
        )
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(text)

    def _prepare_aclocal_path(self):
        """pkg.m4（PKG_CHECK_MODULES 宏）供 aclocal 使用：动态定位 pkg-config
        安装目录，并兜底扫描 hnp 工具链 aclocal 目录（同 xsel/aircrack-ng/afuse）。"""
        dirs = []
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            prefix = os.path.dirname(os.path.dirname(os.path.realpath(pkg_config)))
            cand = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(cand, "pkg.m4")):
                dirs.append(cand)
        for d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            if os.path.isfile(os.path.join(d, "pkg.m4")):
                dirs.append(d)
        if dirs:
            existing = os.environ.get("ACLOCAL_PATH", "")
            os.environ["ACLOCAL_PATH"] = ":".join(
                dirs + ([existing] if existing else []))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # doc/xhk.1 不在 AC_CONFIG_FILES 中（configure.ac 只生成 Makefile 与
        # src/Makefile），上游 make install 不装 man page，此处显式拷贝。
        copy(self, "xhk.1", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # 命令行工具：bin/xhk，无可链接库
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []

    # ── E549 OHOS ELF 自签名 ────────────────────────────────────────────

    def _find_tool(self, name):
        for d in sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        p = os.path.join("/data/service/hnp/bin", name)
        if os.path.isfile(p):
            return p
        return shutil.which(name)

    def _sign_elf(self, binary):
        sign_tool = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not sign_tool or not objcopy:
            # 本地 WSL 交叉编译环境无 device 签名工具：跳过并告警，
            # 由 qemu + OHOS guest rootfs 完成运行验证（真机/CI 上签名）。
            self.output.warning(
                "binary-sign-tool/llvm-objcopy not found; skip OHOS codesign "
                "(local WSL cross-build only)")
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", binary],
                       capture_output=True, timeout=30)
        tmp = binary + ".signed.tmp"
        for _ in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", binary, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True, timeout=60)
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary)
                os.chmod(binary, 0o775)
                return
        if os.path.exists(tmp):
            os.remove(tmp)
        from conan.errors import ConanException
        raise ConanException(f"OHOS codesign failed for {binary} (E549)")

    def _sign_installed_elfs(self):
        for binary in sorted(
                p for p in glob.glob(os.path.join(self.package_folder, "bin", "*"))
                if os.path.isfile(p) and not os.path.islink(p)):
            self._sign_elf(binary)

#!/usr/bin/env python3
"""Conan recipe — spread-sheet-widget 0.10 (autotools).

GNU Spread Sheet Widget — a GTK+ 3 widget that displays and manipulates
tabular data (SswSheet, SswVirtualModel, axis models).

OHOS 适配要点：
  - tarball 自带 configure/Makefile.in，无需 autoreconf；libtool 工程
  - config.guess (2022) 不识别 HarmonyOS → 构建期补 UNAME_SYSTEM 分支
    （E160，gtksourceview3 同法），HarmonyOS → Linux/musl
  - configure 的 config.status 用 `umask 077 && mktemp -d` 建临时目录，
    HMDFS 的 SGID 语义使其不可写 → 构建期剥离 umask（E011）
  - HMDFS 拒绝 execve 任何脚本：configure 用 `/system/bin/sh` 显式解释
    （参数取自 conanbuild.conf 的 configure_args），glib-genmarshal 用
    `sys.executable` 预生成，Makefile 的 MKDIR_P/INSTALL* 改指向 toybox
    的 `/system/bin/mkdir`、`/system/bin/install`
  - config.status 的 depfiles 引导在 HMDFS 上失败 → configure 关闭
    自动依赖跟踪（--disable-dependency-tracking）
  - src/ssw-marshaller.{c,h} 由 glib-genmarshal 从 src/marshall-list 生成
  - 上游 info_TEXINFOS 需要 makeinfo；OHOS 无 makeinfo → make/install 传
    INFO_DEPS=（tarball 自带 .info，本包不安装 texinfo 文档）
  - 依赖 gtk/3.24.43（broadway 后端，ohpcd 已发布 OHOS armv8 binary）
  - package() 对交付的 .so* 重新做 OHOS 签名
"""
import glob
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class SpreadSheetWidgetConan(ConanFile):
    name = "spread-sheet-widget"
    version = "0.10"
    description = ("GNU Spread Sheet Widget — a GTK+ 3 widget to display "
                   "and manipulate tabular data")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/ssw/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gtk/3.24.43 只发布 shared=True OHOS binary；gtk 传递 glib/pango/
        # cairo 等（R36：依赖必须已发布，PF4 依赖闸会逐个探测）
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"spread-sheet-widget requires Linux or OHOS, got {self.settings.os}")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # AutotoolsToolchain 依据 options.shared 自动写 --enable-shared/
        # --disable-static，无需手工追加（追加会产生重复参数）
        tc = AutotoolsToolchain(self)
        # HMDFS 上 config.status 的 depfiles 引导失败（make 片段生成
        # 报错）→ 关闭自动依赖跟踪（仓库内 203 个 autotools 包同法）
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_guess()
        self._patch_config_status_tmpdir()
        env = self._build_environment()
        with env.vars(self).apply():
            # HMDFS 拒绝 execve 脚本（EACCES），configure 不能直接执行 →
            # 用 /system/bin/sh 显式解释（alsa-lib/abiword 同法）；参数
            # 与 AutotoolsToolchain 写入 conanbuild.conf 的完全一致
            configure_args = load_toolchain_args(self.generators_folder).get(
                "configure_args", "")
            configure_cmd = shlex.join(
                [self._configure_shell(),
                 os.path.join(self.source_folder, "configure")])
            if configure_args:
                configure_cmd += " " + configure_args
            self.run(configure_cmd, cwd=self.build_folder, env="conanbuild")
            # glib-genmarshal 不能在 HMDFS 上直接 exec（脚本 shebang 被拒），
            # 因此在 make 之前用 python3 预生成 BUILT_SOURCES，并让生成物
            # 的 mtime 晚于 src/marshall-list，make 不会再调用该工具。
            self._generate_marshaller()
            # E074: HMDFS jobserver fifo → -j1
            # INFO_DEPS=：设备无 makeinfo，跳过 info 目标（tarball 的
            # doc/spread-sheet-widget.info 已随源码提供，不需要重建）
            self.run(f"make -j1 INFO_DEPS= {self._make_install_overrides()}",
                     cwd=self.build_folder, env="conanbuild")

    def package(self):
        env = self._build_environment()
        with env.vars(self).apply():
            # install-sh 是 shell 脚本，HMDFS 拒绝直接 exec，因此把
            # MKDIR_P/INSTALL* 改指向设备自带的 ELF 工具（mkdir/install）
            self.run(
                f'make install DESTDIR="{self.package_folder}" '
                f'INFO_DEPS= -j1 {self._make_install_overrides()}',
                cwd=self.build_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # libtool 归档（.la）记录构建机绝对路径，消费方不需要（gspell 同法）
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["spread-sheet-widget"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "spread-sheet-widget")
        self.cpp_info.set_property("cmake_target_name",
                                   "spread-sheet-widget::spread-sheet-widget")
        self.cpp_info.set_property("pkg_config_name", "spread-sheet-widget")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # ------------------------------------------------------------------
    # OHOS helpers
    # ------------------------------------------------------------------

    def _configure_shell(self):
        """configure 必须由 shell 显式解释（HMDFS 拒绝脚本直接 exec）。"""
        if self.settings.os == "OHOS":
            shell = "/system/bin/sh"
        else:
            shell = shutil.which("sh") or shutil.which("bash")
        if not shell or not os.path.isfile(shell):
            raise ConanInvalidConfiguration(
                f"configure shell is unavailable: {shell}")
        return shell

    def _make_install_overrides(self):
        """MKDIR_P/INSTALL* 在 Makefile 里是裸 install-sh 路径（脚本），
        HMDFS 拒绝 exec → 改用设备上的 ELF 工具：
          - MKDIR_P  → /system/bin/mkdir -p
          - INSTALL* → /system/bin/install（toybox applet）
        libtool 的 install 模式只接受单命令 + 选项形式（`install -c`），
        所以不能把 `/system/bin/sh install-sh -c` 塞进 INSTALL_PROGRAM。
        """
        if self.settings.os != "OHOS":
            return ""
        return (
            'MKDIR_P="/system/bin/mkdir -p" '
            'INSTALL="/system/bin/install -c" '
            'INSTALL_PROGRAM="/system/bin/install -c" '
            'INSTALL_SCRIPT="/system/bin/install -c" '
            'INSTALL_DATA="/system/bin/install -c -m 644"'
        )

    def _patch_config_guess(self):
        """E160: config.guess (2022) 不识别 HarmonyOS。

        运行时改写（与 gtksourceview3/3.24.11 相同），不生成 .patch 文件。
        HarmonyOS 分支在 shell 的 case 中命中后不会再进入 Linux 分支，
        因此 UNAME_SYSTEM=Linux; LIBC=musl 直接决定后续机器判定的结果。
        """
        guess = os.path.join(self.source_folder, "config.guess")
        if not os.path.isfile(guess):
            return
        with open(guess, encoding="utf-8") as handle:
            content = handle.read()
        if "HarmonyOS|HongMeng)" in content:
            return
        old = "case $UNAME_SYSTEM in"
        if old not in content:
            raise RuntimeError("config.guess: UNAME_SYSTEM case not found")
        patched = content.replace(
            old,
            old + "\n    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;",
            1,
        )
        with open(guess, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info("config.guess patched for HarmonyOS (E160)")

    def _patch_config_status_tmpdir(self):
        """E011: config.status 用 `umask 077 && mktemp -d ./confXXXXXX`
        创建 0700 临时目录；HMDFS 的 SGID 语义把它映射成组不可写，
        后续 `./confXXXXXX/subs1.awk: Permission denied`。
        修复：去掉 umask，目录权限继承当前 umask（组可写）。
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        if patched == content:
            self.output.warning(
                "config.status tmpdir template pattern not found in configure")
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info("configure: config.status tmpdir umask patched (E011)")

    def _glib_package(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                return dep
        raise ConanInvalidConfiguration("glib (transitive via gtk) not found in graph")

    def _generate_marshaller(self):
        """Pre-generate src/ssw-marshaller.{c,h} with python3 + glib-genmarshal.

        Makefile.am 的规则直接调用 `glib-genmarshal`（无 configure 变量），
        glib 包里的这个工具是 `#!/usr/bin/env python3` 脚本，HMDFS 拒绝
        直接 exec 脚本。用当前解释器显式执行即可，生成的 .c/.h 写入构建
        目录的 src/ 并以当前时间刷新 mtime，make 判定其新于 marshall-list。
        """
        tool = os.path.join(self._glib_package().package_folder, "bin",
                            "glib-genmarshal")
        if not os.path.isfile(tool):
            raise FileNotFoundError(f"GLib build tool missing: {tool}")
        marshall_list = os.path.join(self.source_folder, "src", "marshall-list")
        if not os.path.isfile(marshall_list):
            raise FileNotFoundError(f"marshall-list missing: {marshall_list}")
        out_dir = os.path.join(self.build_folder, "src")
        os.makedirs(out_dir, exist_ok=True)
        for flag, filename in (("--body", "ssw-marshaller.c"),
                               ("--header", "ssw-marshaller.h")):
            dest = os.path.join(out_dir, filename)
            with open(dest, "w", encoding="utf-8", newline="\n") as out:
                result = subprocess.run(
                    [sys.executable, tool, flag,
                     "--prefix=ssw_cclosure_marshal", marshall_list],
                    stdout=out, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise ConanInvalidConfiguration(
                    f"glib-genmarshal {flag} failed: {result.stderr[-500:]}")
            os.utime(dest, None)
        self.output.info("pre-generated src/ssw-marshaller.{c,h} (glib-genmarshal)")

    def _build_environment(self):
        env = Environment()
        # E002: /tmp 只读 → 构建目录内 tmp
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        for dep in self.dependencies.host.values():
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        # SDK lld 需要 ABI 匹配的 libxml2.so.16（abx/gtksourceview3 同款）
        if self.settings.os == "OHOS":
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            if sdk_llvm_libs:
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
            libcxx = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"))
            if libcxx:
                env.prepend_path("LD_LIBRARY_PATH", libcxx[-1])
        return env

    # ------------------------------------------------------------------
    # OHOS signing
    # ------------------------------------------------------------------

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        # signer 是系统 ELF，依赖系统库；必须剥离 conan 的 LD_LIBRARY_PATH
        clean_env = {
            "PATH": "/data/service/hnp/bin:/system/bin:/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/data/storage/el2/base"),
            "LD_LIBRARY_PATH": "",
            "TMPDIR": os.environ.get("TMPDIR", "/data/storage/el2/base/temp"),
        }
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", binary,
             "-selfSign", "1"],
            env=clean_env, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed for {binary}: "
                f"{result.stdout[-500:]} {result.stderr[-500:]}")

    def _sign_installed_elfs(self):
        patterns = [os.path.join(self.package_folder, "lib", "**", "*.so"),
                    os.path.join(self.package_folder, "lib", "**", "*.so.*")]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            ce = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
            cc = ce.get("c") or ""
            objcopy_candidates = [shutil.which("llvm-objcopy")]
            if cc and os.path.sep in cc:
                objcopy_candidates.insert(
                    0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
            objcopy = next(
                (p for p in objcopy_candidates if p and os.path.isfile(p)), None)
            if objcopy:
                self.run(f"'{objcopy}' --remove-section .codesign "
                         f"'{binary}' 2>/dev/null || true")
            self._sign_elf(binary)

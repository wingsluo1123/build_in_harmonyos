#!/usr/bin/env python3
"""Conan recipe for xdemorse 3.6.7 on HarmonyOS PC (aarch64).

xdemorse 是**业余无线电工具**：X/GTK+ 的 **Morse 解码器** —— 从声卡取音频，经 Goertzel
音调检测得到 mark/space 流，再解码成文本；带瀑布图（整数 FFT）与 Yaesu/Elecraft 的 CAT 支持。
（上游：`qsl.net/5b4az` 的 Morse 工具集 ✓ 本机实测可达。）

## 上游构建形态（实测 configure.ac）

| 事实 | 说明 |
|---|---|
| autotools，且 **`configure` 已随包生成** | 无需 autoreconf，可直接 `./configure && make` ✓ |
| `pkg_modules="gtk+-3.0 >= 3.22.0"` + `PKG_CHECK_MODULES` | 依赖 **GTK3**（本仓 `gtk/3.24.43`） |
| `AC_CHECK_LIB([asound], [snd_pcm_open])` | 依赖 **ALSA**（本仓 `alsa-lib/1.2.16.1`） |
| `AM_GNU_GETTEXT_VERSION([0.19.8])` | i18n 用 gettext：本仓没有该工具 ⇒ 传 `--disable-nls` |
| `AC_CHECK_HEADERS([… perseus-sdr.h …])` | 可选头（无则自动降级）✓ |

## 配方做法

- 用仓内 autotools 约定：`AutotoolsToolchain` + `Autotools`；
- `PkgConfigDeps` 生成依赖的 `.pc`（否则 `configure` 找不到 `gtk+-3.0` ✗）；
- 传 `--disable-nls`（没有 gettext）；
- 打包后对包内 ELF 做 **E318 自签**；
- 消费侧不做 GUI 运行验证（需要显示服务与声卡输入 ✗），只验证产物与签名。
"""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XdemorseConan(ConanFile):
    name = "xdemorse"
    version = "3.6.7"
    description = ("xdemorse — X/GTK+ Morse code decoder (Goertzel tone detection + integer "
                   "FFT waterfall), for amateur radio")
    license = "GPL-3.0-or-later"
    homepage = "https://www.qsl.net/5b4az/pkg/morse/xdemorse/xdemorse.html"
    url = "https://www.qsl.net/5b4az/pkg/morse/xdemorse/"
    topics = ("hamradio", "morse", "gtk3", "alsa", "gui")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("gtk/3.24.43")
        self.requires("alsa-lib/1.2.16.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xdemorse targets Linux/OHOS only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # ⚠️ 上游这份 `configure` 内嵌的 `config.status` 用**相对路径**造临时目录：
        #     tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
        #   随后它要**执行**该目录里的 `subs1.awk` 助手 —— 而构建目录在 hmdfs 上，
        #   **hmdfs 忽略 chmod** ✗ ⇒ 实测报
        #     ./config.status: line 618: ./confX1wMpm/subs1.awk: Permission denied
        #     config.status: error: could not setup config files machinery
        #   （TMPDIR 无关：这条老 autoconf 用的是相对路径。）把该行改为**ext2 绝对路径**
        #   即可让 mktemp 造出的目录能正常 chmod/执行 ✓。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            'mktemp -d "./confXXXXXX"',
            'mktemp -d "/data/storage/el2/base/cache/confXXXXXX"')

    def generate(self):
        # 依赖的 .pc（gtk+-3.0 / alsa）：不生成则 configure 里 PKG_CHECK_MODULES 失败 ✗
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # ⚠️ 两处实测坑（都影响 configure/config.status）：
        # ① 上游随包的 `config.guess` 太老 ⇒ 不显式给三元组时直接
        #    `configure: error: cannot guess build type; you must specify one`；
        #    按仓内 autotools 约定用 **musl** 三元组。
        # ② `config.status` 会在**构建目录**里生成并**执行**一个临时 helper 脚本
        #    （`.confo*/subs1.awk`），而构建目录在 hmdfs 上 —— **hmdfs 忽略 chmod** ✗
        #    ⇒ 实测报 `./confoCVtkC/subs1.awk: Permission denied` +
        #    `config.status: error: could not setup config files machinery`。
        #    解决：把 TMPDIR 指到能行使 chmod 的 **ext2 路径**（Go 系配方已证明该路径
        #    可存放并执行文件 ✓）。
        for candidate in ("/data/storage/el2/base/cache",
                          os.path.expanduser("~/tmp")):
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = os.path.join(candidate, ".probe-xdemorse")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok\n")
                os.chmod(probe, 0o755)
                if os.access(probe, os.X_OK):
                    os.remove(probe)
                    os.environ["TMPDIR"] = candidate
                    self.output.info("TMPDIR for configure/config.status: %s" % candidate)
                    break
                os.remove(probe)
            except OSError:
                continue
        build_triplet = {"armv8": "aarch64", "x86_64": "x86_64"}.get(
            str(self.settings.arch), str(self.settings.arch))
        tc.configure_args.append("--build=%s-unknown-linux-musl" % build_triplet)
        # 上游 AM_GNU_GETTEXT 是硬前置，而本仓无完整 gettext 工具 ⇒ 关掉 NLS
        tc.configure_args.append("--disable-nls")
        # ⚠️ 上游对 ALSA 只做 `AC_CHECK_LIB([asound], …)`（**不取** pkg-config 的 Cflags/Libs ✗）
        # ⇒ 头与库都不会自动进路径，实测两处失败：
        #   ① 编译期 `src/sound.h:18:10: fatal error: 'alsa/asoundlib.h' file not found`
        #   ② 链接期一串 `undefined symbol: snd_mixer_selem_id_set_index / snd_mixer_find_selem`
        #      （连到了 sysroot 里的 stub libasound，而非 conan 制品）
        # 仓内既有写法是 `tc.extra_cflags`（AutotoolsToolchain **没有** `include_paths` ✗，
        # 实测 AttributeError）⇒ 头用 `-I`、库用 `-L` 一并显式给出。
        for dep_name in ("alsa-lib", "gtk"):
            folder = self.dependencies[dep_name].package_folder
            if folder:
                tc.extra_cflags.append("-I%s" % os.path.join(folder, "include"))
                tc.extra_ldflags.append("-L%s" % os.path.join(folder, "lib"))
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()
        for pattern in ("COPYING*", "LICENCE*", "LICENSE*"):
            copy(self, pattern, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # ── OHOS ELF 自签（E318）──────────────────────────────────────────────
    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as handle:
                ident = handle.read(18)
            if len(ident) < 18 or ident[:4] != b"\x7fELF":
                return 0
            return int.from_bytes(ident[16:18], "little")
        except (OSError, IndexError):
            return 0

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        mode = stat.S_IMODE(os.stat(path).st_mode)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path], capture_output=True)
        signed = path + ".signed"
        subprocess.check_call([signer, "sign", "-inFile", path, "-outFile", signed,
                               "-selfSign", "1"])
        shutil.move(signed, path)
        os.chmod(path, mode)

    def _sign_installed_elfs(self):
        targets = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if not os.path.islink(path) and self._elf_type(path) in (2, 3):
                    targets.append(path)
        for path in sorted(targets):
            self._sign_elf(path)
        if targets:
            self.output.info("signed %d ELF(s)" % len(targets))

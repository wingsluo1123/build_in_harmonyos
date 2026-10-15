#!/usr/bin/env python3
"""Conan recipe — picotts 0.1_git20210505 (SVOX Pico TTS).

上游: https://github.com/naggety/picotts （ihuguet/picotts 的 fork，即 Android
AOSP platform/external/svox 的独立化副本），Apache-2.0，纯 C。

产物:
  * lib/libttspico.so.0 — Pico 语音合成引擎（29 个 lib/*.c）
  * bin/pico2wave       — 文本转 WAV 的命令行前端（bin/pico2wave.c，依赖 popt）
  * include/pico*.h     — 公共头文件
  * share/pico/lang/    — 12 个语音资源（6 语种 × _ta.bin/_sg.bin）

构建系统: autotools，但上游**不提供预生成的 configure**——只有
  pico/configure.in + pico/Makefile.am + pico/autogen.sh，
  必须先用 autoconf/automake/libtool 自举。CI worker 只提供 autoconf，
  automake/libtool/aclocal/libtoolize 通过 tool_requires 供给（E178 模式）。

OHOS 要点:
  * 真实上游源树根是 `pico/` 子目录，autotools 工程在该目录内，故所有
    configure/make 均在 <source_folder>/pico 下以 in-source 方式执行。
  * **自举环境必须在命令行内覆盖**（DRAFT-6049 成熟模式）：conanbuild 会在
    self.run 时重新注入 PERL/PERL5LIB，指向 conan perl/5.42.2——该 perl 在
    真机 ABI 不兼容，automake/aclocal/autoconf 一律
    `Perl_my_cxt_init: symbol not found` 而自举失败。故命令前显式
    `PERL=perl PERL5LIB=<纯 Perl 模块目录>`，把 XS 模块交回系统 perl；
    TMPDIR/TMP/TEMP 同时指向构建目录（OHOS /tmp 只读，E002/E011）。
  * 上游 configure 用 AC_CHECK_LIB(popt, poptGetContext) 探测 popt，由
    AutotoolsDeps 注入的 CPPFLAGS/LDFLAGS 满足（popt 走 Conan 依赖链）。
  * GNU config.guess/config.sub 不含 HarmonyOS 分支（E007），在自举后以
    patches/ 中的 OHOS 版副本替换，见 _apply_gnu_config_patches()。
  * 上游 Makefile.am 无 TESTS/check_PROGRAMS，`make check` 目标零注册用例
    （清点证据见 test_package/MANIFEST.yml 的 upstream_zero_evidence）。

R26 判定: /lib、/lib64 下无 libttspico*，本库非系统同名库 → 按 Conan
  默认动态链接（不强制静态），避免污染系统库。
"""
import os
import shlex
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PicottsConan(ConanFile):
    name = "picotts"
    version = "0.1_git20210505"
    description = (
        "Pico TTS: text-to-speech voice synthesizer from SVOX, as shipped in "
        "Android AOSP (libttspico + pico2wave)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/naggety/picotts"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pico2wave 的 popt 参数解析（AC_CHECK_LIB(popt, poptGetContext) + -lpopt）
        self.requires("popt/1.19")

    def build_requirements(self):
        # 上游不发布 configure，必须自举；worker 自带 autoconf 但无 automake/libtool
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps 注入 popt 的 -I/-L/-l；AutotoolsToolchain 注入
        # CC/CFLAGS/CPPFLAGS/LDFLAGS。两者都落进 conanbuild.sh，
        # 由 self.run(..., env="conanbuild") 生效。
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    @property
    def _pico_dir(self):
        """autotools 工程目录（上游源树根的 pico/ 子目录）。"""
        return os.path.join(self.source_folder, "pico")

    def build(self):
        self._bootstrap_autotools()
        self._apply_gnu_config_patches()
        self._run_in_pico("sh ./configure {}".format(self._configure_args()))
        self._run_in_pico("make -j1")
        # 上游 make check（零注册用例，仍必须调用：TEST_QUALITY_SPEC §3.3）
        self._run_in_pico("make -j1 check")

    def package(self):
        self._run_in_pico(
            "make -j1 install DESTDIR={}".format(shlex.quote(self.package_folder))
        )
        # libtool 归档与静态库：默认动态链接，不保留 .la / .a
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "Readme.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["ttspico"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "picotts")
        self.cpp_info.set_property("cmake_target_name", "picotts::picotts")
        self.cmake_target_name = "picotts::picotts"
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ── 内部辅助 ─────────────────────────────────────────────────────

    def _configure_args(self):
        """显式 configure 参数（因 in-source 自举不经过 Autotools 助手）。"""
        args = ["--prefix=/"]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        return " ".join(args)

    def _writable_tmpdir(self):
        """OHOS /tmp 只读（E002）：临时目录落在构建目录内并保证存在。"""
        temporary = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary, exist_ok=True)
        return temporary

    def _perl_module_dirs(self):
        """automake/autoconf 的纯 Perl 模块目录（不带 XS 扩展）。"""
        directories = []
        for ref, tail in (("automake/1.18", "automake-1.18"), ("autoconf/2.72", "autoconf")):
            dependency = self.dependencies.build.get(ref)
            if dependency is None:
                continue
            share_dir = os.path.join(dependency.package_folder, "share", tail)
            if os.path.isdir(share_dir):
                directories.append(share_dir)
        return directories

    def _inline_env_prefix(self):
        """必须内联的环境覆盖。

        conanbuild 会在 self.run 时重新注入 PERL/PERL5LIB（指向真机 ABI 不兼容的
        conan perl/5.42.2），因此用 Conan 的 Environment/``env=`` 覆盖无效——只有
        写在命令行内才可靠（apertium 22.x DRAFT-6049 实证）。
        """
        temporary = self._writable_tmpdir()
        parts = [
            'TMPDIR="{}"'.format(temporary),
            'TMP="{}"'.format(temporary),
            'TEMP="{}"'.format(temporary),
        ]
        modules = self._perl_module_dirs()
        if modules:
            parts.append("PERL=perl")
            parts.append('PERL5LIB="{}"'.format(os.pathsep.join(modules)))
        if self.settings.os == "OHOS":
            parts.append('CONFIG_SHELL="/data/service/hnp/bin/bash"')
            parts.append('SHELL="/data/service/hnp/bin/bash"')
        return " ".join(parts) + " "

    def _run_in_pico(self, command, ignore_errors=False):
        self.output.info("picotts: {}".format(command))
        return self.run(
            self._inline_env_prefix() + command,
            cwd=self._pico_dir,
            env="conanbuild",
            ignore_errors=ignore_errors,
        )

    # 等价上游 autogen.sh 的命令序列（libtoolize → aclocal → automake → autoconf）。
    # 不用 `sh ./autogen.sh` 的原因见 _bootstrap_autotools 的说明。
    _BOOTSTRAP_STEPS = (
        ("libtoolize", "libtoolize --copy"),
        ("aclocal", "aclocal -I lib"),
        ("automake", "automake --add-missing --copy"),
        ("autoconf", "autoconf -I lib"),
    )

    def _bootstrap_autotools(self):
        """上游不发布 configure，在 pico/ 内自举 autotools。

        ⚠️ 不能直接依赖 `sh ./autogen.sh`：它**无 set -e、不检查任何步骤的退出码**，
        而 CI worker 会间歇性 **fork 资源耗尽**（`can't fork - try again` /
        `fork: retry: Resource temporarily unavailable`）。实测（CI 构建 #91548）：

            .aclocal-real: error: .../autom4te failed with exit status: 1
            configure.in:7: error: possibly undefined macro: AM_INIT_AUTOMAKE
            ./configure: line 2152: syntax error near unexpected token `1.9'

        即 aclocal/autoconf 因 fork 失败，autogen.sh 仍打印 "Now run ./configure"
        并留下**宏未展开的半成品 configure**，原实现只判断 configure 是否存在，
        于是放行坏脚本、CI 直接失败。

        这里按上游同样的命令序列分步执行、逐步校验退出码，并在失败时**保留
        autom4te.cache**（上游脚本每次都 `rm -rf autom4te.cache`，使重试永远冷启动、
        fork 压力最大）重试，让瞬时 fork 风暴过去后能收敛。三次仍失败则显式报错，
        绝不把坏 configure 放行给下一步。
        """
        autogen = os.path.join(self._pico_dir, "autogen.sh")
        if not os.path.isfile(autogen):
            raise ConanException(
                "upstream autogen.sh is missing: {}".format(autogen)
            )

        attempts = 3
        for attempt in range(1, attempts + 1):
            if self._configure_is_usable():
                return
            self.output.info(
                "picotts: autotools bootstrap (attempt {}/{})".format(attempt, attempts)
            )
            self._clean_bootstrap_outputs()
            failed_step = None
            for name, command in self._BOOTSTRAP_STEPS:
                result = self._run_in_pico(command, ignore_errors=True)
                if result != 0:
                    failed_step = name
                    self.output.warning(
                        "picotts: bootstrap step '{}' failed with rc={} "
                        "(attempt {}/{})".format(name, result, attempt, attempts)
                    )
                    break
            if failed_step is None and self._configure_is_usable():
                return
            if attempt < attempts:
                # 退避：fork 风暴常为共享 worker 上的短时争用
                time.sleep(15 * attempt)

        raise ConanException(
            "autotools bootstrap failed after {} attempts; {} is unusable "
            "(unexpanded automake macros or unparsable)".format(
                attempts, os.path.join(self._pico_dir, "configure")
            )
        )

    def _clean_bootstrap_outputs(self):
        """清理自举产物（等价 autogen.sh 首段），但**保留 autom4te.cache**。

        保留缓存可让重试时 autom4te 复用已算出的结果，显著减少 fork 次数——
        这正是 fork 受限 worker 上能否收敛的关键。
        """
        for name in (
            "configure",
            "aclocal.m4",
            "Makefile.in",
            "ltmain.sh",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
            "depcomp",
            "compile",
        ):
            target = os.path.join(self._pico_dir, name)
            if os.path.isfile(target):
                os.remove(target)
        for name in (".deps", "m4"):
            target = os.path.join(self._pico_dir, name)
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
        # .deps 之外，libtoolize 需要 m4/ 存在（autogen.sh 亦重新创建）
        os.makedirs(os.path.join(self._pico_dir, "m4"), exist_ok=True)

    def _configure_is_usable(self):
        """configure 存在、不含未展开的 autoconf 宏，且能被 shell 解析。"""
        configure = os.path.join(self._pico_dir, "configure")
        if not os.path.isfile(configure):
            return False
        try:
            with open(configure, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return False
        # aclocal/autoconf 失败时宏原样残留，例如 "AM_INIT_AUTOMAKE(1.9 foreign)"
        for marker in ("\nAM_INIT_AUTOMAKE(", "\nAC_PROG_LIBTOOL("):
            if marker in text:
                return False
        result = self.run(
            "sh ./configure --help >/dev/null 2>&1",
            cwd=self._pico_dir,
            env="conanbuild",
            ignore_errors=True,
        )
        return result == 0

    def _apply_gnu_config_patches(self):
        """E007: 在自举之后给 GNU config.guess / config.sub 补 HarmonyOS 分支。

        上游源树不含这两个脚本：``autogen.sh`` 先 ``rm -f`` 它们，再由
        ``automake --add-missing --copy`` 从 ``automake/1.18`` 复制 GNU 副本
        （config.guess 2024-07-27 / config.sub 2024-05-27）。这两份副本不认识
        ``uname -s = HarmonyOS``，configure 首阶段即中断：

            configure: error: cannot guess build type; you must specify one

        故在**自举之后**（两个文件已存在时）施加差异补丁，把它们补成 OHOS 版，
        得到真实本机三元组 ``aarch64-unknown-linux-ohos``；不用 ``--build/--host``
        绕过（那会让 configure 误判交叉编译并跳过 ``AC_RUN_IFELSE``）。

        两条补丁是相对 ``automake/1.18`` 随附副本的**差异补丁，合计 42 行**：
        早先的"整文件替换"形态会把 GNU 脚本全文（4192 行）塞进 diff，评审工具
        会因变更过大而整体跳过（实测 8 文件/4825 行 → "本次跳过"）。施加后逐条
        校验 OHOS 标记确实落地，未落地即显式失败。
        """
        markers = {
            "config.guess": ("__OHOS__", "HarmonyOS"),
            "config.sub": ("ohos-linux", "linux-ohos"),
        }
        for name in markers:
            if not os.path.isfile(os.path.join(self._pico_dir, name)):
                raise ConanException(
                    "GNU config script missing before E007 patch: {}".format(name)
                )
        apply_conandata_patches(self)
        for name, expected in markers.items():
            path = os.path.join(self._pico_dir, name)
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            absent = [marker for marker in expected if marker not in text]
            if absent:
                raise ConanException(
                    "E007 patch did not land on {}: missing {}".format(name, absent)
                )
            self.output.info("picotts: E007 markers present in {}".format(name))

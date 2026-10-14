#!/usr/bin/env python3
"""Conan recipe — pinentry-mac 1.3.1.1 (autotools, command-line tool).

pinentry = GnuPG 的 PIN/passphrase 输入对话框集合。本配方构建
**pinentry-curses** 与 **pinentry-tty** 两个前端（GUI 系列全部关闭）。

关于名字：上游仓库是 **GPGTools/pinentry**，与 gnupg.org 的 `pinentry` 是
**同一棵源码树**，只是打包 tag 不同（`v1.3.1.1`）。其 `macosx/` 子目录是
macOS 专用 GUI 前端，在非 Darwin 宿主上由 configure.ac 自动关闭
（`configure.ac:127` 只匹配 `*-apple-darwin*`；`configure.ac:825-827`
`pinentry_macosx=no` 为默认值）—— 这是预期行为，不是缺陷。
因此本包名取 `pinentry-mac`，但实际产出的是 **curses + tty 两个命令行前端**。

OHOS 适配要点（与 archives/p/pinentry/1.3.3 同源，差异点见下）：
- **tarball 不含 `configure`**（GitHub tag tarball 只带 configure.ac）→ 必须先
  `autoreconf -fi`。且它**必须在 apply_conandata_patches 之前**跑，因为
  autoreconf 会重新生成 `build-aux/config.sub`，把 HarmonyOS patch 覆盖掉。
- `build-aux/config.guess` / `config.sub` 的 HarmonyOS patch：1.3.1.1 上游不含
  ohos；实测 **1.3.3 的同名 patch 可干净套用到 1.3.1.1**。
- **必须显式指定 `--target=aarch64-linux-ohos`**：OHOS SDK 的 clang 默认
  target 是 `x86_64-unknown-linux-gnu`，会去调宿主的 `/usr/bin/ld` 并报
  `cannot find Scrt1.o / crti.o / -lc`。只给 `--sysroot` 不够，还要
  `-L<sysroot>/usr/lib/aarch64-linux-ohos`（crt 与 libc 都在该子目录）。
- **依赖的 `*-config` 脚本是坏的**：`gpgrt-config --prefix=...` 直接打 usage 退出；
  `libassuan-config --libs` 无视 `--prefix` 返回 `-L/lib -lassuan`。故不能只靠
  PATH，须用 configure 的 `GPG_ERROR_LIBS` / `LIBASSUAN_LIBS` 等变量显式覆盖。
- **`NCURSES_LIBS` 含 `-ltinfo`**：OHOS 的 ncurses/6.6 制品**只有静态
  `libncursesw.a`、没有 libtinfo**，但 configure 探测出 `-lncursesw -ltinfo`
  → 链接报 `unable to find library -ltinfo`。须显式覆盖 `NCURSES_LIBS`。
- `--disable-doc` 关闭 texinfo 构建（否则 `pinentry.texi:80: undefined flag:
  UPDATED` 让 `make` 失败）。
- `/bin/sh` 不可用：config 脚本 shebang 改为 `/data/service/hnp/bin/bash`；并设
  `CONFIG_SHELL`/`SHELL`。
- `TMPDIR` 指向 build 目录；`configure` 内 `umask 077` → `022`（HMDFS 权限问题）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

BASH = "/data/service/hnp/bin/bash"
# automake 制品里 .aclocal-real/.automake-real 的 shebang 指向 HNP perl；
# 这里只用其**目录**做 PATH 兜底（不能把它顶到 PATH 最前，见 _autoreconf_env）
PERL = "/data/service/hnp/bin/perl"
# OHOS SDK clang 的默认 target 是 x86_64-unknown-linux-gnu，必须显式覆盖，
# 否则链接期会调用宿主 /usr/bin/ld 并报 cannot find Scrt1.o/-lc。
OHOS_TARGET = "aarch64-linux-ohos"


class PinentryMacConan(ConanFile):
    name = "pinentry-mac"
    version = "1.3.1.1"
    description = ("GnuPG PIN entry dialog for entering passwords and other "
                   "sensitive data (GPGTools/pinentry tree; curses + tty frontends)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/GPGTools/pinentry"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # patches/ 必须显式导出，否则 apply_conandata_patches 找不到文件
        export_conandata_patches(self)
        # patches/m4/*.m4：上游缺失的 gettext/gnulib 宏，必须随配方一起导出
        # （export_conandata_patches 只导出 conandata 里列出的 patch 文件）。
        # ⚠️ 模式用 "*.m4" 而不是 "m4/*.m4"：后者会把 m4/ 子目录也带上，
        #    落到 dst 里变成 patches/m4/m4/*.m4（实测踩过）。
        copy(self, "*.m4",
             src=os.path.join(self.recipe_folder, "patches", "m4"),
             dst=os.path.join(self.export_sources_folder, "patches", "m4"))

    def requirements(self):
        # 1.3.1.1 仅要求 libgpg-error >= 1.16（configure.ac:247）、
        # libassuan >= 2.1.0（:267）—— 与 1.3.3 一致，版本未抬升
        self.requires("libgpg-error/1.55")
        self.requires("libassuan/3.0.2")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # ★2026-10-10 平台实测修复（CI #80080 / PR !14687）★
        #   本配方 source() 里必须跑 `autoreconf -fi`（上游 tarball 不含 configure），
        #   而 autoreconf 需要 **aclocal**（来自 automake）。
        #   平台 worker 的 HNP 只带 autoconf 2.72，**没有 automake/aclocal**，于是实测报：
        #       Can't exec "aclocal": No such file or directory at
        #         /data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/Autom4te/FileUtils.pm line 299.
        #       autoreconf: error: aclocal failed with exit status: 2
        #   **本机（鸿蒙 PC）装了 brew 的 automake 1.19，所以本地永远复现不出这条失败**。
        #   修法：显式声明由 conan 提供 automake（ohpcd 远端有 automake/1.18 与 1.19，
        #   且都是平台 worker 自己构建的包，其 perl/shebang 路径在 worker 上存在）。
        #   注：pinentry 的 configure.ac 不用 libtool（无 LT_INIT、Makefile.am 无 LTLIBRARIES），
        #   故**不需要** libtoolize。
        self.tool_requires("automake/1.18")
        # ★2026-10-13 追加（CI #89159 仍未通过后实测）★
        #   只补 automake 不够：autoreconf/autoconf 仍来自构建机，实测在装有多版本
        #   autotools 的机器上会报 automake 版本不匹配：
        #       configure.ac:51: error: version mismatch. This is Automake 1.16.5,
        #       but the definition used by this AM_INIT_AUTOMAKE comes from Automake 1.18.
        #   故连 autoconf 一起由 conan 提供（ohpcd 实测有 autoconf/2.72）。
        self.tool_requires("autoconf/2.72")
        # ★2026-10-14 追加（CI #90514 实测）★
        #   `.autom4te-real` 需要 **可执行的 GNU m4** 才能探测版本：
        #       my $m4 = $ENV{"M4"} || '<构建机路径>/bin/m4';
        #       fatal "need GNU m4 1.4 or later: $m4"
        #         if system "$m4 --help </dev/null 2>&1 | grep reload-state";
        #   虽然 autoconf 会传递依赖到 m4，但**显式声明**才能稳定地用它自己的
        #   package_folder 定位可执行文件（见 _ensure_executable_m4），
        #   否则该文件的权限位问题无法在配方侧修复。
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # ⚠️ 顺序至关重要：autotools 引导会重新生成 build-aux/config.sub，
        # 若在其之前打 patch 会被覆盖。tarball 本身不含 configure。
        # ① 补上游缺失的 gettext/gnulib 宏（必须在引导之前）
        self._seed_missing_m4()
        # ② 用 conan 提供的 autoconf+automake 显式引导（见 _autoreconf_env）
        env_vars, note = self._autoreconf_env()
        self.output.info("autotools 引导环境: %s" % note)
        if not env_vars:
            raise ConanException(
                "pinentry-mac: 未能构造 autotools 引导环境（%s）——"
                "build_requirements() 的 autoconf/automake tool_requires 未生效？"
                % note)
        with env_vars.apply():
            self._run_autotools_bootstrap()
        # ★必须在引导之后★ 理由见 _ensure_harmonyos_config 的注释
        self._ensure_harmonyos_config()

    def _seed_missing_m4(self):
        """把上游缺失的 gettext/gnulib 宏补进源码树的 m4/。

        ★CI #89159 之后实测发现★ `aclocal` 能跑通后，`autoconf` 阶段报：
            configure: error: possibly undefined macro: AC_LIB_PREPARE_PREFIX
            configure: error: possibly undefined macro: AC_LIB_RPATH
            configure: error: possibly undefined macro: AC_LIB_LINKFLAGS_BODY
            configure: error: possibly undefined macro: AC_LIB_APPENDTOVAR
        根因（已逐条实测）：上游 `m4/iconv.m4` 里 `AM_ICONV_LINKFLAGS_BODY` 只
        **AC_REQUIRE** 这些宏、**从不定义**它们；定义方是 GNU gettext/gnulib 的
        `lib-prefix.m4` / `lib-link.m4` / `lib-ld.m4`（及其依赖
        `host-cpu-c-abi.m4`）。上游 tarball **没有** `m4/lib-*.m4`
        （实测 `ls m4/` 只有 curses/glib/gpg-error/gtk/iconv/libassuan/pkg/qt*）。
        本机（WSL/鸿蒙 PC）能过，是因为宿主 `/usr/share/aclocal/` 里正好装了 gettext
        的这几个 .m4 —— 典型的"**宿主有、worker 没有**"假绿；平台 worker 的 HNP
        没有 gettext，必然复现该失败。

        修法：把 4 个 .m4 作为配方资产随包提供（`patches/m4/`），在引导之前拷进
        源码树 `m4/`。`Makefile.am:27` 有 `ACLOCAL_AMFLAGS = -I m4`，显式跑
        `aclocal -I m4` 即可收集到。这些文件来自 GNU gettext 0.21，是上游本就该有的
        宏定义，不修改任何 pinentry 源码语义。
        """
        candidates = [
            os.path.join(self.recipe_folder, "patches", "m4"),
            os.path.join(self.export_sources_folder, "patches", "m4"),
        ]
        src = next((c for c in candidates
                    if os.path.isdir(c)
                    and any(n.endswith(".m4") for n in os.listdir(c))), None)
        if src is None:
            raise ConanException(
                "pinentry-mac: 未找到 patches/m4 下的 .m4 资产（配方资产缺失；"
                "export_sources() 应已导出 *.m4）")
        dst = os.path.join(self.source_folder, "m4")
        os.makedirs(dst, exist_ok=True)
        names = sorted(n for n in os.listdir(src) if n.endswith(".m4"))
        for name in names:
            copy(self, name, src=src, dst=dst)
        self.output.info("已补入上游缺失的 m4 宏(%s): %s" % (src, ", ".join(names)))

    def _tool_bin(self, name):
        """返回某个 tool_requires 包的 bin 目录（拿不到返回 None）。

        `tool_requires(...)` 只把工具放进**依赖图**；`source()` 阶段 Conan 不应用
        tool_requires 的环境（那套由 generators 写进 conanbuild.sh，仅
        build()/generate() 生效）。故这里显式取 `self.dependencies.build[...]` 的
        package_folder 自己拼 PATH —— 实测该访问在 source() 阶段可用。
        """
        try:
            dep = self.dependencies.build[name]
        except Exception:
            return None
        bindir = os.path.join(dep.package_folder, "bin")
        return bindir if os.path.isdir(bindir) else None

    def _ensure_executable_m4(self):
        """返回一个**可执行**的 GNU m4 绝对路径（拿不到返回 None）。

        ★CI #90514 实测★ conan 的 m4/1.4.19 制品里 `bin/m4` 权限是 **750**，
        而 worker 以 `USER=100` 运行、非包属主 ⇒ other 位为 `---` ⇒ 不可执行。
        `.autom4te-real` 用 `system "$m4 --help | grep reload-state"` 探测版本，
        执行失败就误判成"不是 GNU m4"并 fatal。

        策略（按优先级）：
          1. tool_requires 的 m4 包（`self.dependencies.build["m4"]`）；
          2. HNP 自带的 `/data/service/hnp/bin/m4`（与 PERL 同策略）；
          3. PATH 上的 `m4`。
        对候选项：若能读且不是可执行位，则尝试 `os.chmod` 补上 other+group 执行位
        （制品目录在 worker 上属当前用户时可写；不可写则保留原状并继续尝试下一项）。
        """
        candidates = []
        m4_bin = self._tool_bin("m4")
        if m4_bin:
            candidates.append(os.path.join(m4_bin, "m4"))
        candidates.append("/data/service/hnp/bin/m4")
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if d:
                candidates.append(os.path.join(d, "m4"))

        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                continue
            if not os.access(cand, os.X_OK):
                # 补执行位（含 other，因为 worker 非属主）
                try:
                    cur = os.stat(cand).st_mode
                    os.chmod(cand, cur | 0o111)
                    self.output.info("m4: 已补执行位 %s（原权限 %o）"
                                     % (cand, cur & 0o777))
                except OSError as exc:
                    self.output.warning("m4: %s 不可执行且 chmod 失败（%s），跳过"
                                        % (cand, exc))
                    continue
            if os.access(cand, os.X_OK):
                return cand
        return None

    def _write_autom4te_wrapper(self, ac_bin, ac_share, perl_bin):
        """生成一个极简的 autom4te 包装脚本，把 `--prepend-include` 固化进去。

        ★CI #90577 实测★ `AUTOM4TE` 的值会被两个脚本以**不同方式**消费：
          · `.autoconf-real` L182：`split /[ \\t\\n]+/, $autom4te`（支持多词）
          · `.autoheader-real` L168：`my $autoconf = "'$autom4te' --language=...";`
            —— 整个值被**单引号**裹成一个 shell 词（多词 ⇒ 被当成一个文件名 ⇒ 127）
        故一个值无法同时满足两者。改为**单文件路径**，把选项固化进包装脚本。

        脚本内容（等价于原 conan `bin/autom4te` 第 42 行，但零 fork）：
            <BASH> 下 exec <perl> "<abs>/.autom4te-real" --prepend-include <share> "$@"

        写到 `<ac_bin>/pm-autom4te`（**新文件名**，不覆盖 conan 自带文件）。
        失败返回 None（调用方会告警并回退）。
        """
        real = os.path.join(ac_bin, ".autom4te-real")
        if not os.path.isfile(real):
            return None
        wrapper = os.path.join(ac_bin, "pm-autom4te")
        body = ('#!%s\n'
                '# 由 pinentry-mac 配方生成：固化 --prepend-include，避免依赖\n'
                '# conan 包装脚本里 `here=$(cd ... && pwd)` 的 fork 行为。\n'
                'exec "%s" "%s" --prepend-include "%s" "$@"\n'
                % (BASH, perl_bin, real, ac_share))
        try:
            with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
            os.chmod(wrapper, 0o755)
        except OSError as exc:
            self.output.warning("autom4te 包装脚本生成失败（%s）" % exc)
            return None
        self.output.info("已生成 autom4te 包装脚本：%s（固化 --prepend-include=%s）"
                         % (wrapper, ac_share))
        return wrapper

    def _fix_tool_wrappers(self, bindir, names):
        """修工具包包装脚本 shebang，返回实际修过的文件名列表。

        ohpcd 的 automake/autoconf 制品里 `bin/*` 是 conan 生成的**包装脚本**，
        shebang 为 `#!/bin/sh`（OHOS 上不存在 /bin/sh）⇒ 即便在 PATH 上也会 ENOENT。
        它们本身是 sh 脚本（只做 dirname + exec），换 bash 完全兼容。
        """
        fixed = []
        for name in names:
            path = os.path.join(bindir, name)
            if os.path.isfile(path):
                # 复用 head 既有的 _fix_shebang(self, path)（内部固定用 BASH）；
                # 不新增参数，保持与已有调用点一致。
                self._fix_shebang(path)
                fixed.append(name)
        return fixed

    def _autoreconf_env(self):
        """为 `source()` 的 autotools 引导构造环境。返回 (env_vars|None, 说明)。

        逐层排查出**六个独立**缺陷，缺一不可（每一条都经平台 CI 或本地实测确认）：

          ① `source()` 拿不到 tool_requires 的 PATH ⇒ `aclocal` 根本不在 PATH 上
             （CI #89159：`Can't exec "aclocal"`）。
          ② ohpcd 的 automake 制品里 `bin/aclocal`、`bin/automake` 是 conan 包装脚本，
             shebang 为 `#!/bin/sh`（OHOS 无 /bin/sh）⇒ 在 PATH 上也 ENOENT。
          ③ 那些包装脚本只传 `--automake-acdir`/`--system-acdir`、**不传 `--libdir`**，
             而实体 `.aclocal-real` 第 26 行写死 `unshift (@INC,
             '//share/automake-1.18')`（`@libdir@` 占位符没被替换）⇒ perl 找不到
             `Automake/Config.pm`。正解：`PERL5LIB=<pkg>/share/automake-1.18`
             （`--libdir` 不是 aclocal 的合法选项，实测补它无效）。
          ④ 只补 automake 时 `autoconf`/`autoreconf` 仍是构建机的 ⇒ 实测报
             `version mismatch. This is Automake 1.16.5, but ... comes from 1.18`。
             故同时声明 `tool_requires("autoconf/2.72")`。
          ⑤ ★PATH 顺序★ `prepend_path` 后调用的排到**更前面**；若把 HNP perl 目录
             放在最后 prepend，`/data/service/hnp/bin` 会被顶到 PATH 首位，而该目录
             自带 **automake 1.16.5 / autoconf 2.71**，会遮蔽 conan 的工具 —— 这正是
             "本地手工跑四步全绿、worker/带 HNP 的机器却报 version mismatch" 的原因。
             故必须**先** prepend 兜底目录、**最后** prepend 两个工具包。
          ⑥ ★包装脚本不止 aclocal 一个★ 把 aclocal/automake 改成直调 `.*-real` 之后，
             失败点**后移**到了 autoconf 侧（CI #90380 实测）——详见下方 ⑥ 号实现注释。
        """
        am_bin = self._tool_bin("automake")
        ac_bin = self._tool_bin("autoconf")
        if not am_bin:
            return None, "未取到 automake 工具包的 bin 目录（tool_requires 未生效？）"
        if not ac_bin:
            return None, "未取到 autoconf 工具包的 bin 目录（tool_requires 未生效？）"

        fixed = self._fix_tool_wrappers(
            am_bin, ("aclocal", "aclocal-1.18", "automake", "automake-1.18"))
        fixed += self._fix_tool_wrappers(
            ac_bin, ("autoconf", "autoheader", "autom4te", "ifnames", "autoscan"))

        am_libdir = os.path.join(os.path.dirname(am_bin), "share", "automake-1.18")
        config_pm = os.path.join(am_libdir, "Automake", "Config.pm")

        env = Environment()
        # ⑥ ★2026-10-14 新增（CI #90380 实测）★ 消掉**其余**包装脚本的 fork 依赖。
        #   上一轮只把 aclocal/automake 改成直调 .*-real，但**漏了 autoconf 侧**：
        #   `.autoconf-real` 第 47 行是
        #       my $autom4te = $ENV{'AUTOM4TE'} || '//bin/autom4te';
        #   即它**通过 AUTOM4TE 环境变量**去调 `bin/autom4te` —— 而那仍是一个
        #   `here=$(CDPATH= cd "$(dirname "$0")" && pwd)` 的 conan 包装脚本。
        #   worker fork 吃紧时 `here` 变空，实测报（CI #90380，3792s 后超时）：
        #       autom4te: fork: retry: Resource temporarily unavailable   ×4
        #       Can't open perl script "/.autom4te-real": No such file or directory
        #       .aclocal-real: error: autom4te failed with exit status: 2
        #   —— 与上一轮 `/.aclocal-real` 是**同一个 bug 的另一个实例**。
        #   修法：把包装脚本本来会导出/推导的东西**全部在 Python 侧静态算好**，
        #   并让 AUTOCONF/AUTOHEADER/AUTOM4TE/AUTORECONF/AUTOSCAN/AUTOUPDATE/IFNAMES
        #   全部指向 `.*-real` 实体。这样整条引导链**不再 exec 任何包装脚本**，
        #   对 fork 不再有任何依赖（`.*-real` 是普通 perl 脚本，自身不 fork）。
        ac_root = os.path.dirname(ac_bin)
        ac_share = os.path.join(ac_root, "share", "autoconf")
        if os.path.isdir(ac_share):
            # ⑩ ★2026-10-14 修正（CI #90547 实测，这是 ⑦ 号修复自身引入的回归）★
            #   `.autoconf-real` 第 182 行是
            #       my @autom4te_command = split /[ \t\n]+/, $autom4te;
            #   —— 它**只按空白切分，不做任何 shell 去引号**！故这些变量的值里
            #   **绝对不能带引号**：带引号时 argv[0] 会变成含引号字符的字符串，
            #   exec 便去找名为 `"perl"`（含引号）的程序，实测报
            #       Can't exec ""/data/service/hnp/bin/perl"": No such file or directory
            #       at .../.autoconf-real line 198.
            #   修法：值一律写成**不带引号**的裸词（这些路径都不含空格/特殊字符）。
            #   这正是 ⑦ 号那轮我写 `'"%s" "%s"'` 引号包裹的疏忽 —— 现已改正。
            perl_bin = PERL if os.path.isfile(PERL) else "perl"
            env.define("PERL", perl_bin)
            # 等价于 autoconf 包装脚本导出的变量（见 bin/autom4te 原文）
            env.define("autom4te_perllibdir", ac_share)
            env.define("AC_MACRODIR", ac_share)
            env.define("trailer_m4", os.path.join(ac_share, "autoconf",
                                                  "trailer.m4"))
            env.define("autom4te_buildauxdir", os.path.join(ac_share, "build-aux"))
            n_bound = 0
            # ⑪ ★2026-10-14 修正（CI #90577 实测）★ AUTOM4TE **只能是单个可执行文件
            #   路径**，不能再带 `--prepend-include` 参数 —— 因为两个消费者对它的
            #   处理方式**不同**：
            #     · `.autoconf-real` L182：`split /[ \t\n]+/, $autom4te` —— 支持多词；
            #     · `.autoheader-real` L168：`my $autoconf = "'$autom4te' --language=...";`
            #       —— 把整个值用**单引号**裹成一个 shell 词！
            #   故多词值在 autoheader 侧会被当成"一个文件名"，实测报
            #       sh: /data/service/hnp/bin/perl .../.autom4te-real --prepend-include
            #           /storage/.../share/autoconf: inaccessible or not found
            #       .autoheader-real: error: '/data/service/hnp/bin/perl failed with exit status: 127
            #   一个值无法同时满足两个消费者 ⇒ 改回**单路径**，并把这个选项
            #   固化进一个我们自己生成的小包装脚本（内容极简、零 fork）：
            #       #!<bash>
            #       exec <perl> "<abs>/.autom4te-real" --prepend-include "<share>" "$@"
            #   这就是原 conan 包装脚本 `bin/autom4te` 第 42 行所做的事，但
            #   **不依赖它的 here=$(cd ... && pwd)**（fork 依赖已被我们消除）。
            #   这样 AUTOM4TE 是单文件、可直接 exec，两个消费者都能正确工作。
            autom4te_wrapper = self._write_autom4te_wrapper(ac_bin, ac_share,
                                                            perl_bin)
            for var, real in (
                    ("AUTOCONF", ".autoconf-real"),
                    ("AUTOHEADER", ".autoheader-real"),
                    ("AUTORECONF", ".autoreconf-real"),
                    ("AUTOSCAN", ".autoscan-real"),
                    ("AUTOUPDATE", ".autoupdate-real"),
                    ("IFNAMES", ".ifnames-real")):
                path = os.path.join(ac_bin, real)
                if not os.path.isfile(path):
                    continue
                # ⑩ 值**不带引号**（`.autoconf-real` 用 split 切分且不去引号，
                #   带引号会让 argv[0] 失真）。
                env.define(var, '%s %s' % (perl_bin, path))
                n_bound += 1
            # AUTOM4TE 特例：单文件路径（见 ⑪）
            if autom4te_wrapper:
                env.define("AUTOM4TE", autom4te_wrapper)
                n_bound += 1
            # autoconf 的 perl 模块（Autom4te::*）在 share/autoconf 下
            env.prepend_path("PERL5LIB", ac_share)
            # ⑧ ★2026-10-14 新增（CI #90514 实测）★ 必须给出可执行的 M4。
            #   ⑦ 号修复生效后（日志实见「7 个变量直指 .*-real 并用显式解释器
            #   /data/service/hnp/bin/perl」），失败点**再次后移**到：
            #       .autom4te-real: error: need GNU m4 1.4 or later:
            #           /storage/.../p/m42d92622f4ed01/p/bin/m4
            #   根因：`.autom4te-real` 第 96-98 行用
            #       my $m4 = $ENV{"M4"} || '<构建机路径>/bin/m4';
            #       fatal "need GNU m4 1.4 or later: $m4"
            #         if system "$m4 --help </dev/null 2>&1 | grep reload-state >/dev/null";
            #   **经 shell 执行 m4** 来探测版本。而 conan 的 m4 制品权限是 **750**，
            #   worker 以 `USER=100` 运行、非包属主 ⇒ other 位是 `---` ⇒ 无法执行
            #   ⇒ system 失败 ⇒ 误报"不是 GNU m4"。包装脚本原本会 `: "${M4:=m4}"`
            #   把 M4 导出去（我们在 ⑦ 把它旁路掉了，故这里必须自己补上）。
            #   修法：定位 m4 可执行文件（优先 tool_requires 的 m4 包，其次 PATH），
            #   若它缺少 other 执行位则 `os.chmod` 补上（包目录可写时），
            #   然后 `env.define("M4", ...)`。
            m4_bin = self._ensure_executable_m4()
            if m4_bin:
                env.define("M4", m4_bin)
            else:
                self.output.warning(
                    "未找到可用的 GNU m4；autom4te 可能报 'need GNU m4 1.4 or "
                    "later'（M4 未设置）")
            self.output.info("autoconf 包装脚本已旁路：%d 个变量直指 .*-real 并用显式"
                             "解释器 %s（零 fork、不依赖 shebang），M4=%s，share=%s"
                             % (n_bound, perl_bin, m4_bin or "(未找到)", ac_share))
        else:
            self.output.warning(
                "autoconf: 未找到 %s，AUTOM4TE 仍会走包装脚本（fork 压力下可能 "
                "报 '/.autom4te-real: No such file or directory'）" % ac_share)
        # ⑤ 顺序：先兜底、后工具包（后 prepend 的排更前）
        perl_dir = os.path.dirname(PERL)
        if os.path.isdir(perl_dir):
            env.prepend_path("PATH", perl_dir)
        env.prepend_path("PATH", am_bin)
        env.prepend_path("PATH", ac_bin)
        # ③ perl @INC
        if os.path.isfile(config_pm):
            env.prepend_path("PERL5LIB", am_libdir)
        else:
            self.output.warning("automake: 未找到 %s，PERL5LIB 未设置" % config_pm)
        env.define("CONFIG_SHELL", BASH)
        env.define("SHELL", BASH)
        env_vars = env.vars(self)
        self._assert_tool_wins(env_vars, am_bin, ac_bin)
        return env_vars, (
            "automake_bin=%s autoconf_bin=%s 修正 shebang=%d 个[%s]"
            % (am_bin, ac_bin, len(fixed), ",".join(fixed) or "无"))

    def _assert_tool_wins(self, env_vars, am_bin, ac_bin):
        """fail-closed 自检：确认 automake/autoconf 等解析到 conan 的工具包。

        被旧版本遮蔽时的症状是难懂的 `version mismatch`，故在此显式拦下。
        """
        wanted = {"automake": am_bin, "aclocal": am_bin,
                  "autoconf": ac_bin, "autoheader": ac_bin}
        with env_vars.apply():
            for tool, expect_bin in wanted.items():
                hit = None
                for d in os.environ.get("PATH", "").split(os.pathsep):
                    cand = os.path.join(d, tool)
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        hit = cand
                        break
                if hit is None:
                    raise ConanException(
                        "pinentry-mac: PATH 上找不到 %s（autotools 引导不可用）" % tool)
                if os.path.dirname(hit) != expect_bin:
                    raise ConanException(
                        "pinentry-mac: %s 被非预期路径遮蔽：解析到 %s，期望 %s 下的版本。"
                        "构建机上存在同名旧版本工具，会让 autotools 引导报 version "
                        "mismatch。" % (tool, hit, expect_bin))
        self.output.info("autotools 工具自检通过：automake/aclocal/autoconf/autoheader "
                         "均解析到 conan 工具包")

    def _run_autotools_bootstrap(self):
        """显式跑 autotools 引导四步，**替代 `autoreconf -fi`**。

        ★为什么不用 autoreconf★（实测）
        `autoreconf` 会自行探测 `automake`：按 aclocal.m4 记录的主版本去调
        `automake-<ver>`，探测不到就回落到构建机上的 `automake`。即使把 conan 的
        automake 1.18 前置进 PATH，它仍可能选中宿主 `/usr/bin/automake` 1.16.5，报
        `version mismatch`。而把同样的四步**显式**跑一遍实测全部 rc=0、无版本不匹配，
        且行为确定、不依赖 autoreconf 的内部探测。
        顺序与 autoreconf 一致：aclocal → autoconf → autoheader → automake。

        ★为什么优先调 `.*-real` 而不是 `bin/aclocal` 包装脚本★（CI #89943 实测）
        conan 生成的包装脚本用 `here=$(cd "$(dirname "$0")" && pwd)` 推导自身位置 ——
        这**需要 fork 一个子 shell**。worker 在并发压力下会报
            aclocal: fork: retry: Resource temporarily unavailable
            aclocal: line 6: /.aclocal-real: No such file or directory
        即 fork 失败 ⇒ `here` 为空 ⇒ `exec "/.aclocal-real"` ENOENT ⇒ 引导中断。
        改法：在 Python 侧一次性算好绝对路径（os.path，零 fork），直接调用
        `<pkg>/bin/.aclocal-real` / `.automake-real`，并把包装脚本本来要传的参数
        （`--automake-acdir` / `--system-acdir` / `--libdir`）显式传进去。
        `.autoconf` 等是普通 perl 脚本、无此问题，仍按名字调用。
        实测：直接调 .real 时四步全部 rc=0、四个产物齐全。
        """
        am_bin = self._tool_bin("automake")
        ac_bin = self._tool_bin("autoconf")
        am_root = os.path.dirname(am_bin)
        # 显式等价于包装脚本里 pfx 的推导，但不 fork
        am_automake_acdir = os.path.join(am_root, "share", "aclocal-1.18")
        am_system_acdir = os.path.join(am_root, "share", "aclocal")
        am_libdir = os.path.join(am_root, "share", "automake-1.18")

        aclocal_real = os.path.join(am_bin, ".aclocal-real")
        automake_real = os.path.join(am_bin, ".automake-real")

        # ⑦ ★2026-10-14 新增（CI #90490 实测）★ 不要依赖 `.*-real` 自身的 shebang。
        #   上一轮的 ⑥ 号修复已成功把包装脚本旁路（#90490 日志实见
        #   「autoconf 包装脚本已旁路：AUTOM4TE 等 7 个变量直指 .*-real（零 fork）」），
        #   fork 报错也确实消失了 —— 但暴露出**下一层**缺陷，报错变成：
        #       sh: .../p/bin/.autom4te-real: No such file or directory
        #       .aclocal-real: error: .../.autom4te-real failed with exit status: 126
        #   注意路径是**正确的绝对路径**（不再是 `/.autom4te-real`），却仍 ENOENT/126。
        #   实测（stat/od）三个独立缺陷：
        #     ① autoconf 侧 7 个 `.*-real` 的 shebang 是 `#! /storage/.../perl.../bin/perl`
        #        —— `#!` 后**多一个空格**，Linux 会把解释器解析成 " "（不存在）⇒ 执行失败；
        #     ② 该 shebang 指向 conan **perl 包的构建机路径**，worker 上不保证存在
        #        （automake 侧写的是 `#!/data/service/hnp/bin/perl`，worker 上确定有）；
        #     ③ autoconf 侧 `.*-real` 权限位是 **750**，而 worker 以 `USER=100` 运行、
        #        并非包属主 ⇒ 无执行权限（automake 侧是 770，故 `.aclocal-real` 能跑）。
        #   正解：**用显式解释器执行**，同时绕开 shebang 与执行位
        #       <perl> <abs>/.autom4te-real ...
        #   perl 用 PERL（/data/service/hnp/bin/perl，HNP 自带，worker 上确定存在），
        #   这也正是 `.aclocal-real` 自身 shebang 用的解释器。
        perl_bin = PERL if os.path.isfile(PERL) else "perl"

        def _real_cmd(real, args):
            """用显式 perl 解释器执行 `.*-real`（不依赖 shebang / 执行位）。

            real 不存在时返回 None，由调用方回退到包装脚本。
            """
            if not os.path.isfile(real):
                return None
            return '"%s" "%s" %s' % (perl_bin, real, args)

        if os.path.isfile(aclocal_real):
            aclocal_cmd = _real_cmd(
                aclocal_real,
                '--automake-acdir="%s" --system-acdir="%s" -I m4'
                % (am_automake_acdir, am_system_acdir))
        else:
            # 兜底：老制品里没有 .*-real 时仍用包装脚本
            self.output.warning(
                "automake: 未找到 %s，回退到包装脚本 aclocal" % aclocal_real)
            aclocal_cmd = "aclocal -I m4"
        if os.path.isfile(automake_real):
            automake_cmd = _real_cmd(
                automake_real, '--libdir="%s" --add-missing --copy' % am_libdir)
        else:
            self.output.warning(
                "automake: 未找到 %s，回退到包装脚本 automake" % automake_real)
            automake_cmd = "automake --add-missing --copy"

        # ⑥ 与 aclocal/automake 同理：autoconf/autoheader 也优先直调 .*-real 实体，
        #   彻底不在引导链里 exec 任何包装脚本（包装脚本 = fork 依赖）。见
        #   _autoreconf_env 的 ⑥ 号注释（CI #90380 的 /.autom4te-real 根因）。
        def _prefer_real(name):
            real = os.path.join(ac_bin, "." + name + "-real")
            cmd = _real_cmd(real, "")
            if cmd is not None:
                return cmd
            self.output.warning(
                "autoconf: 未找到 %s，回退到包装脚本 %s" % (real, name))
            return os.path.join(ac_bin, name)

        steps = [
            # -I m4：上游 Makefile.am:27 声明 ACLOCAL_AMFLAGS = -I m4；
            # autoreconf 会自动带上，显式跑时须自己给。
            (aclocal_cmd, "aclocal 生成 aclocal.m4"),
            (_prefer_real("autoconf"), "autoconf 生成 configure"),
            (_prefer_real("autoheader"), "autoheader 生成 config.h.in"),
            (automake_cmd, "automake 生成 Makefile.in"),
        ]
        self.output.info("autotools 引导使用解释器：%s（显式指定，不依赖 .*-real 的 "
                         "shebang/执行位）" % perl_bin)
        for cmd, why in steps:
            self.output.info("autotools 引导: %s（%s）" % (cmd, why))
            self.run(cmd, cwd=self.source_folder)
        for f in ("aclocal.m4", "configure", "config.h.in"):
            if not os.path.isfile(os.path.join(self.source_folder, f)):
                raise ConanException(
                    "pinentry-mac: autotools 引导后缺少 %s（上游结构可能变了）" % f)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-pinentry-curses",
            "--enable-pinentry-tty",
            # 1.3.1.1 多出 gtk2/gnome3 开关（1.3.3 已移除），一并关闭
            "--disable-pinentry-gtk2",
            "--disable-pinentry-gnome3",
            "--disable-pinentry-efl",
            "--disable-pinentry-qt",
            "--disable-pinentry-qt4",
            "--disable-pinentry-qt5",
            "--disable-pinentry-tqt",
            # 关闭 texinfo 文档：否则 pinentry.texi:80 undefined flag UPDATED
            # 让 make 在 doc/ 目标上失败（与二进制无关）
            "--disable-doc",
            "--disable-inside-emacs",
            "--disable-fallback-curses",
        ])
        tc.generate()

    def _fix_shebang(self, path):
        """OHOS 上 /bin/sh 不可用 → 把 config 脚本 shebang 改为可用的 bash。"""
        if not os.path.isfile(path):
            return
        with open(path, "r") as f:
            content = f.read()
        if content.startswith("#!/bin/sh"):
            with open(path, "w") as f:
                f.write(f"#!{BASH}\n")
                rest = content[len("#!/bin/sh"):]
                if rest.startswith("\n"):
                    rest = rest[1:]
                f.write(rest)

    def _dep(self, name):
        return self.dependencies[name]

    def _build_environment(self):
        """构造构建环境：依赖 bin/PATH、config 脚本路径、TMPDIR、SHELL。"""
        gpg_error = self._dep("libgpg-error")
        libassuan = self._dep("libassuan")
        ncurses = self._dep("ncurses")

        gpg_error_bin = os.path.join(gpg_error.package_folder, "bin")
        libassuan_bin = os.path.join(libassuan.package_folder, "bin")

        # 修正 config 脚本 shebang（OHOS /bin/sh 不可用）
        for script in ["gpgrt-config", "gpg-error-config"]:
            self._fix_shebang(os.path.join(gpg_error_bin, script))
        self._fix_shebang(os.path.join(libassuan_bin, "libassuan-config"))

        env = AutotoolsToolchain(self).environment()
        env.compose_env(AutotoolsDeps(self).vars())

        local_env = Environment()
        local_env.prepend_path("PATH", gpg_error_bin)
        local_env.prepend_path("PATH", libassuan_bin)
        local_env.prepend_path("LD_LIBRARY_PATH",
                               os.path.join(gpg_error.package_folder, "lib"))
        local_env.prepend_path("LD_LIBRARY_PATH",
                               os.path.join(libassuan.package_folder, "lib"))
        local_env.prepend_path("LD_LIBRARY_PATH",
                               os.path.join(ncurses.package_folder, "lib"))

        # libgpg-error 1.56+ 只剩 gpgrt-config（无 gpg-error-config）→ 显式给出
        gpgrt_config = os.path.join(gpg_error_bin, "gpgrt-config")
        if os.path.isfile(gpgrt_config):
            local_env.define("GPGRT_CONFIG", gpgrt_config)
        libassuan_config = os.path.join(libassuan_bin, "libassuan-config")
        if os.path.isfile(libassuan_config):
            local_env.define("LIBASSUAN_CONFIG", libassuan_config)

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        local_env.define("TMPDIR", tmpdir)
        local_env.define("CONFIG_SHELL", BASH)
        local_env.define("SHELL", BASH)

        env.compose_env(local_env)
        return env.vars(self)

    def _find_sysroot(self):
        """定位 OHOS sysroot —— 沿用仓库标准发现链（见 godot/4.7.2-stable:112）。

        1. `tools.build:sysroot` conf（profile 提供时）
        2. 从编译器目录向上最多 5 级找 `sysroot/`（OHOS SDK 目录布局）
        """
        configured = self.conf.get("tools.build:sysroot", default="",
                                   check_type=str).strip('"')
        if configured and os.path.isdir(configured):
            return configured
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler = compilers.get("c") or compilers.get("cpp")
        if compiler:
            directory = os.path.dirname(os.path.abspath(compiler))
            for _ in range(5):
                candidate = os.path.join(directory, "sysroot")
                if os.path.isdir(candidate):
                    return candidate
                parent = os.path.dirname(directory)
                if parent == directory:
                    break
                directory = parent
        return None

    def _dep_flags(self):
        """返回 (cflags, ldflags)：显式 -I/-L + OHOS sysroot/target。

        依赖包自带的 config 脚本**不可信**（`libassuan-config --libs` 无视
        --prefix 返回 `-L/lib -lassuan`），故一律用包目录实测拼出路径。
        """
        gpg_error = self._dep("libgpg-error").package_folder
        libassuan = self._dep("libassuan").package_folder
        ncurses = self._dep("ncurses").package_folder

        cflags = [f"-I{d}/include" for d in (gpg_error, libassuan, ncurses)]
        ldflags = [f"-L{d}/lib" for d in (gpg_error, libassuan, ncurses)]

        sysroot = self._find_sysroot()
        if sysroot:
            # ⚠️ clang 默认 target 不是 OHOS，必须显式指定，否则用宿主 ld 链接、
            # 找不到目标平台的 crt/libc（实测报 cannot find Scrt1.o / crti.o / -lc）
            cflags.insert(0, f"--target={OHOS_TARGET}")
            ldflags.insert(0, f"--target={OHOS_TARGET}")
            cflags.insert(1, f"--sysroot={sysroot}")
            ldflags.insert(1, f"--sysroot={sysroot}")
            cflags.append(f"-I{sysroot}/usr/include")
            # crt*.o 与 libc 位于 <sysroot>/usr/lib/<target>/，普通 -L<sysroot>/usr/lib
            # 找不到它们（实测），故必须显式加上该三元组子目录
            ldflags.append(f"-L{sysroot}/usr/lib/{OHOS_TARGET}")
        return " ".join(cflags), " ".join(ldflags)

    # ★2026-10-10 修复（实测）★ 旧实现用两份**上下文 diff** 给 build-aux/config.guess|config.sub 打补丁，
    #   但 source() 里的 `autoreconf -fi` 会用 `automake --add-missing --copy` 把 **automake 发行版自带**的
    #   config.guess/config.sub 覆盖进 build-aux/（实测与 $(automake --print-libdir)/… 字节相同），于是补丁的
    #   上下文取决于**构建机的 automake 版本**：鸿蒙 PC(automake 1.19) 上两个 hunk 双双不匹配
    #   （expected b'Linux|GNU|GNU/*)' vs actual b'Ironclad|Linux|GNU|GNU/*)'）-> conan create 失败。
    #   现在改成**上下文无关的带守卫锚行插入**（在 autoreconf 之后执行）：
    #     · 文件里已有 HarmonyOS / ohos 就跳过（幂等，已在鸿蒙 PC 实测：连跑两次 sha256 相同）
    #     · config.guess 锚点找不到 -> 报错（这项能力必需）
    #     · config.sub 旧式列表没匹配上 -> 只 WARN（新版 automake 的 config.sub 本就自带 ohos）
    def _ensure_harmonyos_config(self):
        def _read(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                return f.read()

        def _write(p, t):
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(t)

        guess = os.path.join(self.source_folder, "build-aux", "config.guess")
        sub = os.path.join(self.source_folder, "build-aux", "config.sub")

        if os.path.exists(guess):
            t = _read(guess)
            if "HarmonyOS" in t:
                self.output.info("config.guess: 已含 HarmonyOS，跳过插入")
            else:
                a1 = "case $UNAME_SYSTEM in"
                a2 = "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in"
                if a1 not in t or a2 not in t:
                    raise ConanException("config.guess 缺少 HarmonyOS 插入锚点（上游结构变了，需人工改配方）")
                t = t.replace(a1, a1 + "\nHarmonyOS)\n\tLIBC=gnu\n\t;;", 1)
                t = t.replace(a2, a2 + "\n    *:HarmonyOS:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;", 1)
                _write(guess, t)
                self.output.info("config.guess: 已用锚行插入 HarmonyOS 分支（不依赖补丁上下文）")

        if os.path.exists(sub):
            t = _read(sub)
            if "ohos" in t:
                self.output.info("config.sub: 已认 ohos（新版 automake 自带），跳过插入")
            else:
                before = t
                m1 = "gnu* | android* |"
                if m1 in t:
                    t = t.replace(m1, "gnu* | android* | ohos* |", 1)
                m2 = "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib*"
                if m2 in t:
                    t = t.replace(m2, m2 + " | linux-ohos*", 1)
                if t != before:
                    _write(sub, t)
                    self.output.info("config.sub: 已注入 ohos*（旧式列表）")
                else:
                    self.output.warning("config.sub: 不含 ohos 且旧式列表也没匹配上，保持原样（只影响 --host 规范化）")

    def build(self):
        # ★2026-10-10★ 不再用 conandata 里的上下文补丁：HarmonyOS 支持改由 source() 末尾的
        #   _ensure_harmonyos_config() 用**锚行插入**完成（与 automake 版本解耦，实测幂等）。
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            # HMDFS 上 umask 077 会导致临时文件权限问题（R6：用 Conan API）
            replace_in_file(self, configure, "umask 077", "umask 022")

        cflags, ldflags = self._dep_flags()
        gpg_error = self._dep("libgpg-error").package_folder
        libassuan = self._dep("libassuan").package_folder
        ncurses = self._dep("ncurses").package_folder

        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.configure(args=[
                # 显式覆盖探测结果 —— 依赖的 *-config 脚本返回的是宿主路径
                # （实测 `-L/lib -lassuan`、`-L//lib -lgpg-error`），不可信
                f"CFLAGS={cflags}",
                f"LDFLAGS={ldflags}",
                f"GPG_ERROR_CFLAGS=-I{gpg_error}/include",
                f"GPG_ERROR_LIBS=-L{gpg_error}/lib -lgpg-error",
                f"LIBASSUAN_CFLAGS=-I{libassuan}/include",
                f"LIBASSUAN_LIBS=-L{libassuan}/lib -lassuan",
                f"NCURSES_CFLAGS=-D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600 "
                f"-I{ncurses}/include",
                # ⚠️ 不能带 -ltinfo：OHOS 的 ncurses/6.6 制品只有静态
                # libncursesw.a、没有 libtinfo（实测 gnu 工具链探测出的
                # `-lncursesw -ltinfo` 会让链接报 unable to find library -ltinfo）
                f"NCURSES_LIBS=-L{ncurses}/lib -lncursesw",
            ])
            autotools.make(args=["-j4"])

    def package(self):
        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

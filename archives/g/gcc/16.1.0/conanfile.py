#!/usr/bin/env python3
"""Conan recipe — gcc 16.1.0（GCC 编译器本体，C/C++ 前端，含 libstdc++-v3 + libitm）。

本包构建 GCC 16 的 C（cc1）与 C++（cc1plus）语言前端 + libgcc + libstdc++-v3，
并保留 libitm（--enable-libitm），作为 libitm 上游 22 个依赖 -fgnu-tm 测试的
消费编译器。

与 gcobol/16.1.0（c,cobol）的本质差异：
  - --enable-languages=c,c++（而非 c,cobol）；
  - 构建 libstdc++-v3（gcobol 显式移除了它，因为 COBOL 不需要 C++ 标准库，
    且其 configure "cannot run C compiled programs" 失败）；
  - 保留 libitm（gcobol 用 --disable-libitm，本包必须 --enable-libitm）；
  - 去掉 gcobol 专属的 COBOL patch（lexio/symbols/genapi/charmaps/util/symfind）。

关键适配点（OHOS 特有，复用 gcobol/gcc-ada/libgcobol 已验证经验）：
  - HMDFS 无执行位（E046/E087）→ configure 用 /bin/sh 执行；
  - config.status 临时目录（E011/E052/E060）→ patch mktemp 到 $TMPDIR；
  - LLVM-only 工具链（E012）→ export AR=llvm-ar 等；
  - clang 构建 GCC 源码 → --disable-werror 规避 GCC 特有告警；
  - OHOS 是 musl：驱动默认动态链接器是 glibc 的 /lib/ld-linux-aarch64.so.1，
    gcc/g++ 驱动 wrapper 加 -mmusl 切到 /lib/ld-musl-aarch64.so.1；
  - OHOS 动态链接器不认未签名的 ELF → package() 对全部 ELF 签名。
"""
import hashlib
import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import get, unzip
from conan.tools.layout import basic_layout


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class GccConan(ConanFile):
    name = "gcc"
    version = "16.1.0"
    package_type = "application"
    description = "GNU Compiler Collection 16 C/C++ compiler (cc1 + cc1plus + libstdc++ + libitm)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/"

    settings = "os", "compiler", "build_type", "arch"

    # GCC 源码树解压后约 2GB（含 libstdc++-v3 等 target library），Conan 默认
    # 把整个 source 树复制到 build folder 是纯开销，在 hmdfs 上既慢又耗
    # inode/磁盘（见 libitm 的 inode 耗尽 Errno 28）。GCC 支持 out-of-tree
    # 构建（configure 在 build 目录跑，引用 source 目录），故跳过复制。
    no_copy_source = True

    _target_triplet = "aarch64-linux-ohos"
    _ohos_sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
    _ohos_llvm = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"
    _tmpdir = "/data/storage/el2/base/cache"

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "gcc 16.1.0 is prepared for a native OHOS build only")

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"][str(self.version)]
        # 影子 CI / 弱网环境：优先使用本机预置的源码 tarball（GCC_SOURCE_CACHE
        # 目录，按 sha256 校验），避免从 ftp.gnu.org 下载 ~100MB 源码超时/卡死；
        # 未命中时回退到原始 URL，保证真实 CI 的可复现性。
        cache = os.environ.get("GCC_SOURCE_CACHE", "").strip()

        def _fetch(entry, dest_dir=""):
            url = entry["url"]
            sha256 = entry["sha256"]
            # CI 的 mirror fallback 会把 conandata.yml 的 url 改写为多镜像 URL 列表
            # （str 或 list 两种形态都出现）。basename 取第一个 URL 的文件名（各镜像
            # 同名文件）；conan.tools.files.get 原生支持 url 列表、逐镜像重试。
            first_url = url[0] if isinstance(url, list) else url
            basename = os.path.basename(first_url)
            dest = (os.path.join(self.source_folder, dest_dir)
                    if dest_dir else self.source_folder)
            if cache:
                local = os.path.join(cache, basename)
                if os.path.isfile(local) and _sha256(local) == sha256:
                    self.output.info("[gcc] staged source hit: %s" % local)
                    tmp = os.path.join(self.source_folder, basename)
                    shutil.copy2(local, tmp)
                    unzip(self, tmp, destination=dest, strip_root=True)
                    os.unlink(tmp)
                    return
                if os.path.isfile(local):
                    self.output.warning(
                        "[gcc] staged source sha256 mismatch, fallback to URL: %s"
                        % local)
            get(self, url=url, sha256=sha256, strip_root=True, destination=dest)

        _fetch(src["gcc"])
        for name in ("gmp", "mpfr", "mpc"):
            _fetch(src[name], dest_dir=name)

    def _configure_args(self):
        return [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(self._target_triplet),
            "--host={}".format(self._target_triplet),
            "--target={}".format(self._target_triplet),
            "--enable-languages=c,c++",
            "--enable-threads=posix",
            # PICFLAG=-fPIC：gcc/configure.ac 里 enable_host_shared=yes 时
            # PICFLAG=-fPIC；否则默认 -fno-PIE，clang 非 PIC 的 LDST64 绝对
            # 寻址触发 lld 对齐检查失败（R_AARCH64_LDST64_ABS_LO12_NC improper
            # alignment，链接 gcov 等 host 工具时）。这是根因，比 patch Makefile
            # 更根本（Makefile 的 PICFLAG 是 @PICFLAG@ 占位符，由 configure 填）。
            "--enable-host-shared",
            "--disable-bootstrap",
            "--disable-lto",
            "--disable-plugin",
            "--disable-multilib",
            "--disable-nls",
            # CI worker 无 texi2pod/makeinfo，文档生成会失败；只发布编译器二进制。
            "--disable-doc",
            "--disable-shared",
            "--disable-libatomic",
            # 保留 libitm（libitm 测试的消费编译器依赖它）。
            "--enable-libitm",
            "--disable-libsanitizer",
            "--disable-libgomp",
            "--disable-libquadmath",
            "--disable-libssp",
            "--disable-libvtv",
            "--disable-werror",
            "--without-isl",
            "--with-sysroot={}".format(self._ohos_sysroot),
            "--with-native-system-header-dir=/usr/include",
        ]

    def _patch_ohos_sources(self):
        """GCC 16 OHOS 源码适配（gcobol 16.1.0 已验证的通用 patch 子集）。"""
        src = self.source_folder

        # 1. config.sub 注入 ohos triplet（E122）
        scripts = []
        for name in ("config.sub", "configfsf.sub"):
            scripts += _glob(src, name)
        for script in scripts:
            with open(script, "r", errors="surrogateescape") as f:
                content = f.read()
            marker = "# HarmonyOS triplet compatibility (Conan recipe)"
            if marker in content:
                continue
            snippet = (
                "\n{marker}\n"
                'case "$1" in\n'
                "  aarch64-linux-ohos | aarch64-unknown-linux-ohos | "
                "none-unknown-linux-ohos)\n"
                "    echo aarch64-unknown-linux-ohos\n"
                "    exit 0\n"
                "    ;;\n"
                "esac\n"
            ).format(marker=marker)
            newline = content.find("\n")
            if newline < 0:
                continue
            with open(script, "w", errors="surrogateescape") as f:
                f.write(content[: newline + 1] + snippet + content[newline + 1:])

        # 2. 所有 configure 的 mktemp -> $TMPDIR
        for configure in _glob(src, "configure"):
            with open(configure, "r", errors="surrogateescape") as f:
                t = f.read()
            fixed = t.replace(
                'mktemp -d "./confXXXXXX"', 'mktemp -d "$TMPDIR/confXXXXXX"'
            )
            fixed = fixed.replace(
                "tmp=./conf$$-$RANDOM", "tmp=$TMPDIR/conf$$-$RANDOM"
            )
            if fixed != t:
                with open(configure, "w", errors="surrogateescape") as f:
                    f.write(fixed)

        # 3. move-if-change 通过 $(SHELL)
        move_pat = re.compile(
            r"(?<!\$\(SHELL\) )\$\(srcdir\)/\.\./move-if-change")
        for mk in _glob(src, "Makefile.in") + _glob(src, "Make-lang.in"):
            with open(mk, "r", errors="surrogateescape") as f:
                t = f.read()
            fixed = move_pat.sub("$(SHELL) $(srcdir)/../move-if-change", t)
            if fixed != t:
                with open(mk, "w", errors="surrogateescape") as f:
                    f.write(fixed)

        # 4. gmp m4-ccas 通过 $(SHELL)
        m4_path = os.path.join(src, "gmp", "mpn", "Makefile.in")
        if os.path.isfile(m4_path):
            with open(m4_path, "r", errors="surrogateescape") as f:
                t = f.read()
            direct = ("\t$(LIBTOOL) --mode=compile --tag=CC "
                      "$(top_srcdir)/mpn/m4-ccas ")
            through = ("\t$(LIBTOOL) --mode=compile --tag=CC "
                       "$(SHELL) $(top_srcdir)/mpn/m4-ccas ")
            if direct in t and through not in t:
                with open(m4_path, "w", errors="surrogateescape") as f:
                    f.write(t.replace(direct, through, 1))

        # 5. mpfr get_patches.sh 通过 $(SHELL)
        mpfr_mk = os.path.join(src, "mpfr", "src", "Makefile.in")
        if os.path.isfile(mpfr_mk):
            with open(mpfr_mk, "r", errors="surrogateescape") as f:
                t = f.read()
            direct = "\t$(GET_PATCHES_SH) $(PATCHES) > $@"
            through = "\t$(SHELL) $(GET_PATCHES_SH) $(PATCHES) > $@"
            if direct in t and through not in t:
                with open(mpfr_mk, "w", errors="surrogateescape") as f:
                    f.write(t.replace(direct, through, 1))

        # 6. defaults.h: GCC 16 把 stack-check 默认宏放进 #ifdef GCC_INSN_FLAGS_H
        defaults = os.path.join(src, "gcc", "defaults.h")
        if os.path.isfile(defaults):
            with open(defaults, "r", errors="surrogateescape") as f:
                t = f.read()
            anchor = "#ifdef GCC_INSN_FLAGS_H\n"
            if "OHOS stack-check unconditional" not in t and anchor in t:
                snip = (
                    "/* OHOS stack-check unconditional defaults */\n"
                    "#ifndef STACK_CHECK_MAX_VAR_SIZE\n#define STACK_CHECK_MAX_VAR_SIZE 40\n#endif\n"
                    "#ifndef STACK_CHECK_MAX_FRAME_SIZE\n#define STACK_CHECK_MAX_FRAME_SIZE 4088\n#endif\n"
                    "#ifndef STACK_CHECK_PROBE_INTERVAL_EXP\n#define STACK_CHECK_PROBE_INTERVAL_EXP 12\n#endif\n"
                    "#ifndef STACK_CHECK_STATIC_BUILTIN\n#define STACK_CHECK_STATIC_BUILTIN 0\n#endif\n"
                    "#ifndef STACK_CHECK_BUILTIN\n#define STACK_CHECK_BUILTIN 0\n#endif\n\n"
                )
                t = t.replace(anchor, snip + anchor, 1)
                with open(defaults, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 7. libgcc lse-init.c: __getauxval（glibc 内部）→ getauxval（musl 公开）
        lse = os.path.join(src, "libgcc", "config", "aarch64", "lse-init.c")
        if os.path.isfile(lse):
            with open(lse, "r", errors="surrogateescape") as f:
                t = f.read()
            old = "unsigned long int __getauxval (unsigned long int);\n"
            new = ("/* OHOS musl exports getauxval, not glibc's internal __getauxval. */\n"
                   "unsigned long int getauxval (unsigned long int);\n")
            if old in t:
                t = t.replace(old, new, 1)
                t = t.replace(
                    "unsigned long hwcap = __getauxval (AT_HWCAP);",
                    "unsigned long hwcap = getauxval (AT_HWCAP);",
                    1,
                )
                with open(lse, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 8. libgcc gthr-posix.h: OHOS 不支持 pthread_cancel
        gthr = os.path.join(src, "libgcc", "gthr-posix.h")
        if os.path.isfile(gthr):
            with open(gthr, "r", errors="surrogateescape") as f:
                t = f.read()
            repls = (
                (
                    "#ifndef __BIONIC__\n__gthrw(pthread_cancel)\n#endif",
                    "#if !defined (__BIONIC__) && !defined (__OHOS__)\n__gthrw(pthread_cancel)\n#endif",
                ),
                (
                    "#elif defined (__BIONIC__)\n# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_create)",
                    "#elif defined (__BIONIC__) || defined (__OHOS__)\n# define GTHR_ACTIVE_PROXY\t__gthrw_(pthread_create)",
                ),
            )
            changed = False
            for old, new in repls:
                if new not in t and old in t:
                    t = t.replace(old, new, 1)
                    changed = True
            if changed:
                with open(gthr, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 9. libgcc mkheader.sh 通过 $(SHELL) + unwind_h 去双重 shell
        lg_mk = os.path.join(src, "libgcc", "Makefile.in")
        if os.path.isfile(lg_mk):
            with open(lg_mk, "r", errors="surrogateescape") as f:
                t = f.read()
            direct = "\t\t$(srcdir)/mkheader.sh > tmp-libgcc_tm.h"
            through = "\t\t$(SHELL) $(srcdir)/mkheader.sh > tmp-libgcc_tm.h"
            if direct in t and through not in t:
                t = t.replace(direct, through, 1)
            bad = "\tsh $(SHELL) $(srcdir)/../move-if-change $$dest $(gcc_objdir)/include/unwind.h"
            good = "\t$(SHELL) $(srcdir)/../move-if-change $$dest $(gcc_objdir)/include/unwind.h"
            if bad in t:
                t = t.replace(bad, good, 1)
            with open(lg_mk, "w", errors="surrogateescape") as f:
                f.write(t)

        # 10. 创建 ginclude/ohos-availability.h：屏蔽 OHOS sysroot 头文件裸用的
        #     clang __availability__ 属性。OHOS 的 unistd.h/stdio.h 直接写
        #     __attribute__((__availability__(ohos, introduced=12.0.0)))，GCC 不识别
        #     该 clang 属性（把 "12.0.0" 当非法数字字面量报
        #     "too many decimal points in number"）。此头文件通过 build() 里
        #     CFLAGS/CXXFLAGS_FOR_TARGET 的 -include 注入，对所有 target 库
        #     （libgcc/libstdc++-v3/libitm）编译统一生效，覆盖直接 include 系统
        #     头文件的源文件（如 libgcc heap-trampoline.c）。
        avail = os.path.join(src, "gcc", "ginclude", "ohos-availability.h")
        with open(avail, "w", errors="surrogateescape") as f:
            f.write("#ifndef __clang__\n#define __availability__(...) \n#endif\n")

        # 13. 创建 ginclude/ohos-c99-math.h：显式定义 C99 数学函数宏。
        #     cross-compile 模式下 libstdc++ configure 跳过 AC_TRY_RUN（运行检测），
        #     _GLIBCXX_HAVE_ACOSF 等宏未定义，导致 cmath 里 using ::acosf 被跳过、
        #     std.cc（C++23 module std）报 "acosf has not been declared in std"。
        #     OHOS musl 实际提供这些 C99 数学函数，经 CXXFLAGS_FOR_TARGET 注入。
        c99_funcs = [
            "ACOSF", "ACOSL", "ASINF", "ASINL", "ATAN2F", "ATAN2L", "ATANF", "ATANL",
            "CEILF", "CEILL", "COSF", "COSHF", "COSHL", "COSL", "EXPF", "EXPL",
            "FABSF", "FABSL", "FLOORF", "FLOORL", "FMODF", "FMODL", "FREXPF", "FREXPL",
            "LDEXPF", "LDEXPL", "LOG10F", "LOG10L", "LOGF", "LOGL", "MODFF", "MODFL",
            "POWF", "POWL", "SINF", "SINHF", "SINHL", "SINL", "SQRTF", "SQRTL",
            "TANF", "TANHF", "TANHL", "TANL",
        ]
        c99_h = "/* OHOS musl C99 math functions: define explicitly because\n"
        c99_h += "   cross-compile configure skips the AC_TRY_RUN checks. */\n"
        for _name in c99_funcs:
            c99_h += "#define _GLIBCXX_HAVE_{} 1\n".format(_name)
        c99 = os.path.join(src, "gcc", "ginclude", "ohos-c99-math.h")
        with open(c99, "w", errors="surrogateescape") as f:
            f.write(c99_h)

        # 11. libstdc++-v3 + libitm configure：cross_compiling=no → yes，跳过运行测试。
        #     OHOS 上未签名 ELF 一律 Permission denied（即使有 exec 位），configure
        #     编译的 conftest 无法运行，报 "cannot run C compiled programs"（gcobol
        #     移除 libstdc++-v3 的同一根因）。强制 cross-compile 模式跳过运行探测。
        for _cfg in ("libstdc++-v3", "libitm"):
            _c = os.path.join(src, _cfg, "configure")
            if os.path.isfile(_c):
                with open(_c, "r", errors="surrogateescape") as f:
                    t = f.read()
                anchor = "LIBOBJS=\ncross_compiling=no\nsubdirs="
                if anchor in t:
                    t = t.replace(
                        anchor, "LIBOBJS=\ncross_compiling=yes\nsubdirs=", 1)
                    with open(_c, "w", errors="surrogateescape") as f:
                        f.write(t)

        # 12. libstdc++-v3 configure.host：把 linux-ohos 归入 musl 分支（os/generic）。
        #     默认 host_os=linux-ohos 匹配 linux* 分支走 os/gnu-linux（glibc），生成
        #     的 os_defines.h 裸用 __GLIBC_PREREQ，而 OHOS 是 musl 无此宏，libsupc++
        #     编译报 "missing binary operator before token '('"。归入 generic 后干净。
        ch = os.path.join(src, "libstdc++-v3", "configure.host")
        if os.path.isfile(ch):
            with open(ch, "r", errors="surrogateescape") as f:
                t = f.read()
            old = 'linux-musl*)\n    os_include_dir="os/generic"'
            new = 'linux-musl* | linux-ohos*)\n    os_include_dir="os/generic"'
            if "linux-ohos" not in t and old in t:
                t = t.replace(old, new, 1)
                with open(ch, "w", errors="surrogateescape") as f:
                    f.write(t)

        # 14. libstdc++-v3 src/c++23/Makefile.in：relpath.sh 通过 /bin/sh 执行。
        #     HMDFS 无 exec 位，直接 $(toplevel_srcdir)/contrib/relpath.sh 报
        #     "Permission denied"（Error 126），生成 libstdc++.modules.json 失败。
        c23_mk = os.path.join(src, "libstdc++-v3", "src", "c++23", "Makefile.in")
        if os.path.isfile(c23_mk):
            with open(c23_mk, "r", errors="surrogateescape") as f:
                t = f.read()
            old = "relpath=$$($(toplevel_srcdir)/contrib/relpath.sh"
            new = "relpath=$$(/bin/sh $(toplevel_srcdir)/contrib/relpath.sh"
            if new not in t and old in t:
                t = t.replace(old, new, 1)
                with open(c23_mk, "w", errors="surrogateescape") as f:
                    f.write(t)

    @property
    def _toolchain_env(self):
        return (
            "AR=/data/service/hnp/bin/llvm-ar NM=/data/service/hnp/bin/llvm-nm "
            "RANLIB=/data/service/hnp/bin/llvm-ranlib STRIP=/data/service/hnp/bin/llvm-strip "
            "OBJCOPY=/data/service/hnp/bin/llvm-objcopy "
            "READELF=/data/service/hnp/bin/llvm-readelf LD=/data/service/hnp/bin/ld.lld "
            "CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ "
            "CC_FOR_BUILD=/data/service/hnp/bin/clang "
            "CXX_FOR_BUILD=/data/service/hnp/bin/clang++ "
            "CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
            "TMPDIR=/data/storage/el2/base/cache "
            "CFLAGS=\"-g -O2 -fPIC -mstrict-align\" "
            "CXXFLAGS=\"-g -O2 -fPIC -mstrict-align\" "
            "PATH=/data/service/hnp/bin:$PATH"
        )

    def generate(self):
        from conan.tools.env import Environment
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.define("NM", "/data/service/hnp/bin/llvm-nm")
        env.define("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        env.define("STRIP", "/data/service/hnp/bin/llvm-strip")
        env.define("OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        env.define("READELF", "/data/service/hnp/bin/llvm-readelf")
        env.define("LD", "/data/service/hnp/bin/ld.lld")
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("CXX", "/data/service/hnp/bin/clang++")
        env.define("CC_FOR_BUILD", "/data/service/hnp/bin/clang")
        env.define("CXX_FOR_BUILD", "/data/service/hnp/bin/clang++")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        env.define("CFLAGS", "-g -O2 -fPIC -mstrict-align")
        env.define("CXXFLAGS", "-g -O2 -fPIC -mstrict-align")
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self).save_script("gcc_build_env")

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        src = self.source_folder

        self._patch_ohos_sources()

        tmpdir = self._tmpdir
        os.makedirs(tmpdir, exist_ok=True)

        build_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(build_dir, exist_ok=True)

        # 1. configure
        self.run(
            "cd {0} && export {1} && mkdir -p {2} && "
            "TMPDIR={2} /bin/sh {3} {4}".format(
                build_dir, self._toolchain_env, tmpdir, configure,
                " ".join(self._configure_args())),
            env="gcc_build_env",
        )

        # patch 生成的 tm.h: 加 insn-flags.h include
        tmh = os.path.join(build_dir, "tm.h")
        if os.path.isfile(tmh):
            with open(tmh, "r", errors="surrogateescape") as f:
                t = f.read()
            if '# include "insn-flags.h"' not in t:
                t = t.replace(
                    '# include "insn-constants.h"\n',
                    '# include "insn-constants.h"\n# include "insn-flags.h"\n',
                    1,
                )
                with open(tmh, "w", errors="surrogateescape") as f:
                    f.write(t)
        # 真机 20 核；内存空闲充足时（>10GB）用 -j8 榨干提速，紧张时降并行。
        # 但 libstdc++ 的 C++23 模块（std.cc 大文件，include 全部头文件）在 -j8
        # 并行时 cc1plus 内存峰值超限，报 ICE "Segmentation fault"。降到 -j4 平衡
        # 速度与内存（实测 -j4 下 std.cc 可正常编译）。
        jobs = max(1, min(build_jobs(self), 4))

        # 2. all-gcc（cc1 + cc1plus + gcc/g++ 驱动）
        self.run(
            "ulimit -s unlimited && export {0} && make -C {1} -j{2} all-gcc".format(
                self._toolchain_env, build_dir, jobs),
            env="gcc_build_env",
        )

        # 删除 GCC 的 as/ld/nm/collect-ld 包装脚本（HMDFS 无 exec 位）
        for name in ("as", "collect-ld", "nm"):
            p = os.path.join(build_dir, "gcc", name)
            if os.path.exists(p):
                os.remove(p)

        # 3. all-target-libgcc + all-target-libstdc++-v3 + all-target-libitm
        #    （gcc c,c++ 需要 libstdc++-v3，与 gcobol 移除 libstdc++-v3 不同；
        #     保留 libitm 供 libitm 测试消费）
        target = self._target_triplet
        sysr = self._ohos_sysroot
        xgcc = os.path.join(build_dir, "gcc", "xgcc")
        xgcc_args = (
            "-B{0}/gcc/ -B/data/service/hnp/bin/ "
            "-B{1}/usr/lib/{2}/ -isystem {1}/usr/include/{2} "
            "-isystem {1}/usr/include --sysroot={1}".format(build_dir, sysr, target)
        )
        cc_for_target = "{} {}".format(xgcc, xgcc_args)
        # OHOS sysroot 头文件裸用 clang 的 __availability__ 属性，GCC 不识别；经
        # CFLAGS/CXXFLAGS_FOR_TARGET 注入 ginclude/ohos-availability.h（-include）
        # 把 __availability__ 屏蔽为空函数宏。用 -include 而非 -D'__availability__(...)='
        # 是因为 (...) 在 make 经 /bin/sh 执行汇编(.S)命令时会被 shell 解析成语法错误。
        avail_inc = os.path.join(src, "gcc", "ginclude", "ohos-availability.h")
        # libstdc++ configure 的 CPP/CXXCPP 探测会用 --prefix=/ 派生的错误路径
        # （//aarch64-linux-ohos/include，且不带 -B 找不到 build 目录 cc1），导致
        # "C++ preprocessor fails sanity check"。显式给出带 -B + sysroot include 的
        # 预处理命令，绕过探测。
        cpp_cmd = (
            "{0} -B{1}/gcc/ -B/data/service/hnp/bin/ -E --sysroot={2} "
            "-isystem {2}/usr/include/{3} -isystem {2}/usr/include -D__OHOS__".format(
                xgcc, build_dir, sysr, target)
        )
        # libstdc++ 编译用 configure 构造的 RAW_CXX_FOR_TARGET（-nostdinc++ 且缺
        # sysroot 架构 include），需经 CFLAGS/CXXFLAGS_FOR_TARGET 补 sysroot include，
        # 否则 bits/alltypes.h（在 sysroot/usr/include/aarch64-linux-ohos/bits/）找不到。
        # 同时 -DHAVE_DECL_BASENAME=1：cross-compile 使 HAVE_DECL_BASENAME=0，libiberty.h
        # 在 __linux__ 下声明 char *basename(const char *)，与 OHOS musl string.h 的
        # char *basename()（旧式）冲突，报 "conflicting types for 'basename'"。
        sysinc = ("--sysroot={0} -isystem {0}/usr/include/{1} "
                  "-isystem {0}/usr/include -DHAVE_DECL_BASENAME=1".format(
                      sysr, target))
        c99_inc = os.path.join(src, "gcc", "ginclude", "ohos-c99-math.h")
        self.run(
            "ulimit -s unlimited && export {0} && "
            "export CPP=\"{5}\" CXXCPP=\"{5}\" && make -C {1} -j{2} "
            "all-target-libgcc all-target-libstdc++-v3 all-target-libitm "
            "CC_FOR_TARGET=\"{3}\" "
            "CFLAGS_FOR_TARGET=\"-g -O2 -fPIC -D__OHOS__ -include {4} {6}\" "
            "CXXFLAGS_FOR_TARGET=\"-g -O2 -fPIC -D__OHOS__ -include {4} "
            "-include {7} {6}\"".format(
                self._toolchain_env, build_dir, jobs, cc_for_target, avail_inc,
                cpp_cmd, sysinc, c99_inc),
            env="gcc_build_env",
        )

    @staticmethod
    def _required_executable(name, *candidates):
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                    candidate, os.X_OK):
                resolved = os.path.abspath(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name))

    def _sign_elf_tree(self, root):
        signer = self._required_executable(
            "binary-sign-tool", "binary-sign-tool",
            "/data/service/hnp/bin/binary-sign-tool")
        objcopy = self._required_executable(
            "llvm-objcopy", "llvm-objcopy",
            "/data/service/hnp/bin/llvm-objcopy")
        readelf = self._required_executable(
            "llvm-readelf", "llvm-readelf",
            "/data/service/hnp/bin/llvm-readelf")

        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)],
                capture_output=True, text=True)
            if probe.returncode != 0:
                continue
            secs = subprocess.run(
                [readelf, "-S", str(candidate)],
                capture_output=True, text=True)
            if ".codesign" in secs.stdout:
                continue
            if not re.search(r"Type:\s+(?:EXEC|DYN)\b", probe.stdout):
                continue
            original_mode = stat.S_IMODE(candidate.stat().st_mode)
            unsigned = str(candidate) + ".ohos-unsigned"
            signed = str(candidate) + ".ohos-signed"
            shutil.copy2(str(candidate), unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False)
            subprocess.run(
                [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                 "-selfSign", "1"], check=True)
            if ".codesign" not in subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True, text=True).stdout:
                raise ConanException(
                    "Signing did not add .codesign: {}".format(candidate))
            os.replace(signed, str(candidate))
            try:
                os.remove(unsigned)
            except OSError:
                pass
            os.chmod(str(candidate), original_mode | stat.S_IXUSR
                     | stat.S_IXGRP | stat.S_IXOTH)

    def _install_ohos_driver_wrapper(self):
        """把 DESTDIR 安装的 gcc/g++ 驱动改造成可重定位 + OHOS 适配 wrapper。"""
        bindir = Path(self.package_folder) / "bin"
        target = self._target_triplet
        version = "16.1.0"
        sysroot = self._ohos_sysroot
        signer = self._required_executable(
            "binary-sign-tool", "binary-sign-tool",
            "/data/service/hnp/bin/binary-sign-tool")
        objcopy = self._required_executable(
            "llvm-objcopy", "llvm-objcopy",
            "/data/service/hnp/bin/llvm-objcopy")
        readelf = self._required_executable(
            "llvm-readelf", "llvm-readelf",
            "/data/service/hnp/bin/llvm-readelf")

        # gcc 和 g++ 都装 wrapper。gcc 驱动编译 C，g++ 驱动编译 C++。
        for driver_name in ("gcc", "g++"):
            driver = bindir / driver_name
            real_driver = bindir / (driver_name + ".real")
            if not driver.is_file():
                continue
            os.replace(driver, real_driver)
            wrapper = """#!/bin/sh
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/{driver_name}.real"
target={target}
version={version}
sysroot={sysroot}
signer={signer}
objcopy={objcopy}
readelf={readelf}

export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"

set -- -mmusl "$@"
set -- '-D__availability__(...)'= "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
set -- "-L$package_root/lib/" "$@"

"$real_driver" "$@"

output=""
previous=""
compile_only=0
for argument in "$@"; do
    if [ "$previous" = "-o" ]; then
        output="$argument"
        previous=""
        continue
    fi
    case "$argument" in
        -o) previous="-o" ;;
        -o?*) output="${{argument#-o}}" ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done

if [ "$compile_only" -eq 0 ] && [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        if ! "$readelf" -S "$output" 2>/dev/null | grep -q '[.]codesign'; then
            unsigned="${{output}}.ohos-unsigned-$$"
            signed="${{output}}.ohos-signed-$$"
            cp -p "$output" "$unsigned"
            "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
            "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
            mv "$signed" "$output"
            rm -f "$unsigned"
            chmod +x "$output" 2>/dev/null || true
        fi
    fi
fi
exit 0
""".format(
                driver_name=driver_name,
                target=shlex.quote(target),
                version=shlex.quote(version),
                sysroot=shlex.quote(sysroot),
                signer=shlex.quote(signer),
                objcopy=shlex.quote(objcopy),
                readelf=shlex.quote(readelf),
            )
            driver.write_text(wrapper, encoding="utf-8")
            driver.chmod(
                driver.stat().st_mode | stat.S_IXUSR
                | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        build_dir = os.path.join(self.build_folder, "obj")
        self.run(
            "make -C {0} install-gcc install-target-libgcc "
            "install-target-libstdc++-v3 install-target-libitm DESTDIR={1}".format(
                build_dir, self.package_folder),
            env="gcc_build_env",
        )
        # 清理 libtool .la（烤死绝对路径）
        import glob as _glob
        for la in _glob.glob(os.path.join(self.package_folder, "**", "*.la"),
                             recursive=True):
            os.remove(la)

        # 安装 OHOS 驱动 wrapper（加 -mmusl/-B/-isystem）
        self._install_ohos_driver_wrapper()

        # 复制 OHOS binutils 工具（as/ld/nm/ar/ranlib/strip）到 package 的
        # lib/gcc/$target/$version/。OHOS SDK 的 binutils 未签名，gcc.real 经
        # posix_spawn 执行时 Permission denied；复制后由下方 _sign_elf_tree 统一
        # 签名。as（汇编）和 ld（链接）是 gcc 编译用户程序的必需外部工具。
        binutils_dir = ("/data/service/hnp/binutils.org/binutils_2.45/"
                        "aarch64-linux-musl/bin")
        tool_dest = os.path.join(self.package_folder, "lib", "gcc",
                                 self._target_triplet, "16.1.0")
        for _tool in ("as", "ld", "nm", "ar", "ranlib", "strip"):
            _src = os.path.join(binutils_dir, _tool)
            if os.path.isfile(_src):
                shutil.copy2(_src, os.path.join(tool_dest, _tool))

        # 对 package 内所有 ELF 签名（.so + 可执行）
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))


def _glob(root, name):
    import glob as _g
    return _g.glob(os.path.join(root, "**", name), recursive=True)

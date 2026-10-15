#!/usr/bin/env python3
"""Conan recipe — lpr 2008.05.17.4（BSD 行式打印机假脱机系统）适配 HarmonyOS PC。

上游 = OpenBSD lpr，Debian 以 **native** tarball 维护（lpr_2008.05.17.4.dsc:
``Format: 3.0 (native)`` / ``Version: 1:2008.05.17.4``），任务串版本号即该 tarball
的上游版本号。Debian 归档是唯一能 HTTP 200 取到该版本原样源码的一手渠道（上游
OpenBSD CVS 归档已下线，GitHub 无对应 tag/发布件），详见 conandata.yml。

构建系统：**纯手写 Makefile，没有 configure**
----------------------------------------------------------
顶层 Makefile 只是一层 ``for dir in $(SUBDIR); do $(MAKE) -C $$dir; done``，真正
的编译规则在 ``common_source/Makefile.in``（被 8 个子目录 Makefile 用
``include ../Makefile.in`` 引入）：

    .o.c:
            $(CC) ${CFLAGS} -c $<
    ${PROG}: ${OBJ}
            $(CC) -o ${PROG} ${OBJ}

八个程序与安装位置一一对应上游 ``debian/install``：
``lpr`` ``lpq`` ``lprm`` ``lptest`` → bin/，``lpc`` ``lpd`` ``lpf`` ``pac`` → sbin/。

配方不调顶层 Makefile，而是逐个子目录跑 make，两个原因：
1. 顶层 ``all`` 的失败分支用了 ``return 2`` —— 这是 csh 的关键字，POSIX sh
   （dash/busybox sh）会直接报 "return: can only `return' from a function"。
2. 顶层 for 循环在任何子目录失败后无法给出可诊断的 rc，逐目录跑能精确定位。

子目录 Makefile 用了 BSD make 的 ``${.CURDIR}``
------------------------------------------------
``CFLAGS+=-I${.CURDIR}/../common_source`` 里的 ``${.CURDIR}`` 是 **BSD make** 语法；
GNU make 把它当成名为 ``.CURDIR`` 的空变量，于是 CFLAGS 里留下一个悬空的
``-I/../common_source``。这正是 Debian 侧要额外传 ``-I../common_source`` 的原因
（debian/rules: ``DEB_CPPFLAGS_MAINT_APPEND = -D__KAME__ -I../common_source``）——
GNU make 下那个相对路径恰好是每个子目录里正确的路径。配方用**绝对**路径
``-I<source>/common_source``，比 Debian 的相对写法更稳（VPATH/子目录顺序无关）。

musl（OHOS libc）与 glibc 的四处差异 —— 全部在配方层解决，上游源码零改动
---------------------------------------------------------------------------
上游是 1993-2007 年的 BSD 代码，本来是给 BSD libc 写的；Debian 之所以能在
glibc 上过，是因为 glibc 保留了 4.4BSD 兼容面。musl 没有这一层，于是有四处必须
补齐，全部由 ``compat/`` 下的两个文件 + 编译旗标承担（``patches: {}``）：

1. ``u_int`` / ``u_quad_t`` 未定义 —— musl 的 ``<dirent.h>`` 不经过
   ``<sys/types.h>``，而 ``lp.h`` 只 include 了 ``<dirent.h>``。
   → 强制包含 ``<sys/types.h>``。
2. ``TTYDEF_*`` / ``CTRL()`` 未定义 —— glibc 的 ``<termios.h>`` 会 include
   ``<sys/ttydefaults.h>``（glibc termios.h:104），musl 的不会；``lpd/key.c`` 依赖它。
   → 强制包含 ``<sys/ttydefaults.h>``。该头文件在 OHOS sysroot 里**本来就有**，
   值就是 Linux 那套，所以这一条是"复现 Debian 在 glibc 上得到的同一组宏"，
   不是自己编值。
3. ``setresuid``/``setresgid``/``getifaddrs``/``freeifaddrs`` 未声明 —— musl 把它们
   关在 ``_GNU_SOURCE`` 后面；glibc 的默认特性集（``_DEFAULT_SOURCE``）就全部可见，
   所以这也只是补 musl 的缺口。→ 编译加 ``-D_GNU_SOURCE``。
   ``-D__KAME__`` 照抄 debian/rules（打开 ``common.c:391`` 的 link-local IPv6
   scope_id 处理；musl 的 ``struct sockaddr_in6`` 也有 ``sin6_scope_id``，
   ``IN6_IS_ADDR_LINKLOCAL`` 同在，实测编译通过）。
4. ``rresvport_af()`` 与 ``innetgr()`` **链接期缺符号** —— glibc 从 2.2.5 起导出这两个
   4.4BSD 遗留接口（在 ``<netdb.h>`` 声明），musl 既不声明也不导出：
   - ``rresvport_af()``：``common_source/common.c:164``，``getport()`` 用它占一个
     特权端口（<1024）用于回连远端 lpd。这是协议要求的，缺了 5 个客户端程序全部
     链接失败（``undefined symbol: rresvport_af``）。
   - ``innetgr()``：``lpd/rcmd.c:165,182,199,212``，``/etc/hosts.lpd`` /
     ``/etc/hosts.equiv`` 里 ``@``（domain）条目的 netgroup 查询。缺了 lpd 链接失败。
   → 在 ``compat/lpr_bsd_compat.c`` 里按 4.4BSD/OpenBSD 语义实现（该文件头注释
     写明了简化边界：不做 NIS、不解释 netgroup 字段里的 ``+``/``-``）。

   **注入方式**：上游链接规则 ``$(CC) -o ${PROG} ${OBJ}`` 既不吃 ``LDLIBS`` 也不吃
   ``LDFLAGS``，命令行上没有位置塞这个目标文件。配方因此生成一个编译器驱动包装脚本
   ``cc-ohos-wrap``（见 ``CC_WRAPPER``）：编译步骤（出现 ``-c``/``-E``/``-S``/``-M``）
   原样 exec 真驱动；链接步骤且目标程序在 COMPAT_USERS 里时，在末尾追加兼容 .o。
   ``lpf`` 与 ``lptest`` 不引用这两个符号，因此完全不被注入 —— 这一点在
   ``package()`` 里逐个 ELF 校验（见 ``_elf_symbols``）。

上游测试
--------
8 个子目录 Makefile + ``common_source/Makefile.in`` + 顶层 Makefile 一共只有
``all`` / ``clean`` / ``${PROG}`` / ``.o.c`` 四个目标，**没有任何 check/test 目标**
（``make check`` → "No rule to make target"），全树无 TESTS / check_PROGRAMS /
add_test，源码里也没有 tests/ 目录。五维账本：上游用例总数=0 执行=0 通过=0 失败=0
跳过=0。→ L1 在 ``ci/config/no_official_test.txt`` 白名单豁免（理由写在该文件里），
真实覆盖由 test_package 的消费者断言承担，不冒充上游测试。
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 顶层 Makefile 的 SUBDIR 变量，逐字照抄，顺序不变。
SUBDIRS = ("lpc", "lpd", "lpq", "lpr", "lprm", "lptest", "pac", "filters")

# 程序名 -> (子目录, 包内安装目录)，与上游 debian/install 一一对应。
PROGRAMS = {
    "lpr": ("lpr", "bin"),
    "lpq": ("lpq", "bin"),
    "lprm": ("lprm", "bin"),
    "lptest": ("lptest", "bin"),
    "lpc": ("lpc", "sbin"),
    "lpd": ("lpd", "sbin"),
    "lpf": ("filters", "sbin"),
    "pac": ("pac", "sbin"),
}

# 真正引用 compat/lpr_bsd_compat.c 里两个函数的那 6 个程序：
#   rresvport_af -> common_source/common.c:164，被所有链 common.c 的程序引用
#   innetgr      -> lpd/rcmd.c（只有 lpd 链 rcmd.c）
# lpd 同时链两者（lpd/Makefile 的 SRCS 里含 ../common_source/common.c）。
# lpf / lptest 是单文件程序，不引用，因此不得被注入。
COMPAT_USERS = frozenset({"lpc", "lpd", "lpq", "lpr", "lprm", "pac"})

# man page：debian/manpages 清单，去掉重复的路径前缀后落到标准 man 目录。
MAN_PAGES = {
    "man1": ("lpq/lpq.1", "lptest/lptest.1", "lprm/lprm.1", "lpr/lpr.1"),
    "man5": ("filters/lpf.8", "pac/pac.8", "lpc/lpc.8", "lpd/lpd.8",
             "debian/printcap.5"),
}

EM_AARCH64 = 183

CC_WRAPPER = """#!/bin/sh
# lpr recipe: compiler-driver wrapper, generated by conanfile.py.
#
# WHY: common_source/Makefile.in links with `$(CC) -o ${{PROG}} ${{OBJ}}` and
# honours neither LDLIBS nor LDFLAGS, so a compat object cannot be handed to the
# linker from the make command line.  lpr needs one (rresvport_af/innetgr, see
# compat/lpr_bsd_compat.c): without them ld.lld reports
# "undefined symbol: rresvport_af" for lpc/lpd/lpq/lpr/lprm/pac.
#
# WHAT: every invocation is handed to the real driver unchanged, except that a
# *link* step whose -o target is one of COMPAT_USERS gets the compat object
# appended.  Compile/preprocess steps (-c/-E/-S/-M/-MM) and links of programs
# outside COMPAT_USERS (lpf, lptest) are pure pass-through, so nothing can
# silently depend on the wrapper for anything else.
REAL={real}
OBJ={obj}
out=
want_out=0
for a in "$@"; do
        if [ "$want_out" = 1 ]; then out="$a"; want_out=0; continue; fi
        case "$a" in
        -o) want_out=1 ;;
        esac
done
case "$out" in
{user_cases}
        *) exec "$REAL" "$@" ;;
esac
"""


def _real_cc(self):
    compilers = self.conf.get("tools.build:compiler_executables", default={},
                              check_type=dict) or {}
    cc = compilers.get("c")
    if not cc:
        raise ConanException(
            "tools.build:compiler_executables['c'] is not set; the lpr build "
            "needs the real driver path to generate its link wrapper")
    if not os.path.isfile(cc):
        raise ConanException(
            "tools.build:compiler_executables['c'] = %s does not exist" % cc)
    return cc


class LprConan(ConanFile):
    name = "lpr"
    version = "2008.05.17.4"
    description = ("BSD lpr/lpd line printer spooling system: lpr, lpq, lprm, "
                   "lpc, lpd, lpf, pac, lptest")
    license = "BSD-3-Clause"
    homepage = "https://www.openbsd.org/"
    url = "https://salsa.debian.org/debian/lpr"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        # 纯 CLI 工具包：本包自身没有可切换的构建形态。
        self.options.rm_safe("shared")
        self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lpr requires a POSIX target (Linux or OHOS), got %s"
                % self.settings.os)
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                "lpr 2008.05.17.4 recipe targets aarch64, got %s"
                % self.settings.arch)

    def layout(self):
        # 刻意用默认 src_folder：Conan 2 会把 export_sources() 导出的内容放在缓存的
        # s/ 根目录，只有在 source_folder == export_sources_folder 时 compat/ 才会
        # 落在 self.source_folder/compat（archives/a/abiword-plugin-clarisworks/3.0.8
        # 第 127-128 行记的就是这件事）。改成 src_folder="src" 会让 compat/ 落在
        # s/compat 而源码在 s/src，两者错开。
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)
        # compat/ 是源码文件而不是补丁：toybox 的 patch 在 OHOS 上会把"新建文件"
        # 的补丁也真的打进 orig 目录，污染补丁流水线。导出它，补丁集就只保留
        # "改已有文件"的 diff —— 这里实际是空集（patches: {}，上游零改动）。
        # 写法与 archives/a/abiword-plugin-clarisworks/3.0.8 同型。
        copy(self, "*", src=os.path.join(self.recipe_folder, "compat"),
             dst=os.path.join(self.export_sources_folder, "compat"))

    # ── 构建 ───────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        compat_dir = os.path.join(self.source_folder, "compat")
        for name in ("lpr_ohos_compat.h", "lpr_bsd_compat.c"):
            if not os.path.isfile(os.path.join(compat_dir, name)):
                raise ConanException("compat/%s was not exported" % name)

        cc = _real_cc(self)
        cflags = self._cflags(compat_dir)
        compat_obj = self._build_compat_object(cc, compat_dir, cflags)
        wrapper = self._write_cc_wrapper(cc, compat_obj)

        for subdir in SUBDIRS:
            workdir = os.path.join(self.source_folder, subdir)
            if not os.path.isdir(workdir):
                raise ConanException("upstream subdirectory %s is missing" % subdir)
            # CC / CFLAGS 从命令行给，覆盖子目录 Makefile 里自己的 CFLAGS+=
            # （GNU make 下 ${.CURDIR} 展开为空，见模块 docstring）。
            self.run("make CC=%s CFLAGS=%s" % (shlex.quote(wrapper),
                                               shlex.quote(cflags)),
                     cwd=workdir)

        self._assert_all_programs()

    def _cflags(self, compat_dir):
        """复刻 Debian 在 glibc 上得到的可见性，只补 musl 的缺口。"""
        flags = [
            # GNU make 下 ${.CURDIR} 为空，用绝对路径取代它（见 docstring）。
            "-I" + os.path.join(self.source_folder, "common_source").replace("\\", "/"),
            "-I" + compat_dir.replace("\\", "/"),
            # musl 把 setresuid/setresgid/getifaddrs/freeifaddrs 关在 _GNU_SOURCE 后面。
            "-D_GNU_SOURCE",
            # 照抄 debian/rules 的 DEB_CPPFLAGS_MAINT_APPEND。
            "-D__KAME__",
            # <sys/types.h> + <sys/ttydefaults.h> + 两个 BSD 原型，见 compat 头注释。
            "-include", os.path.join(compat_dir, "lpr_ohos_compat.h").replace("\\", "/"),
            "-O2",
        ]
        return " ".join(flags)

    def _build_compat_object(self, cc, compat_dir, cflags):
        obj = os.path.join(self.build_folder, "lpr_bsd_compat.o")
        # 用与上游完全相同的驱动与旗标编，产物才会和其余对象同 ABI。
        # 去掉 -include：compat/lpr_bsd_compat.c 自己 #include 那个头，
        # 重复强包含虽无害但会让构建日志出现两遍同样的头解析。
        filtered, skip = [], False
        for part in cflags.split():
            if skip:
                skip = False
                continue
            if part == "-include":
                skip = True
                continue
            filtered.append(part)
        cmd = [cc] + filtered + [
            "-c", os.path.join(compat_dir, "lpr_bsd_compat.c"),
            "-o", obj,
        ]
        self.run(" ".join(shlex.quote(part) for part in cmd), cwd=self.build_folder)
        if not os.path.isfile(obj):
            raise ConanException("compat/lpr_bsd_compat.c did not produce %s" % obj)
        self._assert_aarch64(obj, "compat/lpr_bsd_compat.o")
        self.output.info("lpr: compat object built for aarch64 (%d bytes)"
                         % os.path.getsize(obj))
        return obj

    def _write_cc_wrapper(self, cc, compat_obj):
        cases = "\n".join("        %s) exec \"$REAL\" \"$@\" \"$OBJ\" ;;" % name
                          for name in sorted(COMPAT_USERS))
        path = os.path.join(self.build_folder, "cc-ohos-wrap")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(CC_WRAPPER.format(real=cc, obj=compat_obj,
                                           user_cases=cases))
        os.chmod(path, 0o755)
        return path

    def _assert_aarch64(self, path, label):
        with open(path, "rb") as handle:
            head = handle.read(20)
        if head[:4] != b"\x7fELF":
            raise ConanException("%s is not an ELF file" % label)
        if head[4] != 2 or head[5] != 1:
            raise ConanException(
                "%s is not a little-endian ELF64 (EI_CLASS=%d EI_DATA=%d)"
                % (label, head[4], head[5]))
        machine = int.from_bytes(head[18:20], "little")
        if machine != EM_AARCH64:
            raise ConanException(
                "%s targets e_machine=%d, expected %d (EM_AARCH64)"
                % (label, machine, EM_AARCH64))

    def _assert_all_programs(self):
        for program, (subdir, _) in sorted(PROGRAMS.items()):
            path = os.path.join(self.source_folder, subdir, program)
            if not os.path.isfile(path):
                raise ConanException(
                    "make did not produce %s/%s (subdir %s)"
                    % (subdir, program, subdir))
            self._assert_aarch64(path, "%s/%s" % (subdir, program))
        self.output.info("lpr: all %d programs built as aarch64 ELF64"
                         % len(PROGRAMS))

    # ── 打包 ───────────────────────────────────────────────────────────

    def package(self):
        for program, (subdir, destdir) in sorted(PROGRAMS.items()):
            src = os.path.join(self.source_folder, subdir, program)
            dst_dir = os.path.join(self.package_folder, destdir)
            self._mkdir(dst_dir)
            target = os.path.join(dst_dir, program)
            shutil.copy2(src, target)
            # Debian 装成 setuid-root/setgid-daemon（lpr/lpq/lprm 6755 root:daemon，
            # lpc 2755 root:daemon, lpd 755 root:daemon）；包内保持可执行即可，
            # 特权位由部署方按需设置，不在包管理里固定。
            os.chmod(target, 0o755)
            self._verify_compat_symbols(target, program)

        # /etc/printcap 是唯一的运行期配置文件（debian/printcap，Debian 装成
        # conffile；包内样本全部注释掉，不会覆盖真机配置）。
        copy(self, "printcap", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "etc"))
        for section, pages in sorted(MAN_PAGES.items()):
            for page in pages:
                copy(self, os.path.basename(page),
                     src=os.path.join(self.source_folder, os.path.dirname(page)),
                     dst=os.path.join(self.package_folder, "share", "man", section))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

        # 刻意 **不** strip：test_package 要读 .symtab 证明 rresvport_af/innetgr
        # 是已定义符号（st_shndx != SHN_UNDEF）而不是悬空引用。8 个程序合计
        # ~380 KB，保留符号表没有任何代价。
        self._sign_ohos_binaries()

    def _verify_compat_symbols(self, path, program):
        """逐个 ELF 校验 compat 注入范围：引用者必须**已定义**两个符号，
        未引用者必须**根本没有**这两个符号。这样"包装脚本注入范围写错"会在这里
        立刻炸掉，而不是留到真机运行期。"""
        defined, undefined = _elf_symbols(path)
        for symbol in ("rresvport_af", "innetgr"):
            if program in COMPAT_USERS:
                if symbol not in defined:
                    raise ConanException(
                        "%s does not define %s; the link wrapper failed to "
                        "inject the compat object (defined=%s undefined=%s)"
                        % (program, symbol, sorted(defined), sorted(undefined)))
                if symbol in undefined:
                    raise ConanException(
                        "%s still has %s as an undefined symbol: the compat "
                        "object was injected twice" % (program, symbol))
            else:
                if symbol in defined or symbol in undefined:
                    raise ConanException(
                        "%s must not reference %s at all, but the compat object "
                        "was injected into a program outside COMPAT_USERS"
                        % (program, symbol))

    def _mkdir(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)

    def _sign_ohos_binaries(self):
        if str(self.settings.os) != "OHOS":
            return
        signer = (self.conf.get("user.ohos:sign_tool", default="", check_type=str)
                  or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        objcopy = (self.conf.get("user.ohos:objcopy", default="", check_type=str)
                   or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if not os.path.isfile(signer):
            # 与 archives/t/termdebug/2.2 同策略：交叉编译机上没有签名工具时
            # 记一条 warning 继续，绝不因为本地环境缺工具就伪造"已签名"。
            self.output.warning(
                "binary-sign-tool not found; the 8 ELF binaries are shipped "
                "unsigned. The real OHOS device rejects unsigned executables, "
                "so the on-device consumer leg will need a signed package "
                "(CI worker provides /data/service/hnp/bin/binary-sign-tool).")
            return
        for program, (_, destdir) in sorted(PROGRAMS.items()):
            target = os.path.join(self.package_folder, destdir, program)
            if os.path.isfile(objcopy):
                subprocess.run([objcopy, "--remove-section", ".codesign", target],
                               capture_output=True, timeout=60)
            signed = target + ".signed"
            subprocess.run([signer, "sign", "-inFile", target, "-outFile", signed,
                            "-selfSign", "1"], capture_output=True, timeout=120,
                           check=True)
            if not os.path.isfile(signed):
                raise ConanException("binary-sign-tool produced no output for %s"
                                     % program)
            os.replace(signed, target)
            os.chmod(target, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "sbin"))


def _elf_symbols(path):
    """极简 ELF64 符号表读取，返回 (已定义符号名集合, 未定义符号名集合)。

    刻意不依赖 nm/llvm-nm/readelf：OHOS worker 的 HMBS 只注入 cmake/make/ninja/
    python3，这些 binutils 未必存在（archives/t/termdebug/2.2/test_package/
    MANIFEST.yml 有同样记录）。只解析 .symtab/.strtab，不处理压缩/剥离后的
    退化情形 —— 调用方在上游就会因"缺 .symtab"报错，不会静默通过。
    """
    import struct

    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF" or data[4] != 2:
        raise ConanException("%s: not ELF64" % path)
    e_shoff, = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    if e_shoff == 0:
        raise ConanException("%s: no section header table (stripped?)" % path)

    sections = []
    for index in range(e_shnum):
        offset = e_shoff + index * e_shentsize
        (sh_name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link,
         _info, _align, sh_entsize) = struct.unpack_from("<IIQQQQIIQQ", data, offset)
        sections.append({"name": sh_name, "type": sh_type, "offset": sh_offset,
                         "size": sh_size, "link": sh_link, "entsize": sh_entsize})

    def read_name(string_section, index):
        base = sections[string_section]["offset"]
        end = data.index(b"\0", base + index)
        return data[base + index:end].decode("utf-8", "replace")

    section_names = [read_name(e_shstrndx, s["name"]) for s in sections]
    defined, undefined = set(), set()
    symtab = [i for i, name in enumerate(section_names)
              if name in (".symtab", ".dynsym")]
    if not symtab:
        raise ConanException(
            "%s: neither .symtab nor .dynsym present; refusing to guess whether "
            "the BSD compat symbols were linked in" % path)
    for index in symtab:
        sym = sections[index]
        strtab = sections[sym["link"]]
        count = sym["size"] // sym["entsize"] if sym["entsize"] else 0
        for slot in range(count):
            st_name, st_info, _other, st_shndx, _value, _size = struct.unpack_from(
                "<IBBHQQ", data, sym["offset"] + slot * sym["entsize"])
            if st_name == 0:
                continue
            name = read_name(sym["link"], st_name)
            if (st_info & 0xF) not in (0, 1, 2, 10, 13):  # NOTYPE/OBJECT/FUNC/...
                continue
            (undefined if st_shndx == 0 else defined).add(name)
    return defined, undefined
#!/usr/bin/env python3
"""Conan recipe for U-Boot 2026.07 — the universal boot loader.

Two Kbuild targets, both driven by the upstream Makefile:

1. `sandbox_defconfig` — U-Boot built as a **native userspace binary**.
   This is the upstream CI/test vehicle: the C-side unit tests
   (DM_TEST/CMD_TEST/UNIT_TEST — 919 subtests enumerated from the
   u-boot.sym linker-list symbols `_u_boot_list_2_ut_<suite>_2_<name>`,
   the upstream pytest RE_UT_TEST_LIST methodology) run one process per
   subtest (`ut <suite> <name>`; a single-process `ut all` has
   cross-test DM state pollution and upstream never runs it), and the
   host tools (mkimage/dumpimage/fit_info/mkenvimage/fdtgrep) built
   alongside are the real artifacts installed into the package.
2. `qemu_arm64_defconfig` — a real aarch64 firmware image (u-boot.bin),
   built natively with clang on OHOS (upstream doc/build/clang.rst
   procedure); on other build hosts it is attempted only when an
   aarch64 cross gcc is discoverable.

Kconfig's parser is not shipped pre-generated in the release tarball
(scripts/kconfig has only zconf.l/zconf.y, no zconf.tab.c/zconf.lex.c),
so bison+flex regeneration runs during the build; both are provided by
the OHOS toolchain PATH on the supported environments (bison 3.8.2 /
flex 2.6.4 on-device) and probed at build time with a clear failure
message.

License: GPL-2.0-or-later.
"""
import os
import re
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, download
from conan.tools.layout import basic_layout


# OHOS 专用 sdl2-config 包装器源码（编译为同名 ELF；见 _sdl2_config_shim）。
# 真机验证：PATH 命令式调用返回 2.30.10 rc=0；带此后 arch/sandbox/Kconfig
# 探测（$(success,sdl2-config --version)）翻 y → CONFIG_SANDBOX_SDL=y /
# CONFIG_VIDEO_SANDBOX_SDL=y。
_SDL2_CONFIG_SHIM_C = r"""/*
 * sdl2-config ELF wrapper for OHOS (compiled by the recipe, same file name,
 * placed first on PATH).
 *
 * OHOS has no binfmt_script: execve() of a "#!" shell script always fails
 * with EACCES (rc=126), so any *command-form* invocation of the sdl2
 * package's sdl2-config (itself a /bin/sh script) is impossible for the
 * kernel.  Two upstream consumers invoke it exactly that way and cannot be
 * rewritten to a "sh <abs-path>" form (the first is upstream Kconfig text,
 * the second resolves through PATH):
 *
 *   - Kconfig HOST_HAS_SDL probe (arch/sandbox/Kconfig):
 *       def_bool $(success,sdl2-config --version)
 *     expands to popen("/bin/sh -c '{ sdl2-config --version; } ...'") and
 *     the shell PATH-search hits this wrapper's execve - an ELF, which the
 *     kernel does execute.
 *   - arch/sandbox/config.mk:
 *       $(shell $(SDL_CONFIG) --cflags/--libs)
 *     with SDL_CONFIG pinned to this wrapper path.
 *
 * The wrapper re-executes the real script through /bin/sh, which opens the
 * script file itself - no kernel script support needed.  Arguments and exit
 * status are forwarded transparently (execv replaces the process image).
 *
 * Build: clang -O2 -o sdl2-config \
 *            -DSDL2_CONFIG_REAL='"/abs/path/to/real/sdl2-config"' this.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#ifndef SDL2_CONFIG_REAL
#error "compile with -DSDL2_CONFIG_REAL=\"/abs/path/to/real/sdl2-config\""
#endif

int main(int argc, char **argv)
{
    char **nargv = calloc((size_t)argc + 2, sizeof(*nargv));
    int i;

    if (nargv == NULL) {
        perror("calloc");
        return 127;
    }
    nargv[0] = "sh";
    nargv[1] = SDL2_CONFIG_REAL;
    for (i = 1; i < argc; i++)
        nargv[i + 1] = argv[i];
    execv("/bin/sh", nargv);
    perror("sdl2-config-shim: execv /bin/sh");
    return 127;
}
"""


class UbootConan(ConanFile):
    name = "uboot"
    version = "2026.07"
    description = "U-Boot universal boot loader (sandbox test binary + qemu_arm64 firmware + host tools)"
    license = "GPL-2.0-or-later"
    homepage = "https://docs.u-boot.org"
    url = ""  # CI 填充
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(self, "patches/**", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # sandbox 的宿主显示/输入/音频后端库（上游 CI 的 sandbox 即 SDL=y
        # 形态，sandbox_defconfig 字面 VIDEO_SANDBOX_SDL=y）：OHOS 无系统
        # SDL2，直接消费平台制品仓已适配的静态构建；接入方式见 build()
        # 中的三件套（PATH / SDL_CONFIG / KCFLAGS）。
        self.requires("sdl2/2.30.10")

    def validate(self):
        # R32: 显式 allow-list。sandbox 目标在任何 POSIX 构建机可编译，
        # qemu_arm64 固件在 OHOS 上原生构建（CI Linux 仅在交叉 gcc 存在时附带）。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"uboot supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # conan 的 get() 走 tarfile extractall：在 OHOS HMDFS 上归档内
        # symlink 会 EPERM 硬失败中断解包（files.py 无容错）。改为
        # download() + 自定义容错解包：先落地常规文件/目录，再逐个尝试
        # 创建 symlink，EPERM 时把链接物化为目标内容副本（构建只读消费，
        # 语义等价；R5 同源治理：包内零软链）。
        archive = os.path.join(self.source_folder, "u-boot.tar.bz2")
        download(self, **self.conan_data["sources"], filename=archive)
        self._extract_tolerant(archive, self.source_folder)
        os.remove(archive)
        apply_conandata_patches(self)

    # ── 容错解包（HMDFS symlink EPERM） ──────────────────────────────
    def _extract_tolerant(self, archive, dst):
        root = None
        members = []
        with tarfile.open(archive, "r:bz2") as tf:
            for m in tf.getmembers():
                if root is None:
                    root = m.name.split("/")[0] + "/"
                if not m.name.startswith(root) or m.isdir():
                    continue
                members.append(m)
            # pass 1: 常规文件（顺序落盘，保证 pass 2 链接目标已存在）
            for m in members:
                if m.issym() or m.islnk():
                    continue
                target = os.path.join(dst, m.name[len(root):])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with tf.extractfile(m) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                self._restore_mode(target, m.mode)
            # pass 2: symlink 尝试直建，EPERM 物化为副本（文件或目录树）
            for m in members:
                if not (m.issym() or m.islnk()):
                    continue
                target = os.path.join(dst, m.name[len(root):])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                try:
                    if m.issym():
                        os.symlink(m.linkname, target)
                    else:  # hardlink → 副本（跨 fs 与 HMDFS 均安全）
                        self._copy_member_file(tf, m, dst, root, target,
                                               is_hardlink=True)
                except OSError:
                    # HMDFS 全域 EPERM：按链接目标物化
                    self._materialize_link(tf, m, dst, root, target)

    def _resolve_link(self, member, dst, root):
        """把成员链接名解析为解包树内相对路径（归一化）。"""
        link = member.linkname
        if not os.path.isabs(link):
            base = os.path.dirname(os.path.join(dst, member.name[len(root):]))
            return os.path.normpath(os.path.join(base, link))
        return os.path.normpath(os.path.join(dst, link.lstrip("/")))

    @staticmethod
    def _restore_mode(target, tar_mode):
        """落盘文件恢复 tar 成员权限（构建脚本需要 +x，open() 默认 0644）。"""
        try:
            os.chmod(target, tar_mode & 0o777)
        except OSError:
            # 极少数 fs 拒绝 chmod 时保留默认位，由构建失败显性暴露
            pass

    def _copy_member_file(self, tf, member, dst, root, target,
                          is_hardlink=False):
        if is_hardlink:
            # 硬链接目标成员
            link_tgt = os.path.normpath(os.path.join(
                os.path.dirname(member.name), member.linkname))
            for m2 in tf.getmembers():
                if m2.name == link_tgt:
                    member = m2
                    break
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with tf.extractfile(member) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)
        self._restore_mode(target, member.mode)

    def _materialize_link(self, tf, member, dst, root, target, depth=0):
        """EPERM 落盘：把链接物化为目标内容的副本（文件或目录树）。"""
        if depth > 4:
            raise ConanInvalidConfiguration(
                f"uboot source symlink chain too deep at {member.name}")
        resolved = self._resolve_link(member, dst, root)
        rel = os.path.relpath(resolved, dst).replace(os.sep, "/")
        # 链式 symlink：目标本身也是链接 → 递归物化
        for m2 in tf.getmembers():
            if m2.name == root + rel and (m2.issym() or m2.islnk()):
                self._materialize_link(tf, m2, dst, root, target, depth + 1)
                return
        # 目录链接 → 把目标目录整树物化到链接位置
        for m2 in tf.getmembers():
            if m2.name == root + rel and m2.isdir():
                for sub in tf.getmembers():
                    if sub.name.startswith(root + rel + "/") and not sub.isdir():
                        if sub.issym() or sub.islnk():
                            continue  # 子链接由 pass 2 主循环处理
                        sub_tgt = os.path.join(
                            target, sub.name[len(root + rel + "/"):])
                        self._copy_member_file(tf, sub, dst, root, sub_tgt)
                return
        # 文件链接（或已物化的常规文件）→ 复制内容
        if os.path.exists(resolved) and not os.path.islink(resolved):
            shutil.copy2(resolved, target)
            return
        for m2 in tf.getmembers():
            if m2.name == root + rel and not (m2.issym() or m2.islnk()):
                self._copy_member_file(tf, m2, dst, root, target)
                return
        raise ConanInvalidConfiguration(
            f"uboot source symlink target missing: {member.name} -> "
            f"{member.linkname}")

    # ── 构建 ─────────────────────────────────────────────────────────
    def _make(self, out_dir, target, extra="", env=""):
        # 分隔归一：各段 strip 后以空格拼接（extra/target 之间不再隐含
        # 依赖调用方尾空格；make 选项经 target 传入的调用形态保持不变）
        cmd = " ".join(p for p in (env.strip(), f"make O={out_dir}",
                                   extra.strip(), target) if p)
        # R9: 串行构建（真机 make -jN 有静默失败先例）
        self.run(cmd, cwd=self.source_folder)

    def _sdl2_config_shim(self, real_script):
        """OHOS 专用：编译 sdl2-config 同名 ELF 包装器，返回其绝对路径。

        内核只能 execve ELF（无 binfmt_script），而调用方以命令形式调用
        sdl2-config（Kconfig popen 经 /bin/sh 的 PATH 查找、config.mk 的
        $(shell $(SDL_CONFIG) ...)），包装器把调用转成 /bin/sh 打开真脚本
        执行。编译后当场冒烟 --version：问题在构建期暴露，而非等
        syncconfig 把整个 SDL 测试面按 depends 静默收敛。
        """
        shim_dir = os.path.join(self.build_folder, "sdl2-shim")
        os.makedirs(shim_dir, exist_ok=True)
        src = os.path.join(shim_dir, "sdl2-config-shim.c")
        with open(src, "w") as out:
            out.write(_SDL2_CONFIG_SHIM_C)
        shim = os.path.join(shim_dir, "sdl2-config")
        # 宏值需字面双引号：shell 单引号包住（conan 缓存路径不含单引号）。
        # clang 来自 conan buildenv PATH（与后续 make HOSTCC=clang 同源）。
        self.run(f"clang -O2 -o '{shim}' "
                 f"-DSDL2_CONFIG_REAL='\"{real_script}\"' '{src}'")
        self.run(f"'{shim}' --version")
        return shim

    # ── 无密码学库构建配置（决策表第 11 条） ──────────────────────────
    def _disable_crypto_tools(self, out_dir):
        # 只关 host 侧密码学工具（上游文档化「host 工具不链 OpenSSL」开
        # 关）：FIT_SIGNATURE=y 完整保留（固件侧签名校验/UT_LIB_RSA 测
        # 试零损失）。host 代码里 CONFIG_IS_ENABLED(FIT_SIGNATURE) 经
        # include/linux/kconfig.h 的 USE_HOSTCC 重映射解析为
        # CONFIG_TOOLS_FIT_SIGNATURE，而该符号 depends on
        # TOOLS_LIBCRYPTO → 自动回落 n，openssl 头不再被包含（0005/0006/0007
        # 修复上游三处未走重映射的裸引用）。必须同时 -d TOOLS_KWBIMAGE：
        # 该符号 default y 且 select TOOLS_LIBCRYPTO，Kconfig 的 select
        # 无视用户显式关闭，单独 -d TOOLS_LIBCRYPTO 会被 syncconfig 强制
        # 拉回 y（真机 .config 实测复现）。同理 -d TOOLS_MKEFICAPSULE：
        # mkeficapsule.c 无条件 include <gnutls/gnutls.h>（tools/Makefile
        # 仅对链接旗标做 pkg-config 兜底，头文件无兜底），而该符号
        # default y if EFI_LOADER（sandbox_defconfig 显式 EFI_LOADER=y），
        # 设备无 gnutls 开发头 → host 编译必炸；qemu_arm64_defconfig 无
        # EFI_LOADER 本就不开，-d 是无害 no-op。目标侧
        # EFI_CAPSULE_AUTHENTICATE=y 完整保留（sandbox ut efi 自跑在固件
        # 内、不依赖 host 工具，测试零损失）。不跑 olddefconfig：
        # TOOLS_LIBCRYPTO 是 default y，重跑会把它打回 y；make 启动时
        # conf --syncconfig 会按 depends 自动收敛 TOOLS_FIT_SIGNATURE*。
        cfg = os.path.join(out_dir, ".config")
        self.run("bash scripts/config --file " + cfg +
                 " -d TOOLS_KWBIMAGE -d TOOLS_LIBCRYPTO -d TOOLS_MKEFICAPSULE",
                 cwd=self.source_folder)

    def build(self):
        # Kconfig 解析器不随发行包提供预生成版（scripts/kconfig 只有
        # zconf.l/zconf.y，无 zconf.tab.c/zconf.lex.c），构建期由
        # bison/flex 再生成
        for tool in ("bison", "flex"):
            if not shutil.which(tool):
                raise ConanInvalidConfiguration(
                    f"uboot Kconfig requires {tool} on PATH (OHOS toolchain "
                    f"provides it); not found")
        sb = os.path.join(self.build_folder, "sandbox")
        qm = os.path.join(self.build_folder, "qemu")
        # 上游 doc/build/clang.rst 官方姿势：显式 HOSTCC=clang CC=clang
        # （2026.07 已移除 LLVM=1 伞开关，Makefile 里 grep 不到 LLVM 处理；
        # HOSTCC 默认 cc，设备上无 cc 二进制，必须显式传入）
        # NO_PYTHON=1：上游文档化的「构建环境无法构建 Python 工具」模式。
        # pylibfdt/binman 依赖 SWIG+setuptools（OHOS python 环境两者皆无，
        # SWIG 无法 pip 提供）；sandbox.dts 的 binman 节点为空（no-op），
        # 跳过不改动任何产物（配 0003 给 .binman_stamp 加 PYTHON_ENABLE 门）。
        # CONFIG_SHELL=bash：u-boot Makefile 硬编码 CONFIG_SHELL:=sh，而
        # scripts/check-local-export 是 bash 脚本（shopt），设备 /bin/sh
        # 无 shopt（实测 "shopt: inaccessible or not found"）、/bin/bash
        # 不存在；bash 位于 /data/service/hnp/bin/bash（PATH 可达，Kbuild
        # 标准覆盖位）。配 0002 给 cmd_check_local_export 补 $(CONFIG_SHELL)
        # 前缀（上游裸 exec，OHOS 无 binfmt_script 直接 exec 必 EACCES
        # rc=126，真机 arch/sandbox/cpu/start.o 实测）。
        native = "HOSTCC=clang CC=clang NO_PYTHON=1 CONFIG_SHELL=bash "
        if self.settings.os == "OHOS":
            # LTO 链接走 lld：CONFIG_LTO 经 arch/Kconfig `imply LTO` 在
            # sandbox 默认开启（qemu_arm64 无 LTO，该旗标为无害 no-op）；
            # clang -flto + GNU ld 需要 LLVMgold 插件（设备无，实测），
            # ld.lld 在工具链 PATH（实测）。LTO_FINAL_LDFLAGS 是命令行
            # 覆盖位：Makefile 内 := 置空后 += -flto 会附加到命令行值，
            # 最终 -fuse-ld=lld -flto。仅链接 cmd_u-boot__ 使用该变量。
            native += "LTO_FINAL_LDFLAGS=-fuse-ld=lld "
        # sandbox 的 SDL2 接线（对齐上游 SDL=y 的 sandbox 配置）：Kconfig
        # 以 sdl2-config 可用性判定 HOST_HAS_SDL → SANDBOX_SDL →
        # VIDEO_SANDBOX_SDL（defconfig 字面 =y；探测失败会被 syncconfig
        # 按 depends 静默收敛，video/cedit/expo 整片测试面随之消失，故
        # 探测各阶段都须命中依赖包），arch/sandbox/config.mk 亦以同名
        # 工具取 --cflags/--libs 接入链接。三件套：
        #  * PATH 前置 sdl2 包 bin/（OHOS 上为下述包装器目录）：Kconfig
        #    $(success,) 探测与 config.mk 的 SDL_CONFIG ?= sdl2-config
        #    默认解析都命中；
        #  * SDL_CONFIG 显式钉扎同一工具（脚本自定位 prefix，不依赖安装
        #    前缀；OHOS 上钉扎包装器，见下）；
        #  * KCFLAGS 补 -I<pkg>/include：sdl2-config --cflags 只回
        #    -I<prefix>/include/SDL2，而源码按 <SDL2/SDL.h> 引用（上游
        #    指望 /usr/include 是默认搜索路径）。顶层 Makefile 把 KCFLAGS
        #    并入 KBUILD_CFLAGS，syshdrs 文件经 -idirafter 等效落地。
        sdl2_pkg = self.dependencies["sdl2"].package_folder
        sdl2_bin = os.path.join(sdl2_pkg, "bin")
        sdl2_conf = os.path.join(sdl2_bin, "sdl2-config")
        if self.settings.os == "OHOS":
            # 制品仓 sdl2-config 是 sh 脚本，而 OHOS 无 binfmt_script：
            # 脚本 execve 恒 EACCES rc=126（真机实测）。上面两处对该
            # 脚本的调用都是「命令」形式——Kconfig 探测经 popen 走
            # /bin/sh 的 PATH 查找、config.mk 走 $(shell sdl2-config
            # ...)——内核必须直接 execve 脚本本体，必败且无声（探测恒
            # n → SANDBOX_SDL 被 syncconfig 收敛；链接旗标为空）。两处
            # 都是上游文字（Kconfig 行 / Makefile 默认值），不能改写为
            # sh <全路径> 形式（真机实测 busybox sh 对 <script> 操作数
            # 不做 PATH 查找，sh sdl2-config 亦败）。解法=同名 ELF 包装器
            # 置 PATH 前位：内核可执行 ELF，包装器 execv("/bin/sh",
            # ["sh", <真脚本全路径>, ...]) 由 sh 打开脚本执行，参数与
            # 退出码透明转发（源码 _SDL2_CONFIG_SHIM_C）。
            sdl2_conf = self._sdl2_config_shim(sdl2_conf)
            sdl2_bin = os.path.dirname(sdl2_conf)
        sdl_env = (
            f'PATH="{sdl2_bin}:$PATH" '
            f'SDL_CONFIG="{sdl2_conf}" '
            f'KCFLAGS="-I{os.path.join(sdl2_pkg, "include")}" '
        )
        self._make(sb, "sandbox_defconfig", extra=native, env=sdl_env)
        self._disable_crypto_tools(sb)
        self._make(sb, "-j1", extra=native, env=sdl_env)
        if self.settings.os == "OHOS":
            # qemu_arm64 原生 aarch64（ld/as/objcopy 等由工具链 PATH 提供）
            self._make(qm, "qemu_arm64_defconfig", extra=native)
            self._disable_crypto_tools(qm)
            self._make(qm, "-j1", extra=native)
        else:
            # CI Linux 构建机：sandbox 用本机 clang 原生构建；
            # qemu_arm64 仅在有 aarch64 交叉 gcc 时构建（否则跳过并告警）
            cross = shutil.which("aarch64-linux-gnu-gcc")
            if cross:
                x = f"HOSTCC=clang CROSS_COMPILE=aarch64-linux-gnu- NO_PYTHON=1 CONFIG_SHELL=bash "
                self._make(qm, "qemu_arm64_defconfig", extra=x)
                self._disable_crypto_tools(qm)
                self._make(qm, "-j1", extra=x)
            else:
                self.output.warning(
                    "no aarch64-linux-gnu-gcc on build machine; qemu_arm64 "
                    "firmware skipped here (built natively on OHOS)")

    def test(self):
        if not can_run(self):
            return
        sb = os.path.join(self.build_folder, "sandbox")
        # 轻量冒烟（全量 919 子测试逐进程口径由 test_package 执行）：版本 + lib 套件
        self.run(f'{os.path.join(sb, "u-boot")} -c "version; ut lib; exit"')

    # ── 打包 ─────────────────────────────────────────────────────────
    def package(self):
        sb = os.path.join(self.build_folder, "sandbox")
        qm = os.path.join(self.build_folder, "qemu")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # host 工具（consumer 可直接执行）
        for tool in ("mkimage", "dumpimage", "fit_info", "mkenvimage",
                     "fdtgrep"):
            copy(self, tool, src=os.path.join(sb, "tools"), dst=bin_dir)
        # sandbox 本体：带后缀落盘，保留 -c 命令接口
        shutil.copy2(os.path.join(sb, "u-boot"),
                     os.path.join(bin_dir, "u-boot-sandbox"))
        # sandbox 运行期资源：OF_LIVE 组单元测试（dm_test_ofnode_*_ot、
        # dm_test_livetree_ensure）经 state_load_other_fdt() →
        # state_get_rel_filename()（arch/sandbox/cpu/state.c:402）按
        # argv[0] 所在目录相对解析 "<dir(argv0)>/arch/sandbox/dts/other.dtb"
        # ——上游构建树内二进制（build/sandbox/u-boot）的天然相对布局。
        # 包内二进制位于 bin/ 下，在同一目录镜像该相对结构，消费方以
        # 任意路径调用 bin/u-boot-sandbox 时解析均成立。
        other_dst = os.path.join(bin_dir, "arch", "sandbox", "dts")
        os.makedirs(other_dst, exist_ok=True)
        shutil.copy2(
            os.path.join(sb, "arch", "sandbox", "dts", "other.dtb"),
            os.path.join(other_dst, "other.dtb"))
        # arm64 固件（OHOS 原生构建时存在；非 ELF 可执行镜像放 firmware/）
        fw_dir = os.path.join(self.package_folder, "firmware")
        if os.path.isfile(os.path.join(qm, "u-boot.bin")):
            os.makedirs(fw_dir, exist_ok=True)
            shutil.copy2(os.path.join(qm, "u-boot.bin"),
                         os.path.join(fw_dir, "u-boot-qemu_arm64.bin"))
        # 许可证
        copy(self, "Licenses/gpl-2.0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 测试资产（test_package 的 bootstd E2E 夹具 + 全量 ut 子测试）：
        # test.dtb 驱动 sandbox 设备树、testapp.efi 是 EFI 夹具里的
        # BOOTSBOX.EFI；ut 子测试清单在打包时从 u-boot.sym 的链接器列表
        # 符号（与上游 pytest conftest RE_UT_TEST_LIST 同一正则）生成
        # pairs.txt，测试期不再依赖体积庞大的 .sym 文件。
        test_dir = os.path.join(self.package_folder, "test")
        os.makedirs(test_dir, exist_ok=True)
        shutil.copy2(os.path.join(sb, "arch", "sandbox", "dts", "test.dtb"),
                     os.path.join(test_dir, "test.dtb"))
        shutil.copy2(os.path.join(sb, "lib", "efi_loader", "testapp.efi"),
                     os.path.join(test_dir, "testapp.efi"))
        _ut_list_re = re.compile(
            r"_u_boot_list_2_ut_[a-zA-Z0-9_]+_2_[a-zA-Z0-9_]+$")
        pairs = set()
        with open(os.path.join(sb, "u-boot.sym"), errors="ignore") as sym:
            for line in sym:
                m = _ut_list_re.search(line.rstrip())
                if m:
                    s = m.group(0)[len("_u_boot_list_2_ut_"):]
                    if not s.endswith("_norun"):
                        pairs.add(s)
        with open(os.path.join(test_dir, "pairs.txt"), "w") as out:
            for s in sorted(pairs):
                out.write(s + "\n")
        self.output.info(f"ut subtest list: {len(pairs)} pairs")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # test_package 经 conanrun 环境消费的测试资产路径
        self.runenv_info.define(
            "U_BOOT_SANDBOX",
            os.path.join(self.package_folder, "bin", "u-boot-sandbox"))
        self.runenv_info.define(
            "U_BOOT_MKIMAGE",
            os.path.join(self.package_folder, "bin", "mkimage"))
        self.runenv_info.define(
            "U_BOOT_UT_DTB",
            os.path.join(self.package_folder, "test", "test.dtb"))
        self.runenv_info.define(
            "U_BOOT_UT_TESTAPP",
            os.path.join(self.package_folder, "test", "testapp.efi"))
        self.runenv_info.define(
            "U_BOOT_UT_PAIRS",
            os.path.join(self.package_folder, "test", "pairs.txt"))

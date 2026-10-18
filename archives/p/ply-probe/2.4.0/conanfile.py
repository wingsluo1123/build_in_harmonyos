#!/usr/bin/env python3
"""Conan recipe for ply-probe 2.4.0 — eBPF/kprobe 动态追踪前端（上游 iovisor/ply）。

【知识库扩展载体】本包除配方外，同时承载「OHOS 无 Linux 内核追踪接口」这一平台共性缺口的
检测与记录能力（内核追踪特性 bpf/kprobe/perf_event/tracefs 此前在知识库中零覆盖）：
  · 知识条目草稿 knowledge/drafts/E545-draft-44F3.kv
    （prescan_pattern → PreScanner 运行时派生 PSCAN-KB-E545 规则）
  · 平台能力实测与复现：2.4.0/reports/{ohos-kernel-tracing-probe.c,repro-kernel-tracing.sh,probe-output.log}

平台限制（HarmonyOS PC aarch64 实测，证据见 reports/probe-output.log）:
  bpf()             → SIGSYS（信号 31，进程被直接终止，exit 159；不是 ENOSYS）
  perf_event_open() → EACCES
  /proc/kallsyms    → 地址被 kptr_restrict 抹零
  ⇒ 产物可编译安装，但除 `ply -v` / `ply -h` 外无可用功能路径：
     kprobe 脚本编译期即需 kallsyms（受限 → rc=1 静默失败），tracepoint 脚本需 tracefs
     （缺失 → 解析失败），探针加载需 bpf()（SIGSYS）。本配方不做 stub 伪造（R8），
     平台边界如实记录于 notes.md 与知识条目 E545。

引导链处置（详见 notes.md「平台适配」节）：
  0001 固定 AC_INIT 版本号（上游取自 git describe，tarball 内无 .git）——conandata 声明，
       build() 起始统一应用；
  0002/0003 修 config.guess/config.sub（由 libtoolize/automake 注入的版本不识别 HarmonyOS，
       E007），必须在 automake --add-missing 之后应用，故不列入 conandata（否则应用时
       目标文件尚不存在），改在 _autogen() 末尾执行；
  mktemp 临时目录修（E114）——configure 由本配方现场生成，无法用静态补丁，生成后就地替换。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get, patch,
                               replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# autotools 生成链所需的构建工具（由 tool_requires 提供）
_TOOL_DEPS = ("automake", "libtool", "flex", "bison")

# 需在 libtoolize/automake 落地 aux 脚本之后就地应用的补丁（OHOS config.guess/config.sub）
_POST_LIBTOOLIZE_PATCHES = (
    "0002-config-guess-harmonyos.patch",
    "0003-config-sub-ohos.patch",
)


class PlyProbeConan(ConanFile):
    name = "ply-probe"
    version = "2.4.0"
    description = ("ply — eBPF 动态追踪前端（上游 iovisor/ply）。"
                   "OHOS 适配：产物可安装可执行（ply -v / ply -h、脚本解析器）；"
                   "运行期内核追踪不可用（bpf() → SIGSYS，见 notes.md / 知识条目 E545）")
    license = "GPL-2.0-only"
    homepage = "https://github.com/iovisor/ply"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # configure.ac 需要 AC_PROG_LEX/AC_PROG_YACC（flex/bison），并用 libtool 产出共享库；
        # CI 无系统级 automake/libtool/flex/bison（abiword-plugin-*、captagent/6.4.4 同款 pin）
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _tool_bin_dirs(self):
        """tool_requires 工具包的 bin 目录（显式前置到 PATH）。

        CI/本机 PATH 上的同名系统工具可能缺失或不可执行，裸调用会命中错误的可执行文件；
        从构建依赖的 package_folder 取真实路径，保证用的是 tool_requires 提供的工具链。
        """
        dirs = []
        for name in _TOOL_DEPS:
            dep = self.dependencies.build.get(name)
            if dep is None or not dep.package_folder:
                continue
            for bindir in (dep.cpp_info.bindirs or ["bin"]):
                path = os.path.join(dep.package_folder, bindir)
                if os.path.isdir(path):
                    dirs.append(path)
        return dirs

    def _patch_config_guess(self):
        """修 config.guess/config.sub，使其识别 HarmonyOS（E007）。

        上游不随源码发布这两个脚本：libtoolize --automake 会延后 aux 脚本安装，
        实际由 `automake --add-missing` 落地，故补丁必须在生成链末尾、configure 运行前应用。
        打完后 configure 正确得到 aarch64-unknown-linux-ohos，无需 --build/--host 绕过
        （绕过会把 configure 误判为交叉编译，跳过 AC_RUN_IFELSE 等运行时检测）。
        """
        for fname in ("config.guess", "config.sub"):
            if not os.path.exists(os.path.join(self.source_folder, fname)):
                raise ConanException(
                    "{} 缺失：automake --add-missing 未安装 aux 脚本，生成链顺序异常".format(fname))
        for name in _POST_LIBTOOLIZE_PATCHES:
            patch(self, base_path=self.source_folder,
                  patch_file=os.path.join(self.export_sources_folder, "patches", name),
                  strip=1)

    def _fix_config_tmpdir(self):
        """E114：OHOS 下 `mktemp -d ./confXXXXXX` 建出的目录不可写（drwx--S---）。

        config.status 往里写 subs1.awk 时报 "Permission denied"，configure 最终以
        "could not setup config files machinery" 失败。configure 是本配方用 autoconf
        现场生成的（上游不发布），静态补丁不适用，故就地禁用 mktemp 分支，强制走
        autoconf 自带的 `mkdir` 回退路径。config.status 由 configure 输出，改 configure
        即同时修好 config.status（与 ocp/abiword 系列同一处理）。
        """
        replace_in_file(
            self, os.path.join(self.source_folder, "configure"),
            '(umask 077 && mktemp -d "./confXXXXXX")',
            '(umask 077 && false)')

    def _autogen(self):
        """上游不预生成 configure（autogen.sh = autoreconf -W portability -visfm）。

        按 autoconf 生成链逐步执行并校验产物，避免 autoreconf 在受限文件系统下的 m4 缓存问题。
        """
        dirs = self._tool_bin_dirs()
        prefix = 'PATH="{}:$PATH" '.format(":".join(dirs)) if dirs else ""

        def run_step(cmd, artifact):
            self.run(prefix + cmd, cwd=self.source_folder, env="conanbuild")
            if artifact and not os.path.exists(os.path.join(self.source_folder, artifact)):
                raise ConanException(
                    "autotools 引导失败：'{}' 未生成 {}".format(cmd, artifact))

        # configure.ac 声明 AC_CONFIG_MACRO_DIRS(m4)：先备好目录，再由 libtoolize 灌入
        # ltmain.sh / m4/libtool.m4 —— 之后 aclocal 才能解析 LT_INIT。
        run_step("mkdir -p m4", None)
        run_step("libtoolize --force --copy --automake", "ltmain.sh")
        run_step("aclocal --force -I m4", "aclocal.m4")
        run_step("autoconf -o configure configure.ac", "configure")
        self._fix_config_tmpdir()
        run_step("autoheader", "config.h.in")
        run_step("automake --add-missing --copy --foreign", "Makefile.in")
        # config.guess/config.sub 由上面的 automake 落地 → OHOS 补丁须在此之后应用（E007）
        self._patch_config_guess()

    def build(self):
        apply_conandata_patches(self)
        self._autogen()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        """ply 是命令行工具：主体产物为 bin/ply（BPF 动态追踪前端）。

        libply（共享库）随包发布，bin/ply 依赖它；同时导出 include/ply/*.h 供二次开发。
        OHOS 上内核追踪后端缺失（bpf()/perf_event_open()/kallsyms/tracefs 均不可用，
        见 notes.md 与知识条目 E545），但产物本身可正常安装与执行（ply -v / ply -h）。
        """
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["ply"]
        self.cpp_info.includedirs = ["include"]

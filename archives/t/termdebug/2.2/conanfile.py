#!/usr/bin/env python3
"""Conan recipe — termdebug 2.2（Tilde Terminal Toolkit 的终端录制/回放工具集）。

上游 https://os.ghalkes.nl/termdebug.html（作者 G.P. Halkes），唯一官方发行渠道是
``https://os.ghalkes.nl/dist/termdebug-2.2.tar.bz2``（HTTP 200，sha256 见
conandata.yml）。该 tarball 未进 Debian 之外的任何上游 git 仓库，故按官方归档取源。

构建系统：**自研 configure**（Tilde Terminal Toolkit 的 config.pkg 框架）。tarball 里
只有生成好的 ``configure`` + ``Makefile.in``，没有 ``configure.ac``/``Makefile.am``。
``configure`` 用 sed 把 ``Makefile.in`` 变成 ``Makefile``，并在探测阶段把依赖结论写进
``CONFIGFLAGS`` / ``CONFIGLIBS`` / ``OPTOBJECTS``（见 config.pkg 的 ``config()``）。

就地表构建（不是补丁）
----------------------
``configure``、``Makefile.in``、``config.pkg`` 三者用**相对路径**互相引用
（``cat Makefile.in | sed -f .sedscript > Makefile``、``clean ${EXT}.config``），只能在
源码根目录就地运行。Conan 的 build folder 与 source folder 是两个目录，所以配方在
``self.source_folder`` 里跑 configure + make —— 与 archives/m/magicrescue/1.1.10 同一
处理（knowledge/DRAFT-magicrescue-1.1.10-custom-configure-source-root-cwd.md）。

依赖探测顺序与我们的适配点
--------------------------
configure 依次探测（任一失败就降级并**静默砍功能**）：

1. ``tinfo`` / ``ncurses`` 的 pkg-config，再退到 ``-ltinfo`` / ``-lcurses`` / ``-lncurses``
2. libunistring（``-lunistring``）
3. ``cairo`` 的 pkg-config
4. ``pangocairo`` 的 pkg-config
5. iconv
6. pthread（``-pthread``）

降级不报错，所以**必须在配方里主动核验**：任一项缺失都意味着 visual compare / 图片
输出被砍掉，而构建日志只有一行 ``Warning: compiling without ...``。配方因此
(a) 把 Conan 依赖的 ``-I``/``-L``/``-D`` 显式导出给 configure 与 make，(b) 自己补出
configure 找不到的两个 .pc（见 ``generate()``），(c) 构建后逐一断言五个可选目标文件
都产出了 —— 少一个就抛异常，绝不把降级包当成功交付。

OHOS 适配（均为**构建环境**适配，上游源码零改动、无补丁）
----------------------------------------------------------
1. ``CFLAGS`` 被 sed 整行替换（``sed_rules_c`` → ``replace_default CFLAGS``），上游默认
   的 ``-O2 -Isrc`` 会消失。配方导出 ``<依赖 -I/-D> -O2 -Isrc``，保持等价的优化级别和
   ``src/`` 相对包含路径。
2. ``-lutil``：musl OHOS 把 openpty/forkpty/login_tty 收进 libc。configure 只在
   ``TESTLIBS=-lutil`` 探测成功时才追加该库，探测失败自动走 ``posix_openpt``/``/dev/ptmx``
   回退，不需要干预。
3. 链接器用 OHOS SDK clang（target ``aarch64-linux-ohos``），Conan 依赖给的 ``-L`` 走
   静态 ncursesw（formw/menuw/panelw 顺序由 ncurses/6.6 的 ``cpp_info.libs`` 保证
   “消费者在前、核心在后”），cairo/pango 是 shared。
4. 真机 HMDFS 拒绝执行未签名 ELF（cronutils 首轮 ``PermissionError: [Errno 13]``），
   ``package()`` 对最终 ``bin/termdebug`` 做 ``llvm-objcopy --remove-section .codesign``
   + ``binary-sign-tool -selfSign 1``。
5. 5 个命令是同一 ELF 的 argv[0] symlink（``src/common.c`` 的 ``main()`` 按
   ``basename(argv[0])`` 分派），签名一个即可；install target 用 ``cd $(DESTDIR)$(prefix)/bin
   && ln -s`` 建软链，装出来天然正确。
6. 真机无系统 pkg-config（HMBS 只注入 cmake/make/ninja/python3），配方
   ``tool_requires("pkgconf/3.0.5")``（pango/1.58.2 同款实证），并在 ``build()`` 里做
   ``--version`` 握手后落一个同名 shim 钉进 PATH。

cairo 的使用范围（R40 说明）
---------------------------
本包**不是**图形应用：cairo/pangocairo 只用来把录制差异**离屏**渲染成 PNG
（``src/write_image.c`` 走 ``cairo_image_surface_create`` + ``pango_cairo_create_layout`` +
``cairo_surface_write_to_png``），不涉及 EGL / GLES / Vulkan / X11 / Wayland 窗口系统，
也不碰 GPU。因此不存在"stub 掉渲染接口骗过编译"的空间：能力缺失时上游 configure 会
直接砍掉 ``src/write_image.o``，而配方在 ``_require_full_feature_set()`` 里硬断言该
``.o`` 必须存在、test_package 又断言 ``cairo_surface_write_to_png`` /
``pango_cairo_create_layout`` 符号在最终 ELF 里。真机上 ``tdreplay -p`` / ``tdcompare -p``
的实际出图由 CI 的运行段（--help 能力探针）覆盖。

上游测试
--------
``Makefile`` 只有 ``all`` / ``clean`` / ``dist-clean`` / ``install``，**没有任何测试目标**，
上游也不带 tests/ 目录 —— 因此 L1 上游测试按 ci/config/no_official_test.txt 的白名单
豁免，不用 test_package 冒充"上游测试通过"。真实覆盖由 test_package 的消费者断言承担
（其中 4 条直接验的就是上面那套条件编译功能：``tdreplay --help`` 里出现
``--visual-compare`` / ``--picture=`` / ``--picture-series=`` 分别对应 curses+libunistring /
cairo / cairo+pthreads）。
"""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout

# configure 的 5 个可选能力对应的目标文件（config.pkg 的 OPTOBJECTS）。
# 少任何一个 = 功能被静默降级，构建必须失败而不是交付残包。
OPTIONAL_OBJECTS = {
    "curses": "src/curses_handling.o",
    "libunistring": "src/window.o",
    "unistring-stringlist": "src/write_stringlist.o",
    "cairo-image": "src/write_image.o",
    "pthreads-picture-series": "src/picture_queue.o",
}

# 5 个 argv[0] symlink → man page（上游 install target 与 man/*.1 的对应关系）
COMMAND_MAN_PAGES = {
    "tdrecord": "tdrecord.1",
    "tdreplay": "tdreplay.1",
    "tdrerecord": "tdrerecord.1",
    "tdview": "tdview.1",
    "tdcompare": "tdcompare.1",
}

# 上游包内自带的一个 2013 年的 x86-64 预编译残留文件（不是构建产物，不参与 Makefile）
STRAY_TARBALL_BINARY = os.path.join("src", "tdcompare")


class TermdebugConan(ConanFile):
    name = "termdebug"
    version = "2.2"
    description = ("Tools for recording and replaying the input and output of "
                   "terminal programs (tdrecord/tdreplay/tdview/tdrerecord/tdcompare)")
    license = "GPL-3.0-only"
    homepage = "https://os.ghalkes.nl/termdebug.html"
    url = "https://os.ghalkes.nl/dist/termdebug-2.2.tar.bz2"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        # 纯 CLI 工具包：本包自身没有可切换的构建形态。
        self.options.rm_safe("shared")
        self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"termdebug requires a POSIX target (Linux or OHOS), got {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                f"termdebug 2.2 recipe targets aarch64, got {self.settings.arch}")

    def requirements(self):
        # 版本钉死：这几个组合是 ohpcd 里同时存在 OHOS armv8 Release 二进制的组合。
        # cairo 必须钉 1.18.4.2 —— pango/1.58.2 要求 cairo/1.18.Z，范围解析会落到
        # ohpcd 上最新的 1.18.4.2，钉 1.18.4 会直接版本冲突。
        # R26（ncurses 与系统库同名 → 必须静态）：不在这里写
        # default_options {"ncurses/*": {"shared": False}}，因为 ncurses/6.6 的配方
        # 根本没有 options（连 config_options 都没有），写 pattern 会在 Conan 初始化
        # options 阶段直接抛 "'function' object has no attribute 'items'"。改由依赖包
        # 自身保证 —— 实测该 OHOS 包就是 shared=False 的 static-only 包，
        # conan list 显示 ncurses/6.6#3dcfd3b6...:21b17f8b... 的 options 为
        # {fPIC: True, shared: False}，静态链接顺序由其 cpp_info.libs 保证。
        # cairo / pango 不在此列：非系统库，且 pango/1.58.2 要求 cairo shared=True。
        self.requires("ncurses/6.6")
        self.requires("libunistring/1.0")
        self.requires("cairo/1.18.4.2")
        self.requires("pango/1.58.2")

    def build_requirements(self):
        # 真机没有系统 pkg-config（HMBS 只注入 cmake/make/ninja/python3），仓内
        # pkgconf 只装 bin/pkgconf。pango/1.58.2 用同一招做 _ensure_pkg_config_shim。
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        # src_folder="src" 只是给 Conan 一个独立的源码目录名；真正的构建目录由
        # configure/Makefile 自己决定（就地构建，见模块 docstring）。
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # conandata.yml 的 patches 段为空：上游源码零改动。
        apply_conandata_patches(self)

    # ── 生成 .pc 与构建环境 ─────────────────────────────────────────────

    def generate(self):
        PkgConfigDeps(self).generate()

        # configure 只认 `tinfo` / `ncurses` 和 `cairo` / `pangocairo` 四个包名，而
        # 上游依赖配方声明的 pkg_config_name 分别是 ncursesw / cairo / pango。
        #
        # ncurses / cairo 必须写成**自包含** .pc（直接给出 -L/-I/-l）：termdebug 的
        # configure 用 `pkg-config --libs <x>` 的结果做「能否链接」探测，而仅靠
        # `Requires:` 转发的 .pc 在 OHOS 构建机上解析出的链接行不稳定（实测
        # `ncurses pkg-config compile` 与 `cairo` 探测都失败 → 静默砍掉 curses /
        # cairo）。自包含写法把依赖包真实的 libdir / includedir / libs 直接写进 .pc，
        # 链接探测与最终产物链接都稳。顺序由 cpp_info.libs 保证。
        self._write_self_contained_pc("ncurses", "ncurses")
        self._write_self_contained_pc("cairo", "cairo")
        # pangocairo：上游 configure 找 `pangocairo`，依赖包只提供 `pango`（pkg_config_name）。
        # pango 有原生 .pc，cairo 已被上面的自包含 .pc 覆盖，转发成 `Requires: pango cairo` 即可。
        self._write_forwarding_pc("pangocairo", "pango cairo")

        self._compose_build_env(VirtualBuildEnv(self)).vars(self).save_script(
            "conanbuild-termdebug")

    @staticmethod
    def _pc_paths(dep):
        """取依赖包真实的 libdir / includedir / libs / version，用于写自包含 .pc。"""
        cpp = dep.cpp_info.aggregated_components()
        libdirs = [os.path.join(dep.package_folder, d) for d in (cpp.libdirs or ["lib"])]
        incdirs = [os.path.join(dep.package_folder, d) for d in (cpp.includedirs or ["include"])]
        return libdirs, incdirs, (cpp.libs or []), str(dep.ref.version)

    def _write_self_contained_pc(self, alias, dep_name):
        dep = self.dependencies.host.get(dep_name)
        if dep is None:
            raise ConanException(
                f"termdebug requires {dep_name} to generate the {alias}.pc stub, "
                f"but it is not a (host) dependency")
        libdirs, incdirs, libs, version = self._pc_paths(dep)
        if not libs:
            raise ConanException(
                f"{dep_name} cpp_info.libs is empty; cannot build {alias}.pc")
        libdir = libdirs[0]
        incdir = incdirs[0]
        stub = os.path.join(self.generators_folder, alias + ".pc")
        with open(stub, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("prefix=%s\n" % dep.package_folder)
            handle.write("libdir=%s\n" % libdir)
            handle.write("includedir=%s\n" % incdir)
            handle.write("Name: %s\n" % alias)
            handle.write("Description: self-contained .pc generated by the termdebug "
                         "recipe for upstream configure (wide-char ncurses)\n")
            handle.write("Version: %s\n" % version)
            handle.write("Libs: -L${libdir} -l%s\n" % " -l".join(libs))
            handle.write("Cflags: -I${includedir}\n")
        self.output.info("termdebug: generated %s.pc -> Libs: -L%s -l%s"
                         % (alias, libdir, " -l".join(libs)))

    def _write_forwarding_pc(self, alias, targets):
        # targets: 空格分隔的 pkg-config 包名（如 "pango cairo"）
        missing = []
        for t in targets.split():
            if not os.path.isfile(os.path.join(self.generators_folder, t + ".pc")):
                missing.append(t)
        if missing:
            raise ConanException(
                f"PkgConfigDeps did not generate {', '.join(missing)}.pc; cannot "
                f"build the {alias}.pc forwarding stub that upstream configure looks for")
        version = "0"
        for t in targets.split():
            with open(os.path.join(self.generators_folder, t + ".pc"), encoding="utf-8") as h:
                for line in h:
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
        stub = os.path.join(self.generators_folder, alias + ".pc")
        with open(stub, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("Name: %s\n"
                         "Description: forwarding .pc generated by the termdebug "
                         "recipe for upstream configure\n"
                         "Version: %s\n"
                         "Requires: %s\n" % (alias, version, targets))
        self.output.info("termdebug: generated %s.pc -> Requires: %s" % (alias, targets))

    def _dependency_flags(self):
        """从依赖图聚合 -I/-D/-L（Conan 的 VirtualBuildEnv 在 build context 只带
        build_requires 的 buildenv_info，**不会**把 host 依赖的 cpp_info 变成
        CC/CFLAGS/LDFLAGS —— 这正是必须自己算的原因）。"""
        includedirs, libdirs, defines = [], [], []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info.aggregated_components()
            for item in cpp.includedirs or []:
                includedirs.append(os.path.join(dep.package_folder, item))
            for item in cpp.libdirs or []:
                libdirs.append(os.path.join(dep.package_folder, item))
            for item in cpp.defines or []:
                defines.append(item)

        def unique(items):
            seen, out = set(), []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        return unique(includedirs), unique(libdirs), unique(defines)

    def _compose_build_env(self, build_env):
        """在 VirtualBuildEnv 的基础上补上依赖 flags（它本身不带 host 依赖的
        cpp_info，见 _dependency_flags 的说明）。返回 Environment 对象。"""
        env = build_env.environment()
        includedirs, libdirs, defines = self._dependency_flags()
        # -O2 -Isrc：sed_rules_c 的 replace_default 会把 Makefile.in 里的整行
        # `CFLAGS=-O2 -Isrc` 换成我们的值，所以这两个必须自己补回去。
        # -DHAVE_PTHREAD：上游 config.pkg 在这里漏了宏。它对 curses/unistring/cairo 都写了
        # `CONFIGFLAGS="${CONFIGFLAGS} -DHAVE_XXX"`（config.pkg:304/328/383），
        # 唯独 pthread 只追加了 ${PTHREADFLAGS}（config.pkg:439，即 -pthread），
        # 而 replay.c 的 -P/--picture-series 与整块图片序列代码都挂在 #ifdef HAVE_PTHREAD 上
        # （replay.c:35/84/122/211/247/684/696/907）—— 也就是说上游自己构建出来的 tdreplay
        # **永远没有 -P 选项**。这里由配方补上该宏，与 OPTIONAL_OBJECTS 里
        # "pthreads-picture-series": "src/picture_queue.o" 的既有要求一致
        # （_require_full_feature_set() 会断言该目标确实链接进来了）。
        cflags = (["-I" + d for d in includedirs] + ["-D" + d for d in defines]
                  + ["-O2", "-Isrc", "-DHAVE_PTHREAD"])
        ldflags = ["-L" + d for d in libdirs]

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if cc:
            # 必须用 define（覆盖）而不是 append（追加）：conan 的 append 语义生成
            # `export CC="${CC:-}${CC:+ }<abs>"`，一旦宿主/worker 的 [buildenv] 已经
            # 给了 CC（实测 worker 上是 `CC=clang`），结果就变成
            # `CC="clang /data/service/hnp/bin/clang"` 两个词；上游那套 configure 用
            # 不带引号的 $CC 去编译探针，第二个词被当成输入文件 → 探针编译失败 →
            # 「No working C compiler found」。本地之所以一直绿，是因为本机环境里
            # 没有预置 CC，append 的结果恰好只有一个词。
            env.define("CC", cc)

        env.append("CFLAGS", " ".join(cflags))
        env.append("LDFLAGS", " ".join(ldflags))
        env.append("PKG_CONFIG_PATH", self.generators_folder)
        env.append("PKG_CONFIG", self._pkg_config_shim())
        return env

    def _pkg_config_shim(self):
        """落一个可运行的 ``pkg-config`` 同名 shim 并返回其绝对路径。

        优先 conf / tool_requires 的 pkgconf，再用 PATH 上的；每一步都用
        ``--version`` 握手，避免把「存在但跑不起来」的路径写进 PKG_CONFIG
        （pango/1.58.2 _ensure_pkg_config_shim 同款思路）。
        """
        shim = os.path.join(self.build_folder, "pkg-config")
        if os.path.isfile(shim):
            return shim
        os.makedirs(self.build_folder, exist_ok=True)

        candidates = []
        # conf key 是 tools.gnu:pkg_config（conan config list 里查得到；
        # tools.build:pkg_config 并不存在，会直接抛 ConanException）。
        conf_pkgconfig = self.conf.get("tools.gnu:pkg_config", check_type=str,
                                       default="")
        if conf_pkgconfig:
            candidates.append(conf_pkgconfig)
        pkgconf = self.dependencies.build.get("pkgconf")
        if pkgconf is not None:
            for name in ("pkgconf", "pkg-config"):
                candidate = os.path.join(pkgconf.package_folder, "bin", name)
                if os.path.isfile(candidate):
                    candidates.append(candidate)
        for name in ("pkg-config", "pkgconf"):
            found = shutil.which(name)
            if found:
                candidates.append(found)

        chosen = None
        for candidate in candidates:
            if not (candidate and os.path.isfile(candidate)):
                continue
            if self._pkg_config_works(candidate):
                chosen = candidate
                break
        if chosen is None:
            raise ConanException(
                "no runnable pkg-config/pkgconf found (tried: %s); upstream "
                "configure cannot locate cairo/pangocairo/ncurses without it"
                % ", ".join(c for c in candidates if c))
        self.output.info("termdebug: pkg-config = %s" % chosen)
        with open(shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\n"
                         "# generated by the termdebug recipe; the shim exists because\n"
                         "# upstream configure invokes plain `pkg-config`.\n"
                         "exec %s \"$@\"\n" % chosen)
        os.chmod(shim, 0o755)
        return shim

    @staticmethod
    def _pkg_config_works(candidate):
        # 只做握手，不把版本输出混进 build 日志。
        try:
            result = subprocess.run([candidate, "--version"], capture_output=True,
                                    timeout=120)
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    # ── 构建 ───────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild-termdebug"]
        stray = os.path.join(self.source_folder, STRAY_TARBALL_BINARY)
        if os.path.isfile(stray):
            # tarball 里混进的 2013 年 x86-64 预编译残留，既不参与 Makefile 也不该
            # 出现在包里；删掉它，免得被误认成构建产物。
            os.remove(stray)
            self.output.info("termdebug: removed stray prebuilt binary %s"
                             % STRAY_TARBALL_BINARY)

        # 就地构建：configure 用相对路径引用 Makefile.in / config.pkg。
        try:
            self.run("./configure --prefix=/", cwd=self.source_folder, env=env)
        except ConanException:
            # 失败自诊断（2026-10-15 加）：worker 连续两次报 "No working C compiler
            # found"，但日志里看不到 config.log 的内容，无法判断真因属于「编译器跑不
            # 起来」「找不到头文件/sysroot 缺失」还是别的。这里把关键证据打全，纯失败
            # 分支，不影响任何成功构建的行为。
            self._dump_configure_failure(env)
            raise
        self._require_full_feature_set()
        self.run("make -j1", cwd=self.source_folder, env=env)

        binary = os.path.join(self.source_folder, "termdebug")
        if not os.path.isfile(binary):
            raise ConanException("make did not produce %s" % binary)

    def _dump_configure_failure(self, env):
        """configure 失败时把关键证据打到日志里（纯诊断路径，只在失败分支调用）。

        ``env`` 是**环境脚本名列表**（如 ``["conanbuild-termdebug"]``），不是
        Environment 对象 —— conan 的 ``self.run(env=[...])`` 是在子进程里 source
        这些脚本，本进程环境里看不到 CC/CFLAGS。所以这里改为：① 列出生成器目录；
        ② 打印本配方那条环境脚本与 conanbuild.sh 的正文（CC/CFLAGS/LDFLAGS 都在
        里面）；③ 从脚本里取 CC 做一次 ``--version`` 握手并 which 一次；
        ④ 打印 source_folder/config.log 的最后 100 行。

        背景：本配方只用 VirtualBuildEnv、**没有** AutotoolsToolchain，因此
        CFLAGS 是自己拼的（不含 --target/--sysroot 这类工具链级 flag），CC 只取
        conf tools.build:compiler_executables.c 的裸路径；而同批在 worker 上编译
        成功的 spectools 用的是 AutotoolsToolchain。加了这段诊断就能直接看到
        config.log 里的真实报错，再决定是否补 --target/--sysroot。
        """
        self.output.error("termdebug: configure 失败，开始自诊断（env scripts: %s）" % (env,))
        gen = self.generators_folder
        try:
            self.output.info("  [gen] %s -> %s" % (gen, sorted(os.listdir(gen))))
        except OSError as exc:
            self.output.error("  [gen] 无法列出 %s: %s" % (gen, exc))

        for name in list(env) + ["conanbuild.sh"]:
            path = os.path.join(gen, name if name.endswith(".sh") else name + ".sh")
            if not os.path.isfile(path):
                self.output.error("  [script] %s 不存在" % path)
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            self.output.error("  [script] %s（%d 字节）正文：" % (path, len(text)))
            for line in text.splitlines():
                self.output.error("   | %s" % line)
            match = re.search(r"export CC=['\"]?([^'\"\s]+)", text) or \
                re.search(r"^CC=['\"]?([^'\"\s]+)", text, re.M)
            if match:
                cc = match.group(1)
                self.output.info("  [probe] which(%s) -> %s"
                                 % (cc, shutil.which(cc) or "<不在 PATH 上>"))
                try:
                    pr = subprocess.run([cc, "--version"], capture_output=True, timeout=60)
                    self.output.info("  [probe] %s --version rc=%d :: %s"
                                     % (cc, pr.returncode,
                                        (pr.stdout or pr.stderr).decode("utf-8", "replace").splitlines()[:1]))
                except Exception as exc:          # noqa: BLE001 - 诊断路径，尽力而为
                    self.output.error("  [probe] 无法执行 %s: %s" % (cc, exc))

        log_path = os.path.join(self.source_folder, "config.log")
        if not os.path.isfile(log_path):
            self.output.error("  [config.log] %s 不存在" % log_path)
            return
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        self.output.error("  [config.log] 共 %d 行，以下为最后 100 行：" % len(lines))
        for line in lines[-100:]:
            self.output.error("   | %s" % line)


    def _require_full_feature_set(self):
        """configure 砍功能只打一行 warning，不报错。这里硬断言 OPTOBJECTS 全在。"""
        makefile = os.path.join(self.source_folder, "Makefile")
        if not os.path.isfile(makefile):
            raise ConanException("configure did not generate a Makefile")
        with open(makefile, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        missing = []
        for feature, obj in OPTIONAL_OBJECTS.items():
            # Makefile.in 的 OPTOBJECTS 以空格分隔，configure 追加时前导空格。
            if obj not in text.split("OPTOBJECTS=", 1)[-1].split("\n", 1)[0]:
                missing.append("%s (%s)" % (feature, obj))
        if missing:
            raise ConanException(
                "upstream configure degraded the build; these optional features "
                "are missing from OPTOBJECTS: %s. Refusing to ship a package "
                "whose visual compare / picture output silently does not work. "
                "See config.log in the build folder." % ", ".join(missing))
        self.output.info("termdebug: all 5 optional features enabled (curses, "
                         "libunistring, cairo/pango images, pthread picture series)")

    # ── 打包 ───────────────────────────────────────────────────────────

    def package(self):
        # Makefile 的 install target 尊重 $(DESTDIR)$(prefix)：prefix=/ 由
        # `configure --prefix=/` 烘进 Makefile，所以 DESTDIR=package_folder 就得到
        # <pkg>/bin、<pkg>/share/man/man1、<pkg>/share/doc/termdebug。
        self.run("make install DESTDIR=%s" % self.package_folder,
                 cwd=self.source_folder, env=["conanbuild-termdebug"])

        binary = os.path.join(self.package_folder, "bin", "termdebug")
        if not os.path.isfile(binary):
            raise ConanException("bin/termdebug missing after make install")

        # argv[0] symlink 分派（src/common.c main()）：5 个命令必须是同一个 ELF。
        for command in COMMAND_MAN_PAGES:
            link = os.path.join(self.package_folder, "bin", command)
            if not os.path.islink(link) or os.readlink(link) != "termdebug":
                raise ConanException(
                    "bin/%s is not the expected symlink to termdebug" % command)
        for command, page in COMMAND_MAN_PAGES.items():
            installed = os.path.join(self.package_folder, "share", "man", "man1", page)
            if not os.path.isfile(installed):
                raise ConanException("man page share/man/man1/%s missing" % page)

        os.chmod(binary, 0o755)
        self._sign_ohos_binary(binary)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (signer or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool unavailable; skipping OHOS ELF "
                                "signing (cross build only, consumer test on a "
                                "real device will need it)")
            return
        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (objcopy or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path),
                     ignore_errors=True)
        signed = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                 % (signer, path, signed))
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool produced no output for %s" % path)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))

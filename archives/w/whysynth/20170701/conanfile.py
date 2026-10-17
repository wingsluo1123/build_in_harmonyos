#!/usr/bin/env python3
"""Conan recipe — whysynth 20170701 (WhySynth DSSI 软件合成器插件, autotools).

形态
----
上游是 C（24 个源文件）+ autotools，产物是一个 DSSI 插件模块
`lib/dssi/whysynth.so`（libtool `-module -avoid-version`，无版本后缀）。
没有库/头供下游链接，消费方是 DSSI 宿主（本仓 dssi/1.1.1 的
`lib/dssi/*.so` 与它同一目录）。

依赖（score 与上游 configure.ac 一一对应）
------------------------------------------
* `PKG_CHECK_MODULES(COMMON, dssi >= 0.9)`  → dssi/1.1.1（头 dssi.h + ladspa.h）
* `PKG_CHECK_MODULES(PLUGIN, fftw3f >= 3.0.1)` → **fftw3f**/3.3.10
* `PKG_CHECK_MODULES(GUI, liblo >= 0.12)`   → liblo/0.32
* `PKG_CHECK_MODULES(ALSA, alsa)`           → alsa-lib/1.2.16.1

fftw3f 这一条是本库最容易踩的坑：FFTW 一次构建只出一种精度，本仓
`fftw/*` 各版本都只建 double（`fftw3.pc`），**没有** `fftw3f.pc`；
单精度是独立包 `fftw3f/*`（`pkg_config_name = "fftw3f"`，3.3.10 已发布
OHOS/armv8 二进制）。实测：`~/.conan2/p/fftw*/p/lib/pkgconfig/` 下只有
`fftw3.pc`，而 fftw3f/3.3.10 的 recipe 里 `ENABLE_FLOAT=ON`。所以这里
必须依赖 fftw3f，依赖 fftw 会让 configure 直接报找不到 fftw3f。

GUI（GTK+2）不构建
------------------
`AM_PATH_GTK_2_0` 找不到 GTK+ 时上游只是 `AC_MSG_WARN` 后跳过 GUI
（configure.ac 里 GUI 是可选项），`WhySynth_gtk` 也不安装。本次不引入
gtk2：GUI 需要显示设备，真机无法驱动/断言，而交付物是 DSSI 插件本身。

注意「GTK+ 没装」与「gtk-2.0.m4 没装」是两回事：构建机没有 gtk-2.0.m4
时 `AM_PATH_GTK_2_0` 这个宏根本没有定义，autoconf 会以
`possibly undefined macro: AM_PATH_GTK_2_0` **直接失败**，连可选项都轮不到。
`patches/0001-configure.ac.patch` 把这次调用包进 `m4_ifdef` 修的就是这一点，
语义不变：有宏的机器照旧探测 GTK+，没宏的机器照旧跳过 GUI。

引导与平台识别（铁律 #0：禁止 --build/--host/--target）
------------------------------------------------------
tag 归档里没有 `configure`，必须先 `autoreconf -fi`。本机 `uname -s` 是
"HarmonyOS"（不是 Linux），老 config.guess 认不出来会 "cannot guess
build type"。按 E007 的正解是修 config.guess/config.sub 而**不是**加
--build/--host：这里在 autoreconf 之后把 autoconf 2.72 自带的
config.guess/config.sub 覆盖进源码树（2023-08-22 版有直接的
`*:HarmonyOS:*:*` 分支，实测返回 `aarch64-unknown-linux-ohos`），
然后再断言一次，认不出来就硬失败。为什么不用更新的 2024-07-27 版、
以及为什么必须放在 autoreconf 之后，见 `_install_config_helpers()` 的注释。

引导还要跨过两个坑，都在对应方法的 docstring 里：
* 仓里提交的那份 `aclocal.m4` 会让 autoreconf 整体跳过 aclocal/automake
  （`_drop_stale_aclocal_m4()`）；
* conan 的 perl 包与设备自带 perl 混用会炸（`_run_autoreconf()` 里把
  PERL5LIB 钉回 automake 自己的模块目录）。
"""

import glob
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rm)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# E490：编辑器/HMDFS 下 autoreconf 生成的辅助脚本可能丢 +x，configure 会
# 以 "Permission denied" 失败，这里逐个补回。
_AUTOTOOLS_HELPERS = (
    "configure", "config.guess", "config.sub", "install-sh", "missing",
    "depcomp", "compile", "ltmain.sh", "config.status", "ar-lib",
    "mkinstalldirs", "test-driver",
)


class WhysynthConan(ConanFile):
    name = "whysynth"
    version = "20170701"
    package_type = "shared-library"
    description = "WhySynth DSSI software synthesizer plugin"
    homepage = "https://github.com/theabolton/whysynth"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("dssi/1.1.1")
        # 单精度 FFTW3（fftw3f.pc）。不要换成 fftw/*：那个只建 double。
        self.requires("fftw3f/3.3.10")
        self.requires("liblo/0.32")
        self.requires("alsa-lib/1.2.16.1")

    def build_requirements(self):
        # tag 归档没有 configure/Makefile.in，必须现场 autoreconf；设备上
        # 只有 autoconf 一族在 /data/service/hnp/bin（无 automake/libtool），
        # 所以这三个走 tool_requires（zvbi 0.2.44 / rnnoise 同款做法）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")
        # config.guess/config.sub 也从这里取（见 _install_config_helpers）。
        self.tool_requires("autoconf/2.72")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"whysynth is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps 把依赖的 -I/-L/-l 喂进 configure/make；PkgConfigDeps
        # 生成 dssi.pc/fftw3f.pc/liblo.pc/alsa.pc，供 configure.ac 的
        # PKG_CHECK_MODULES 使用（AutotoolsToolchain 会把 generators 目录
        # 加进 PKG_CONFIG_PATH）。
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # --prefix 默认就是 "/"，package() 用 DESTDIR 收包。
        tc.extra_ldflags.extend(self._dependency_rpath_flags())
        tc.generate()
        PkgConfigDeps(self).generate()

    def _dependency_rpath_flags(self):
        """把依赖的 lib 目录写进 DT_RPATH（E467/E505：configure 的 conftest 跑不起来）。

        根因链：AutotoolsDeps 会把整条依赖闭包塞进 LIBS/LDFLAGS，于是 autoconf
        最早那次 AC_PROG_CC 的探测程序（conftest）也要真正加载 liblo/libfftw3f/
        libasound；而这些共享库只在 conan 缓存里，**不**在加载器默认路径上，本平台
        上 AutotoolsDeps 又只在 Macos 才给 conftest 加 rpath（Linux/OHOS 不加），
        于是 conftest 一跑就 :
            Error loading shared library liblo.so: (needed by ./conftest)
            Error loading shared library libfftw3f.so.3: (needed by ./conftest)
        autoconf 由此误判成"不能运行 C 程序"（rc=77），报
            configure: error: cannot run C compiled programs.

        修法是给依赖目录一条硬 rpath，**不是**按 E467 的告诫去改静态链接、预设
        cross_compiling 缓存变量或加 --host。这里用 `--disable-new-dtags` 让
        -rpath 落在 **DT_RPATH**（不是 DT_RUNPATH）：本平台 LD_LIBRARY_PATH 一旦
        被设置就会压过 DT_RUNPATH，而 DT_RPATH 优先级更高，这样无论构建 shell 里
        有没有 LD_LIBRARY_PATH（E505），conftest 与最终插件都能自己找到依赖。
        同一个做法在 audiowmark 0.6.5（用 fftw3f）里已经落地。
        """
        libdirs = []
        for dependency in self.dependencies.host.values():
            cpp_info = dependency.cpp_info
            for libdir in cpp_info.aggregated_components().libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return [f"-Wl,--disable-new-dtags,-rpath,{libdir}" for libdir in libdirs]

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        # .la 是 libtool 的内部描述文件（里面写死了构建机的绝对路径），不随包发布。
        # 注意两点：
        #  1) Conan 2.x 的 copy() **没有** delete= 参数，ADR §4.1 模板里那句
        #     `copy(..., keep_path=False, delete=True)` 是 Conan 1 的写法，照抄会在
        #     package() 里直接 TypeError（`copy() got an unexpected keyword
        #     argument 'delete'`）。等价实现是用 rm()。
        #  2) rm() 默认 **非递归**：它只扫第一层目录。本库的插件模块（连同它的
        #     .la）装在 `lib/dssi/whysynth.la`，非递归会漏掉，必须 recursive=True，
        #     否则 .la 会带着构建机绝对路径留在包里。
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_plugins()

    def package_info(self):
        # 插件模块：没有可链接的库、没有公开头。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # 与 dssi/1.1.1 同目录，宿主插件搜索路径用同一条约定。
        self.runenv_info.prepend_path(
            "DSSI_PATH", os.path.join(self.package_folder, "lib", "dssi")
        )

    # ── 平台引导 ─────────────────────────────────────────────────────────

    def _bootstrap_autotools(self):
        """在源码树里生成 configure/Makefile.in（E007：不用 --build/--host）。"""
        self._drop_stale_aclocal_m4()
        self._run_autoreconf()
        self._install_config_helpers()
        if str(self.settings.os) == "OHOS":
            self._assert_triplet_supported()

    def _drop_stale_aclocal_m4(self):
        """删掉上游仓里那份"非 aclocal 生成"的 aclocal.m4。

        autoreconf 的第一步是 aclocal，但它有个护栏：**若 aclocal.m4 已存在
        且首行不含 "generated ... by aclocal"，就判定"本包不用 aclocal"而整个
        跳过 aclocal 和 automake**（见 autoconf 2.72 的 autoreconf 第 512-523 行）。
        whysynth 仓里恰好提交了这样一份 aclocal.m4：它是 2002 年代 libtool.m4
        （"serial 46"）的内容，首行是 "# libtool.m4 - Configure libtool ..."，
        没有任何 aclocal 标记，而且**不含 automake 的宏、也不含 pkg.m4**。

        后果实测（第一次 G2）：configure.ac 里 AM_INIT_AUTOMAKE /
        AM_CONFIG_HEADER / AM_CONDITIONAL / AM_PATH_GTK_2_0 以及
        PKG_CHECK_MODULES 全部报 "possibly undefined macro"，autoconf 退出 1。

        删掉它让 autoreconf 正常走 aclocal（会重新生成带标记的 aclocal.m4），
        等价于上游自己的 autogen.sh 里那句 `aclocal`。
        """
        stale = Path(self.source_folder, "aclocal.m4")
        if not stale.is_file():
            return
        first_line = stale.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
        if "by aclocal" in first_line:
            return
        self.output.info(
            "dropping stale aclocal.m4 (first line: %r) so autoreconf will run "
            "aclocal/automake" % first_line
        )
        stale.unlink()

    def _automake_module_dirs(self):
        """automake tool_require 里的 Perl 模块目录（Automake::* 所在）。

        conan 生成的那两个脚本（bin/aclocal-1.18、bin/automake-1.18）只是包装，
        真正执行的 bin/.aclocal-1.18-real / .automake-1.18-real 里 @INC 被写死成
        编译期的 `//share/automake-1.18`（前缀被烤成了 "/"），**在别处根本找不到
        自己的模块**，只能靠 PERL5LIB 指过来。
        """
        package = self.dependencies.build["automake"].package_folder
        dirs = [d for d in sorted(glob.glob(os.path.join(package, "share", "automake-*")))
                if os.path.isfile(os.path.join(d, "Automake", "Config.pm"))]
        if not dirs:
            raise ConanException(
                f"automake tool-require has no Perl modules under {package}/share"
            )
        return dirs

    def _perl_interpreter(self):
        """引导期统一使用的 perl：**automake 包脚本 shebang 里的那个**。

        两个工具包生成的脚本烤死了不同的 perl：
          · automake 包的 bin/.aclocal-real  → `#!/data/service/hnp/bin/perl`
            （设备自带的 5.42.0，包是在本机构建时定型的）
          · autoconf 包的 bin/.autom4te-real → conan perl 5.42.2 的绝对路径，
            而它的编译期 @INC 又是 `//lib/perl5/...`（prefix 被烤成 "/"），
            没有 PERL5LIB 连 strict.pm 都找不到
        两者的二进制模块互不兼容（实测：设备 perl 加载 conan perl 的
        Cwd.so 报 `Perl_my_cxt_init: symbol not found`），而一个 PERL5LIB
        不可能同时满足两边。所以统一到 automake 用的那个 perl —— 它是设备
        自带、@INC 完整、也正是 autoreconf 自己的解释器。
        （autoconf 的包装脚本是 `exec "$PERL" .autom4te-real`，所以给 PERL
        一个覆盖值就能把两边拉到同一个解释器上。）
        """
        candidates = []
        aclocal_real = os.path.join(
            self.dependencies.build["automake"].package_folder, "bin", ".aclocal-real"
        )
        if os.path.isfile(aclocal_real):
            with open(aclocal_real, encoding="utf-8", errors="replace") as handle:
                shebang = handle.readline().strip()
            if shebang.startswith("#!"):
                candidates.append(shebang[2:].strip().split()[0])
        candidates.append(shutil.which("perl") or "")
        candidates += ["/data/service/hnp/bin/perl", "/usr/bin/perl"]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanException("no perl interpreter found for the autotools bootstrap")

    def _run_autoreconf(self):
        self._restore_script_modes()
        # 命令行前缀而不是 Environment().define()：conanbuild.sh 是在 self.run
        # 里被 source 的，它 export 的 PERL/PERL5LIB 会盖掉 os.environ，只有
        # 命令行前缀生效在 source 之后。
        #
        # PERL5LIB **只放 automake 的模块目录**（理由见 _perl_interpreter 与
        # _automake_module_dirs：automake 的 .real 脚本 @INC 被烤成
        # `//share/automake-1.18`，只能靠这个变量指过来；而 conan perl 的模块
        # 目录一旦进来，设备 perl 就会去加载它的 .so 而 ABI 炸）。
        #
        # ACLOCAL_PATH 不用自己拼：conan 已经把它置成 automake 的
        # share/aclocal(-1.18) + 设备 bison/cmake/gettext/pkg-config 的
        # share/aclocal + libtool 的 share/aclocal（conanbuildenv 实测可见），
        # pkg.m4 与 libtool 的 m4 都在里面。
        perl = self._perl_interpreter()
        perl5lib = os.pathsep.join(self._automake_module_dirs())
        self.output.info(f"WHYSYNTH_BOOTSTRAP_PERL={perl}")
        # 必须走 self.run(env="conanbuild")：只有 conan 的聚合环境才带着
        # tool_requires 的 bin 目录（aclocal/automake/libtoolize）。
        self.run(f"PERL={shlex.quote(perl)} PERL5LIB={shlex.quote(perl5lib)} "
                 f"AUTOPOINT=true autoreconf -fi < /dev/null",
                 cwd=self.source_folder, env="conanbuild")
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanException("autoreconf finished but produced no configure script")
        self._restore_script_modes()

    def _install_config_helpers(self):
        """装上能认 HarmonyOS 的 config.guess/config.sub。

        **必须**在 autoreconf 之后：`autoreconf -fi` 会给 automake 传
        `--force-missing`，把 config.guess/config.sub 换回工具包自带的那份，
        所以在它之前放什么都会被覆盖。

        为什么用 autoconf 2.72 自带的那份（config.guess 2023-08-22 /
        config.sub 2023-09-19），而不是更新的 autotools-dev 20240727
        （config.guess 2024-07-27）：新版把"按 uname 静态判定"换成了**编译探针**，
        探针要先在临时目录里写 dummy.c，而它建临时目录用的是 `umask 077`
        （0700）。本机 HMDFS 上 0700 目录不可写（E011：按组位判可达、chmod 是
        空操作），于是探针必然失败，config.guess 直接退化成
        "unable to guess system type" 并 exit 1 —— 实测：
            config.guess[1741]: can't create .../cgGNGbFa/dummy.c: Permission denied

        而且**必须**取 conan 制品里这份、不能取设备 /data/service/hnp 下同名
        2.72 安装的那份：制品里的 config.guess/config.sub 已经按
        scripts/patch-autotools-ohos.pl 打过 OHOS 补丁（多了
        `#elif defined(__OHOS__) LIBC=ohos` 与 `*:HarmonyOS:*:*` 分支），
        设备安装的那份是原版，`uname -s` = HarmonyOS 时同样落到编译探针上而
        失败（两文件 diff 只有这两处，实测设备版 exit 1、制品版 rc=0 返回
        aarch64-unknown-linux-ohos）。
        """
        helpers = os.path.join(
            self.dependencies.build["autoconf"].package_folder,
            "share", "autoconf", "build-aux",
        )
        for name in ("config.guess", "config.sub"):
            if not os.path.isfile(os.path.join(helpers, name)):
                raise ConanException(f"autoconf tool-require is missing {name}: {helpers}")
            copy(self, name, src=helpers, dst=self.source_folder)
        self._restore_script_modes()

    def _assert_triplet_supported(self):
        """断言 config.guess/config.sub 能认出本机（E007 的可验证判据）。

        认不出来时 configure 只会给出含糊的 "cannot guess build type"，
        在这里显式失败能直接把根因钉在 config.* 上（连 stdout/stderr 一起报）。
        """
        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(guess) or not os.path.isfile(sub):
            raise ConanException("config.guess/config.sub missing after bootstrap")
        raw = self._run_config_helper(guess, [guess])
        canon = self._run_config_helper(sub, [sub, raw])
        if "-linux-ohos" not in canon:
            raise ConanException(
                "config.guess/config.sub do not recognize this platform: "
                f"guess={raw!r} canonical={canon!r} (E007 regression)"
            )
        self.output.info(f"WHYSYNTH_NATIVE_TRIPLET={canon}")

    @staticmethod
    def _run_config_helper(script, argv):
        """跑 config.guess/config.sub 并把 stdout/stderr 一并带进错误信息。"""
        completed = subprocess.run(["/bin/sh"] + argv, capture_output=True,
                                   text=True, timeout=120)
        if completed.returncode != 0:
            raise ConanException(
                f"{os.path.basename(script)} failed (rc={completed.returncode}):\n"
                f"stdout: {completed.stdout.strip()[:2000]}\n"
                f"stderr: {completed.stderr.strip()[:2000]}"
            )
        return completed.stdout.strip()

    def _restore_script_modes(self):
        for relative in _AUTOTOOLS_HELPERS:
            path = Path(self.source_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)
        build_aux = Path(self.source_folder, "build-aux")
        if build_aux.is_dir():
            for helper in build_aux.iterdir():
                if helper.is_file():
                    helper.chmod(helper.stat().st_mode | 0o111)

    # ── 鸿蒙代码签名 ─────────────────────────────────────────────────────

    def _sign_plugins(self):
        """鸿蒙 PC 要求 dlopen 的 .so 带 .codesign 节，否则 Permission denied。"""
        if str(self.settings.os) != "OHOS":
            return
        plugins = sorted(
            glob.glob(os.path.join(self.package_folder, "lib", "dssi", "*.so"))
            + glob.glob(os.path.join(self.package_folder, "lib", "dssi", "*.so.*"))
        )
        if not plugins:
            raise ConanException(
                "no DSSI plugin module installed under lib/dssi (expected whysynth.so)"
            )
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(f"OHOS ELF signer missing: {signer}")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        for plugin in plugins:
            if os.path.islink(plugin):
                # 只签真实 ELF，跳过版本化软链（否则对同一目标重复签）。
                continue
            self.run(f'{objcopy} --remove-section .codesign "{plugin}" '
                     f'2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{plugin}" -outFile "{plugin}" -selfSign 1')
            if readelf:
                sections = subprocess.run([readelf, "-S", plugin], capture_output=True,
                                          text=True, timeout=30).stdout
                if ".codesign" not in sections:
                    raise ConanException(
                        f"signed plugin lacks .codesign section: {plugin}"
                    )
        self.output.info(f"WHYSYNTH_SIGNED_PLUGINS={len(plugins)}")

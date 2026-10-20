#!/usr/bin/env python3
"""Conan recipe for Mednafen 1.32.1 —— 多机种模拟器（HarmonyOS PC / aarch64）。

上游：https://mednafen.github.io/releases/files/mednafen-1.32.1.tar.xz （官方直链，R39）
源码主语言：C++（autotools：configure + make），产物是命令行程序 bin/mednafen，
因此 package_type = "application"，并按 R38 在**软件级**目录提供 commands.json。

依赖面（逐一取自 configure.ac 的探测语句，不是猜测）：
  * zlib :  configure.ac:96 `AC_CHECK_LIB([z], [zlibVersion], ZLIB_LIBS="-lz",
            AC_MSG_ERROR([*** zlib not found!]))` —— 硬依赖，缺即 configure 失败。
  * sdl2 :  configure.ac:872-883 `if $NEED_SDL` → `AM_PATH_SDL2(2.0.5, ...)`，
            该宏（m4/sdl2.m4:32-35）先走 `PKG_CHECK_MODULES([SDL],[sdl2 >= 2.0.5])`，
            失败再找 sdl2-config，再失败即 `AC_MSG_ERROR([*** SDL >= 2.0.5 not found!])`
            —— 硬依赖。
  * flac :  configure.ac:709-716 `--with-libflac` 默认 yes →
            `PKG_CHECK_MODULES(FLAC, flac >= 1.3.0, [], AC_MSG_ERROR([...]))`
            —— 默认开启的硬依赖。
其余 `--with-external-*`（mpcdec/tremor/trio/lzo/libzstd）默认都是 no，即使用源码树
自带的内部实现（src/zstd、src/trio、include/minilzo_internal 等），故不声明依赖、
也不加 --with-external-* 开关（R1 参数最少化）。ALSA 与 JACK 在 OHOS 上不存在，
但上游对两者都是**优雅降级**（AM_PATH_ALSA 失败只把 have_alsa 置 no；JACK 走
PKG_CHECK_MODULES 的 ACTION-IF-NOT-FOUND），故同样不加 --disable-*，让 configure
的探测结果如实进入 include/config.h（实测 HAVE_ALSA/HAVE_JACK 均为 undef）。

平台补丁面（详见 conandata.yml 每条 patch 的注释）：
  0001/0002 config.guess/config.sub：真机 uname -s=HarmonyOS 不被 2018 年老脚本识别，
            configure 起手 `cannot guess build type`（E007/E1092/E072）；
  0003 configure：(a) HMDFS 上 `umask 077 && mktemp -d ./confXXXXXX` 建出的目录不可写，
            config.status 写 subs1.awk 报 Permission denied（E114）；(b) OHOS 的
            clang15+ld.lld+musl 下，上游强制的 -fno-pic/-fno-pie/-no-pie 会产生
            `improper alignment for relocation R_AARCH64_LDST64_ABS_LO12_NC`；
  0004 intl/lock.h：gnulib 的 pthread_in_use() 探测用了 OHOS 没有的 pthread_cancel；
  0005 Joystick_Linux.cpp：OHOS 的 dirent.h 不声明 GNU versionsort(3)（E1574 同族）。

测试面：mednafen 没有注册进构建系统的测试（全树无 TESTS/check_PROGRAMS，
`make check` 是空跑），真正的上游断言是**编进二进制**的两处注册入口——
src/mednafen.cpp:1457 在 MDFNI_Init() 里无条件调用的 MDFN_RunCheapTests()（60 项，
清单在 src/tests.cpp），以及由上游调试开关 `-exptests <dir>` 触发的
MDFNI_RunExpensiveTests()（12 项，清单在 src/testsexp.cpp）；任何一项断言失败都会
抛异常。test_package/test.sh 真跑安装出来的 mednafen 来覆盖这两面。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MednafenConan(ConanFile):
    name = "mednafen"
    version = "1.32.1"
    description = ("Mednafen —— 多机种模拟器（NES/SNES/GB/GBA/PCE/PSX/MD/Saturn 等 20+ 机种，"
                   "SDL2 前端，命令行程序）")
    license = "GPL-2.0-or-later"
    homepage = "https://mednafen.github.io/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 用 self.requires() 调用式声明（而非类属性元组）：W0 预检
        # ci/scripts/preflight_check.sh 与 create-pr 的 PF4 依赖闸都只解析调用式。
        self.requires("zlib/1.3.1.1")
        self.requires("sdl2/2.30.10")
        self.requires("flac/1.5.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _hmdfs_env(self):
        """HMDFS / 只读 /tmp 兜底（仓内 adcli/addchain/analog/open-mpi 家族同款）。

        OHOS 的 /tmp 是只读 erofs；autoconf 的 AS_TMPDIR 兜底路径、
        libtool/config.status 子进程都依赖可写的 TMPDIR。这里把 TMPDIR/TMP/TEMP
        钉到 build_folder 内配方主进程预建的目录（build_folder 随构建档期存在）。
        """
        tmpdir = os.path.join(self.build_folder, ".hmdfs-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        return env

    def generate(self):
        # configure.ac 用 PKG_CHECK_MODULES 找 sdl2 / flac：PkgConfigDeps 生成的
        # .pc 落在 generators 目录，而 conanbuild 环境不会自动把它加进
        # PKG_CONFIG_PATH（仓内 1189 个配方同款处置，如 abiword-plugin-docbook:
        # 「PkgConfigDeps 生成的 .pc 在 generators_folder,但 conanbuild env 未自动
        #   注入 PKG_CONFIG_PATH」⇒ 显式注入）。
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("PKG_CONFIG_PATH=" + self.generators_folder)
        # SDL2 的头装在 `<sdl2 package>/include/SDL2/` 下，而上游写的是
        # `#include <SDL.h>`（src/drivers/main.h:11）。conan 的 PkgConfigDeps 按
        # cpp_info.includedirs 生成 `.pc`，Cflags 只有 `-I<prefix>/include`
        # （SDL2 官方 `sdl2.pc` 里则是 `-I${includedir}/SDL2`）⇒ configure 的
        # `checking for SDL... yes` 照样过，`make` 才炸
        # `fatal error: 'SDL.h' file not found`（实测 conan-create 第 3 轮，
        # main.o/ers.o/help.o 三处）。同族已合入先例：exfatprogs/1.4.3 的
        # blkid 子目录缺失（`-I<libblkid>/include/blkid` 追加进 CPPFLAGS）。
        # 路径取自 conan 依赖图（R33/R49），不读裸 shell 变量、不写死机器路径。
        sdl2_inc = os.path.join(str(self.dependencies["sdl2"].package_folder),
                                "include", "SDL2")
        tc.extra_cflags.append("-I" + sdl2_inc)
        tc.extra_cxxflags.append("-I" + sdl2_inc)
        # 同一个坑的第二处：上游只在 `src/Makefile.am:2` 写了
        # `DEFS = @DEFS@ @FLAC_CFLAGS@`，而 **drivers 子目录自己的**
        # `src/drivers/Makefile.am:2` 是
        # `DEFS = -DLOCALEDIR=... @DEFS@ @SDL_CFLAGS@` —— **没有 @FLAC_CFLAGS@**，
        # 于是 `src/drivers/main.cpp:1802` 的 `#include <FLAC/all.h>` 在
        # "flac 装在系统默认 include 路径"（/usr/include）时才侥幸成立；
        # conan 把 flac 装在私有 prefix ⇒ 实测 `fatal error: 'FLAC/all.h' file not found`
        # （第 4 轮 conan-create，main.o 一处）。这里把依赖图里的 flac include
        # 显式补进 CFLAGS/CXXFLAGS（R33：路径取自 conan 依赖图，不读裸 shell 变量）。
        flac_inc = os.path.join(str(self.dependencies["flac"].package_folder), "include")
        tc.extra_cflags.append("-I" + flac_inc)
        tc.extra_cxxflags.append("-I" + flac_inc)
        # 上游 configure.ac:31 自己把 CXX 定成 `-std=gnu++11`，而 conan profile
        # 的 `compiler.cppstd=17` 会让 AutotoolsToolchain 再往 CXXFLAGS 里塞一个
        # `-std=gnu++17`（CXXFLAGS 在 configure 追加的 -std 之后 ⇒ 生效的是 17）。
        # C++17 已删除 register 存储类，实测
        # src/snes_faust/ppu_render_common.inc:1221 起 6 处
        # `error: ISO C++17 does not allow 'register' storage class specifier`。
        # 按上游声明的语言级别把标准钉回 gnu++11（extra_cxxflags 落在 CXXFLAGS 末尾，
        # 覆盖 toolchain 注入的 -std；与原生 driver 构建用的级别一致）。
        tc.extra_cxxflags.append("-std=gnu++11")
        tc.generate()
        self._hmdfs_env().vars(self).save_script("conanbuildenv-hmdfs")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # 上游 make check：mednafen 没在 Makefile.am 注册任何 TESTS/check_PROGRAMS
        # （顶层 SUBDIRS = po intl src），所以这一步是 0 用例空跑 —— 保留它是为了
        # 与 CI L1c 的口径一致（"make check 在 build() 中真实执行"），
        # 真实断言面由 test_package 真跑二进制承担（见文件头"测试面"）。
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

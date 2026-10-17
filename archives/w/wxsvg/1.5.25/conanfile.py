#!/usr/bin/env python3
"""Conan recipe for wxsvg 1.5.25 — Autotools build system (configure + make).

wxsvg is a C++ library to create, manipulate and render SVG files, built on
wxWidgets (GTK3 port) + cairo/pango (render backend) + ffmpeg (multimedia
elements). 1.5.25's headline change is the ffmpeg-7/8 (libav* 60+) adaptation.
Exploration build (2026-10-13, OHOS PC aarch64) validated the full chain incl.
the svgview demo linking. Environment facts baked into this recipe:

1. wxwidgets-gtk3/3.2.10 is a static-PIC package; its bundled wx-config
   hardcodes the CI build machine's conan cache path, so consumers must
   relocate it via --prefix/--exec-prefix. AM_PATH_WXCONFIG honors a preset
   WX_CONFIG_PATH env var (AC_PATH_PROG semantics).
2. The wx-config wrapper is compiled to an ELF binary: script shebang exec
   (any interpreter) is rejected in whole windows on OHOS devices ("bad
   interpreter: Permission denied", HMDFS trust quirk), while binary exec is
   unaffected. The wrapper execs bash, which reads the real wx-config as data.
3. The published glib package ships a private proxy libintl.so (defines the
   gettext -> g_libintl_* bridge) that is not propagated by its .pc files;
   consumers need -L{glib_libdir} -lintl (same handling as aris/2.2).
4. libffi/pcre2 are glib's static transitive deps and are NOT visible in
   self.dependencies.host, so this recipe cannot append -lffi/-lpcre2-8.
   Measurement shows it is not needed for the library itself: the shipped
   libwxsvg.so has zero undefined ffi_*/pcre2_* symbols. Consumers that link
   the static wx chain (e.g. test_package) append the two flags themselves.
5. The published ffmpeg .pc files carry the package version (8.1.2) where
   upstream ffmpeg uses library soname numbers (62.x). wxsvg's
   PKG_CHECK_MODULES(libavformat >= 50.0.0 ...) checks library-version
   semantics and fails; bypass with LIBAV_CFLAGS/LIBAV_LIBS (configure's own
   documented escape hatch).
6. --disable-dependency-tracking: config.status's am--depfiles bootstrap
   execs install-sh directly (via MKDIR_P), which fails in the same
   no-script-exec windows; on CI it is an equally safe no-op.
7. make install runs with MKDIR_P=/bin/mkdir -p for the same reason.
8. config.guess/config.sub HarmonyOS detection + umask fixes in patches
   0001/0002/0003 (E533 pattern, libarchive precedent).
9. Runtime library lookup must NOT use a global LD_LIBRARY_PATH (E505
   forbid_2): the variable is inherited by clang's lld subprocess, which
   itself links libxml2 - Conan's libxml2 then hijacks it and lld crashes
   ("Error relocating .../lld: xmlFreeDoc: symbol not found"), which autoconf
   reports as "C compiler cannot create executables". It does not reproduce on
   every host. Instead a private materialised runtime view + DT_RPATH
   (--disable-new-dtags) is embedded for the configure-time conftest; the
   packaged .so gets its rpath normalised to $ORIGIN afterwards (patchelf).
   LD_LIBRARY_PATH must also be *unset* (Environment.unset): on OHOS musl a
   non-empty value supersedes DT_RPATH entirely (the profile's buildenv always
   injects the SDK llvm lib dir), so resolution falls back to device default
   paths and a same-named-but-different library wins - the device
   /usr/local/lib/libintl.so.8 has no g_libintl_* bridge, while the glib
   package's private proxy does.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

_OHOS_BIN = "/data/service/hnp/bin"
_OHOS_OBJCOPY = _OHOS_BIN + "/llvm-objcopy"
_OHOS_SIGNER = _OHOS_BIN + "/binary-sign-tool"
_OHOS_PATCHELF = _OHOS_BIN + "/patchelf"
_HNP_BASH = _OHOS_BIN + "/bash"

# 二进制 wx-config 包装（见模块 docstring 第 2 点）。包装不烘焙任何路径：
# 真实 wx-config 与重定位前缀经 WXSVG_WXCONFIG_REAL / WXSVG_WXCONFIG_PREFIX
# 环境变量传入，同一份二进制适用于任何 conan 包布局。
_WXCONFIG_WRAPPER_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char *bash = getenv("WXSVG_WXCONFIG_BASH");
    const char *real = getenv("WXSVG_WXCONFIG_REAL");
    const char *prefix = getenv("WXSVG_WXCONFIG_PREFIX");
    if (!bash || !real || !prefix) {
        fprintf(stderr, "wx-config wrapper: missing WXSVG_WXCONFIG_* env\n");
        return 127;
    }
    char pflag[1024], epflag[1024];
    snprintf(pflag, sizeof(pflag), "--prefix=%s", prefix);
    snprintf(epflag, sizeof(epflag), "--exec-prefix=%s", prefix);
    char **nargv = malloc(sizeof(char *) * (argc + 5));
    if (!nargv) return 127;
    int i, j = 0;
    nargv[j++] = (char *)bash;
    nargv[j++] = (char *)real;
    nargv[j++] = pflag;
    nargv[j++] = epflag;
    for (i = 1; i < argc; i++)
        nargv[j++] = argv[i];
    nargv[j] = NULL;
    execv(bash, nargv);
    fprintf(stderr, "wx-config wrapper: execv %s failed\n", bash);
    return 127;
}
"""

# configure 的 ELF 启动器（同窗口的 shebang exec 拒绝，见模块 docstring 第 2
# 点）：当探测到直接 exec configure 被拒（退出 126）时，把真身挪到
# configure.real，原路径放本启动器——conan 的 Autotools.configure() 命令行
# 不变，参数、环境、日志完全同常规路径。解释器与真身路径经环境变量传入。
_CONFIGURE_WRAPPER_C = r"""
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char *bash = getenv("WXSVG_CONFIGURE_BASH");
    const char *real = getenv("WXSVG_CONFIGURE_REAL");
    if (!bash || !real || !bash[0] || !real[0]) {
        fprintf(stderr, "wxsvg configure launcher: missing WXSVG_CONFIGURE_* env\n");
        return 127;
    }
    /* argc+2: 下标 0..argc-1 之外还要容纳 bash/real 两个头部条目并留出
       NULL 终止符 —— execv 按指针数组扫描，缺终止符会读到越界内存
       (EFAULT/间歇性失败)。 */
    char **nargv = calloc(argc + 2, sizeof(char *));
    if (!nargv) return 127;
    nargv[0] = (char *)bash;
    nargv[1] = (char *)real;
    for (int i = 1; i < argc; i++)
        nargv[i + 1] = argv[i];
    execv(bash, nargv);
    fprintf(stderr, "wxsvg configure launcher: execv %s failed: errno=%d %s\n",
            bash, errno, strerror(errno));
    return 126;
}
"""


class WxsvgConan(ConanFile):
    name = "wxsvg"
    version = "1.5.25"
    description = "C++ library to create, manipulate and render SVG files"
    license = "wxWindows Library Licence"
    homepage = "https://wxsvg.sourceforge.net/"
    topics = ("svg", "wxwidgets", "multimedia", "rendering")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libav": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_libav": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与 manifest.yaml dependencies 保持一致（可复现构建）。
        self.requires("wxwidgets-gtk3/3.2.10")
        # src/svgxml/svgxml.cpp 直接 #include <expat.h>（非 wx 内置 expat），
        # 且 gtk 树把 expat 统一到 2.8.2.1，须对齐避免单图双版本。
        self.requires("expat/2.8.2.1")
        # ExifHandler：SVG 内嵌 JPEG 的 EXIF 方向处理。
        self.requires("libexif/0.6.26.1")
        # 渲染后端（默认 USE_RENDER_CAIRO）与文本布局（pangocairo）。
        self.requires("cairo/1.18.4")
        self.requires("pango/1.50.14.1.1")
        # 注：libffi/3.4.4 与 pcre2/10.45 是 glib 的静态传递依赖（glib 配方
        # requires，但不进消费图聚合）。这里【不能】显式 requires：它们一旦
        # 进入 wxsvg 自己的依赖图，AutotoolsDeps 会把 pcre2 的组件
        # （pcre2-posix 等）聚进 LIBS，libtool 对 -lpcre2-8 做 .la 展开时得到
        # 空前缀路径（'//lib/libpcre2-8.la'）直接断链。链接补链
        # 本配方【不】追加 -lffi/-lpcre2-8（generate() 实测无需，见其第 4 点）；
        # test_package 侧自行声明这两个包、自行按需补链（见其 conanfile）。
        if self.options.with_libav:
            # 1.5.25 主题：ffmpeg 7/8 系适配（<audio>/<video> 元素解码）。
            self.requires("ffmpeg/8.1.2")
        # ffmpeg/8.1.2 发布配方 pin harfbuzz/14.2.0，gtk 树 pin 14.2.0.1.1.1；
        # 同一 conan 图不允许双版本，统一 override 到 gtk 树版本（无 ABI 差异）。
        self.requires("harfbuzz/14.2.0.1.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # 依赖图小工具
    # ------------------------------------------------------------------ #

    def _dep(self, name):
        """按名取 host 依赖（含传递依赖）；找不到返回 None。"""
        for ref_id, dep in self.dependencies.host.items():
            if dep.ref.name == name:
                return dep
        return None

    def _host_libdirs(self):
        """全部 host 依赖的（绝对）lib 目录，去重保序。"""
        dirs = []
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                d = libdir if os.path.isabs(libdir) \
                    else os.path.join(dep.package_folder, libdir)
                if d not in dirs:
                    dirs.append(d)
        return dirs

    # ------------------------------------------------------------------ #
    # generate
    # ------------------------------------------------------------------ #

    def _runtime_view(self):
        """E505: 依赖共享库闭包的实体化运行视图（供 rpath 使用）。

        禁止导出全局 LD_LIBRARY_PATH（E505 forbid_2）：该变量会被 clang/lld
        等工具链子进程继承，而 OHOS SDK 的 lld 自身依赖 libxml2，一旦被
        Conan 的 libxml2 抢占即在 CI worker 上崩溃（Error relocating ...
        native/llvm/bin/lld: xmlFreeDoc: symbol not found），被 autoconf 报成
        "C compiler cannot create executables"；本地介质恰好兼容所以不复现。
        另外 OHOS musl 下 LD_LIBRARY_PATH 还会压过 DT_RPATH，且 HMDFS 上
        版本化别名（libfoo.so.1 -> libfoo.so.1.2.3）无法由加载器经别名解析。

        做法：把依赖 libdir 中"符号链接形式的版本化别名"解引用后按别名复制
        为实体文件（实体文件无需拷贝，rpath 可直接解析），构建期只经
        DT_RPATH 暴露视图与各依赖 libdir。
        """
        view = os.path.join(self.build_folder, "runtime-libs")
        os.makedirs(view, exist_ok=True)
        for libdir in self._host_libdirs():
            if not os.path.isdir(libdir):
                continue
            for entry in sorted(os.listdir(libdir)):
                if ".so" not in entry:
                    continue
                src = os.path.join(libdir, entry)
                if not os.path.islink(src):
                    continue  # 实体文件：rpath 直接解析，无需拷贝
                real = os.path.realpath(src)
                if not os.path.isfile(real):
                    continue  # 悬空链接：交由 rpath 其他目录兜底
                dst = os.path.join(view, entry)
                if os.path.exists(dst):
                    continue
                try:
                    shutil.copy2(real, dst)
                except OSError:
                    continue
        return view

    def generate(self):
        VirtualBuildEnv(self).generate()
        # cairo/pangocairo/expat/libexif/libav* 的 .pc：configure 的
        # PKG_CHECK_MODULES 消费。
        PkgConfigDeps(self).generate()
        # LIBS/LDFLAGS 聚合（不含 glib 私有 libffi/pcre2，见下）。
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # am--depfiles 引导直接 exec install-sh 脚本，在脚本 exec 被拒的设备
        # 会话窗必挂；CI 上 --disable-dependency-tracking 同样安全。
        tc.configure_args.append("--disable-dependency-tracking")
        if self.options.shared:
            # conan 包只装一份形态：shared 包不产静态库（上游默认两态都建）。
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
        tc.generate()

        env = Environment()

        # (0) E505：必须清空 LD_LIBRARY_PATH。OHOS musl 加载器一旦发现该变量
        #     非空，就会【取代】二进制的 DT_RPATH 生效（profile 的 buildenv 会
        #     注入 SDK llvm lib 路径，故实际总是非空）；此时依赖解析回落到
        #     设备默认路径，命中同名但符号不同的库——典型是
        #     /storage/Users/currentUser/usr/local/lib/libintl.so.8（标准
        #     gettext 符号，无 g_libintl_* 桥），而 glib 包私有代理才是桥的
        #     提供者，于是 conftest 运行期 "g_libintl_*: symbol not found"。
        #     清空后 rpath（见 (1)(2)）才真正生效；实测 clang/lld/llvm-objcopy/
        #     patchelf/binary-sign-tool 均不依赖该变量。
        env.unset("LD_LIBRARY_PATH")

        # (1) E505：configure 的编译器健全性检查以全量 LDFLAGS+LIBS 链接
        #     并【运行】conftest。运行时库定位【不能】用全局 LD_LIBRARY_PATH
        #     （会被 clang/lld 继承并把 lld 的 libxml2 抢成 Conan 版 → CI 崩溃，
        #     本地侥幸不复现，见 _runtime_view docstring）。改为实体化视图 +
        #     DT_RPATH 嵌入：conftest 与新库都经 rpath 找到依赖。
        view = self._runtime_view()

        # (2) LDFLAGS：视图与全图 host 依赖 lib 目录前置。
        #     -L 顺序：OHOS 适配版 conan 会往 LDFLAGS 注入设备级
        #     -L/usr/local/lib（hnp clang sysroot），共享设备上该目录可能存有
        #     其他会话安装的同名库（无桥符号 libintl.so、静态 libgio-2.0.a），
        #     抢在包目录之前会选错 → 前置全部包目录恢复"配方依赖先于设备
        #     系统前缀"的语义。
        #     --disable-new-dtags 保证写出 DT_RPATH 而非 DT_RUNPATH。
        libdirs = [d for d in self._host_libdirs() if os.path.isdir(d)]
        rpaths = [d for d in [view] + libdirs if os.path.isdir(d)]
        env.prepend(
            "LDFLAGS",
            " ".join(
                ["-L%s" % view, "-Wl,--disable-new-dtags"]
                + ["-Wl,-rpath,%s" % d for d in rpaths]
                + ["-L%s" % d for d in libdirs]
            ),
        )

        # (3) glib 代理 libintl（gettext -> g_libintl_* 桥）：.pc 不传递，
        #     消费端补 -lintl（aris/2.2 同款）。共享代理与位置无关，经
        #     (2) 前置的 glib lib 目录选中正确的桥。
        glib = self._dep("glib")
        if glib is not None:
            env.append("LIBS", "-lintl")

        # (4) libffi/pcre2 是 glib 的静态传递依赖，但不作为本配方的可见
        #     requires 出现（self.dependencies.host 中无此二者），故此处不追加
        #     -lffi/-lpcre2-8。实测产物 libwxsvg.so.3.12.8 的动态未定义符号里
        #     ffi_*/pcre2_* 均为 0（llvm-nm -D --undefined-only），当前
        #     wxwidgets-gtk3/3.2.10 构建下 wx 静态链并未烘焙这两个引用；
        #     consumer（test_package）需要时自行在链接行尾补（见其 conanfile）。

        # (5) libav 版本旁路：发布的 ffmpeg .pc Version=8.1.2（包版本），而上游
        #     ffmpeg .pc 用库版本号（62.x），wxsvg 按库版本语义检查必然失败。
        #     LIBAV_CFLAGS/LIBAV_LIBS 是 configure 文档化的旁路口。
        if self.options.with_libav:
            ffmpeg = self._dep("ffmpeg")
            ff_inc = os.path.join(ffmpeg.package_folder,
                                  ffmpeg.cpp_info.includedirs[0])
            ff_lib = os.path.join(ffmpeg.package_folder,
                                  ffmpeg.cpp_info.libdirs[0])
            # 链接序遵循 ffmpeg 组件依赖表：avformat > avcodec > swscale >
            # swresample > avutil；传递依赖（openh264/vpx/opus/lame/xml2/zlib）
            # 由共享 libav* 的 DT_NEEDED 在运行期解决。
            env.define("LIBAV_CFLAGS", f"-I{ff_inc}")
            env.define(
                "LIBAV_LIBS",
                f"-L{ff_lib} -lavformat -lavcodec -lswscale -lswresample -lavutil",
            )

        # (6) wx-config：编译二进制包装（见模块 docstring 第 2 点）。真实脚本
        #     与前缀经环境变量传入。wxwin.m4 的 WX_CONFIG_CHECK 拿裸名
        #     "wx-config" 在 cwd 做 test -x，命中后却按 PATH 搜索执行（m4 假定
        #     传入的是绝对路径）——必须把包装所在目录前置 PATH 才两条路都通。
        wx = self.dependencies["wxwidgets-gtk3"]
        real_wxconfig = os.path.join(
            wx.package_folder, "lib", "wx", "config", "gtk3-unicode-static-3.2")
        if not os.path.isfile(real_wxconfig):
            raise Exception(
                f"wx-config not found at {real_wxconfig}; wxwidgets-gtk3 "
                "package layout changed?")
        wrapper_src = os.path.join(self.build_folder, "wxconfig_wrapper.c")
        wrapper_bin = os.path.join(self.build_folder, "wx-config")
        with open(wrapper_src, "w", encoding="utf-8") as f:
            f.write(_WXCONFIG_WRAPPER_C)
        env.prepend_path("PATH", self.build_folder)
        env.define("WX_CONFIG_PATH", wrapper_bin)
        # 解释器探测（hnp bash 优先，逐级兜底），与 configure 启动器同一处逻辑
        env.define("WXSVG_WXCONFIG_BASH", self._bash_path())
        env.define("WXSVG_WXCONFIG_REAL", real_wxconfig)
        env.define("WXSVG_WXCONFIG_PREFIX", wx.package_folder)

        # configure 启动器 + autoconf 自引用路径（shebang exec 受阻的会话窗，
        # 见 _wrap_configure；CONFIG_SHELL 让 config.status/Makefile SHELL 都
        # 走同一 bash，健康窗口无影响）。
        bash = self._bash_path()
        env.define("CONFIG_SHELL", bash)
        env.define("WXSVG_CONFIGURE_BASH", bash)
        env.define(
            "WXSVG_CONFIGURE_REAL",
            os.path.join(self.source_folder, "configure.real"))
        env.vars(self, scope="build").save_script("conanbuild_wxsvg_env")

    # ------------------------------------------------------------------ #
    # build / package
    # ------------------------------------------------------------------ #

    @staticmethod
    def _bash_path():
        """设备上可用的脚本解释器（hnp bash 优先，其后逐级兜底）。"""
        for candidate in (_HNP_BASH, "/system/bin/sh", "/bin/bash", "/bin/sh"):
            if os.path.isfile(candidate):
                return candidate
        return _HNP_BASH

    def _build_wxconfig_wrapper(self):
        """把 wx-config 包装编译为 ELF 二进制并置执行位。

        编译器取构建环境 CC（VirtualBuildEnv/AutotoolsToolchain 已激活），
        兜底 clang。HMDFS 可能吞掉新文件的执行位（E490），编译后显式 chmod。
        """
        wrapper_src = os.path.join(self.build_folder, "wxconfig_wrapper.c")
        wrapper_bin = os.path.join(self.build_folder, "wx-config")
        cc = os.environ.get("CC") or "clang"
        subprocess.run(
            [cc, wrapper_src, "-o", wrapper_bin],
            check=True, cwd=self.build_folder,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        os.chmod(wrapper_bin, 0o755)

    def _shebang_exec_ok(self):
        """探测：脚本经 shebang 机制直接 exec 是否可行。

        设备上存在整窗拒绝脚本 shebang exec 的 HMDFS 信任状态（此时二进制
        exec 不受影响）。探测体与 configure 同为 build 目录下的 #!/bin/sh
        脚本，探测失败（126/Permission denied）即需要启动器。
        """
        probe = os.path.join(self.build_folder, "wxsvg_shebang_probe.sh")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(probe, 0o755)
        try:
            self.run('"%s"' % probe)
            return True
        except ConanException:
            return False
        finally:
            os.remove(probe)

    def _wrap_configure(self):
        """configure → ELF 启动器（真身挪至 configure.real，参数与环境
        保持在 Autotools.configure() 的常规命令行里，无需复刻参数组合）。"""
        configure = os.path.join(self.source_folder, "configure")
        real = os.path.join(self.source_folder, "configure.real")
        os.rename(configure, real)
        wrapper_src = os.path.join(self.build_folder, "configure_launcher.c")
        with open(wrapper_src, "w", encoding="utf-8") as f:
            f.write(_CONFIGURE_WRAPPER_C)
        cc = os.environ.get("CC") or "clang"
        subprocess.run(
            [cc, wrapper_src, "-o", configure],
            check=True, cwd=self.build_folder,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        os.chmod(configure, 0o755)
        self.output.info(
            "shebang exec restricted in this window: installed ELF "
            "configure launcher (real script at configure.real)")

    def build(self):
        apply_conandata_patches(self)
        # E490：HMDFS 可能只保留源码内容而丢失执行位（新文件 0755 正常）。
        # 先恢复 autotools 脚本的执行位，否则 configure 非可执行时探针会误判
        # （探针自建文件恒 0755），跳过 ELF 启动器替换而在 configure 处失败。
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "depcomp", "compile"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
        self._build_wxconfig_wrapper()
        if not self._shebang_exec_ok():
            self._wrap_configure()
        autotools = Autotools(self)
        autotools.configure()
        # -j1：HMDFS 不支持 make jobserver 的 mkfifo（"Operation not permitted"），
        # 并行时子 make 无法建 jobserver 通道；单线程构建稳定且避免该噪音。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # 生成的 Makefile 里 MKDIR_P 直接 exec install-sh 脚本（非 $(SHELL)
        # 包装），脚本 shebang exec 被拒的会话窗会挂 install；以命令行变量
        # 覆盖为系统 mkdir -p（幂等，CI 同样安全，并经 MAKEFLAGS 传播子 make）。
        # 注意值含空格必须整体引号包裹：install() 按空白 join 后经 shell 执行，
        # 不加引号时 "-p" 会被 make 当作自己的选项（--print-data-base）。
        # -j1：HMDFS 拒绝 make jobserver 的 mkfifo（"Operation not permitted"，
        # 非致命但污染日志），安装无并行收益，顺带规避开。
        autotools.install(args=["MKDIR_P='/bin/mkdir -p'", "-j1"])
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # R38：本包是 library —— svgview 是上游演示程序（svgview_LDADD=
        # ../src/libwxsvg.la 的全链链接验证品），不随包分发（无 commands.json）。
        shutil.rmtree(os.path.join(self.package_folder, "bin"), ignore_errors=True)
        # E505 收尾：归一 rpath（去构建机绝对路径；签名前）
        self._normalize_rpath()
        # 移除 libtool .la 包装：其 dependency_libs 内嵌构建机绝对路径
        # （-L/tmp/.../p/<dep>/p/lib），对下游 autotools 消费方是错误来源；
        # pkg-config（libwxsvg.pc）才是受支持路径（a52dec 等 527 个配方同款）。
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        # 构建沙箱 symlink/link 被拒：物化 .so 别名（playerctl 同款）。
        self._ensure_shared_lib_aliases()
        # 鸿蒙 PC XPM：动态库需代码签名。
        self._sign_artifacts()

    def _normalize_rpath(self):
        """E505 收尾：把安装后共享库的 DT_RPATH 归一为 $ORIGIN。

        构建期 DT_RPATH 指向实体化运行视图/依赖包目录（绝对路径），发布产物
        不应内嵌构建机路径；$ORIGIN 是共享库惯例（同目录自查找），且不依赖
        全局 LD_LIBRARY_PATH。必须在签名（_sign_artifacts）之前执行——patchelf
        会重写 ELF，签名必须是对最终字节流。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        patchelf = _OHOS_PATCHELF if os.path.isfile(_OHOS_PATCHELF) \
            else shutil.which("patchelf")
        targets = [p for p in glob.glob(os.path.join(libdir, "lib*.so*"))
                   if self._is_elf(p)]
        if not targets:
            return
        if not patchelf:
            self.output.warning(
                "patchelf 不可用：产物保留构建期 rpath（运行不受影响，仅不够干净）")
            return
        for target in sorted(targets):
            # $ORIGIN 用单引号，避免被 shell 展开为空
            self.run('"%s" --set-rpath \'$ORIGIN\' "%s"' % (patchelf, target),
                     ignore_errors=True)

    def _ensure_shared_lib_aliases(self):
        """补齐共享库链接名与 SONAME 实体文件（symlink 不可用环境）。

        make install 由 libtool 安装 libwxsvg.so.3.12.8 + 别名；别名若被
        跳过（symlinkat 被拒），消费方 -lwxsvg 与运行期 SONAME 加载都会失败。
        别名缺失时以实体文件补齐；能正常建链的环境无任何改动。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = [p for p in glob.glob(os.path.join(libdir, "libwxsvg.so.*"))
                if not os.path.islink(p)]
        if not real:
            return
        source = sorted(real)[-1]
        for alias in ("libwxsvg.so.3", "libwxsvg.so"):
            target = os.path.join(libdir, alias)
            if os.path.lexists(target):
                continue
            shutil.copy2(source, target)
            self.output.info(
                "Materialized shared library alias %s (symlinks unsupported)"
                % os.path.basename(target))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_artifacts(self):
        """鸿蒙 PC XPM：动态库需代码签名（binary-sign-tool 缺失时告警不阻塞）。"""
        libdir = os.path.join(self.package_folder, "lib")
        targets = []
        if os.path.isdir(libdir):
            for pattern in ("**/*.so", "**/*.so.*"):
                targets.extend(glob.glob(os.path.join(libdir, pattern), recursive=True))
        targets = [t for t in targets if self._is_elf(t)]
        if not targets:
            return
        if not os.path.isfile(_OHOS_SIGNER):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        objcopy = _OHOS_OBJCOPY if os.path.isfile(_OHOS_OBJCOPY) \
            else shutil.which("llvm-objcopy")
        for target in sorted(set(targets)):
            if objcopy:
                # || true：老产物可能本无 .codesign 段（objcopy 返回非零），
                # 属预期情形，不应中断签名流程。
                self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                        % (objcopy, target))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                    % (_OHOS_SIGNER, target, target))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libwxsvg")
        self.cpp_info.set_property("cmake_file_name", "wxsvg")
        self.cpp_info.set_property("cmake_target_name", "wxsvg::wxsvg")
        self.cpp_info.libs = ["wxsvg"]
        # 依赖传播由 requirements() 的图自动完成：无 components 时
        # cpp_info.requires 会被 conan 校验为"未定义的内部组件"，不可填。
        # 头文件在 include/wxSVG/ 下，消费方 #include <wxSVG/SVGDocument.h>，
        # includedirs 用默认 include 即与上游 libwxsvg.pc 的 Cflags 一致。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

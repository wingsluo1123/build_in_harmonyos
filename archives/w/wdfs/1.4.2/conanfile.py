#!/usr/bin/env python3
"""Conan recipe — wdfs 1.4.2 (WebDAV filesystem for FUSE).

wdfs 把 WebDAV 资源（http/https）挂载成本地目录的 FUSE 用户态文件系统，
唯一产物是可执行文件 wdfs（src/Makefile.am: bin_PROGRAMS = wdfs）。

上游 codyps/wdfs 仓库无 tag；版本以 master 源码树 configure.ac
AC_INIT(wdfs, 1.4.2) 与 ChangeLog 首条 1.4.2 确认，固定提交
3fa703545e384dca75417b01a45a534a253ef4c7（2015-11-14）保证可复现。

构建要点（配方参照 mtpfs/mhddfs 等同类 FUSE 2.x 工具先例）：
  * tarball 自带 2015 年生成的 configure/Makefile.in（autoconf 2.69），
    无需 autoreconf：configure.ac 使用已被 automake 1.13+ 移除的
    AM_CONFIG_HEADER，重新 bootstrap 必失败；也不声明 automake/
    libtool tool_requires。
  * configure.ac 无 AC_CANONICAL_HOST/config.guess，依赖发现全走
    PKG_CHECK_MODULES(WDFS, [fuse >= 2.5.0 neon >= 0.24.7 glib-2.0])，
    因此不传 --build/--host（mtpfs 同款形态：无平台检测，靠
    CC/CFLAGS/LDFLAGS 直接驱动）。
  * libfuse 配方没有定义 pkg_config_name（且 package() 阶段 rmdir 了
    自带 pkgconfig 目录），PkgConfigDeps 不会生成 fuse.pc → 本配方在
    generators_folder 手写 fuse.pc（mtpfs 同款先例），路径取自
    self.dependencies 的实际 package_folder，禁止硬编码缓存路径。
  * neon 的公开头文件按上游约定装在 <prefix>/include/neon/（ne_props.h
    等），而 wdfs 源码用无前缀包含 `#include <ne_props.h>`；conan
    PkgConfigDeps 生成的 neon.pc 只有 `Cflags: -I<prefix>/include`，
    不足以编译 → 同样手写 neon.pc 补 `-I<prefix>/include/neon`
    （与上游 neon.pc 的 `Cflags: -I${includedir}/neon` 一致）。
  * 上游 configure 内联 `export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:
    $PKG_CONFIG_PATH`，会把宿主 /usr/local 的 .pc 插到搜索路径最前
    （本机 $HOME/usr/local/lib/pkgconfig 有 glib-2.0.pc 等同名模块）→
    构建期用 replace_in_file 去掉该前缀，只保留 conan 生成的
    generators 目录（R49：不得注入共享系统前缀）。
  * E011/E386: HMDFS 上 config.status 的 `umask 077 && mktemp -d` 造出
    构建用户写不进的临时目录 → 内联 sed umask 077→022（configure 属
    autoconf 生成物，refresh-patch 政策拒绝出补丁，故内联处理）；
    SDK bash getcwd 问题用 SHELL=/bin/sh + unset CONFIG_SHELL 规避。
  * D3: OHOS musl 忽略 DT_RUNPATH，configure 的 conftest 运行期找不到
    glib 共享库（伪装成 "cannot run C compiled programs"）→ 依赖包
    libdirs 注入 LD_LIBRARY_PATH。
  * FUSE_USE_VERSION=25（src/wdfs-main.h 固定）→ libfuse 2.x API，
    对应 libfuse/2.9.9（3.x API 不兼容，validate() 显式拒绝）。
  * E085 (musl 无 POSIX 线程取消 API): OHOS libc 导出 pthread_cancel/
    pthread_setcancelstate，但**未导出 pthread_setcanceltype**，而
    src/cache.c 的缓存回收线程用它设置异步取消类型 → 不加处理时动态
    加载器以 "Error relocating ...: pthread_setcanceltype: symbol not
    found" 拒绝启动（rc=127）。本配方在 generate() 生成语义兼容实现
    （见 _write_libc_compat）并随可执行文件静态链入；libfuse.a 对
    pthread_cancel/pthread_setcancelstate 的引用则由 OHOS 运行期 libc
    提供，配合 -Wl,--unresolved-symbols=ignore-all 保持符号未定义。
  * R9: make -j1（Autotools.make 默认非并行）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
    replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class WdfsConan(ConanFile):
    name = "wdfs"
    version = "1.4.2"
    description = "WebDAV filesystem for FUSE (mount a WebDAV share as a local directory)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/codyps/wdfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 标准脚手架（G1 完整性）；conandata patches 为空时 no-op
        export_conandata_patches(self)

    def requirements(self):
        # src/wdfs-main.h: #define FUSE_USE_VERSION 25 -> FUSE 2.x API
        self.requires("libfuse/2.9.9")
        # neon >= 0.24.7（WebDAV 客户端库，静态构建，仓库已发布）
        self.requires("neon/0.34.0")
        # glib-2.0（PKG_CHECK_MODULES 第三项）
        self.requires("glib/2.88.3.1")
        # 传递依赖冲突消解：neon/0.34.0 约束 zlib/1.3.1，glib/2.88.3.1 约束
        # zlib/1.3.2（其已发布 binary 即按 1.3.2 构建）→ 统一 override 到
        # 1.3.2。zlib 补丁版间 API/ABI 兼容；仓库 zlib/1.3.2 为 -fPIC 静态版
        # （不引入运行期 libz.so，不污染系统 /lib），符合静态链接诉求。
        self.requires("zlib/1.3.2", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported")
        # FUSE_USE_VERSION=25 固定 FUSE 2.x API：显式拒绝 3.x 防止依赖漂移
        fuse_version = str(self.dependencies["libfuse"].ref.version)
        if not fuse_version.startswith("2."):
            raise ConanInvalidConfiguration(
                f"wdfs needs libfuse 2.x (FUSE_USE_VERSION=25), got {fuse_version}")

    def layout(self):
        # src/ 解包 + 独立 build 目录（VPATH 构建）
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_handmade_pc(self, pc_dir):
        """手写 fuse.pc / neon.pc（覆盖 PkgConfigDeps 同名生成物）。

        * fuse：libfuse 配方未定义 pkg_config_name，PkgConfigDeps 生成的
          文件名是 libfuse.pc，而 configure 的 PKG_CHECK_MODULES 要求模块名
          fuse（fuse >= 2.5.0）→ 必须手写 fuse.pc（mtpfs 先例）。
        * neon：公开头安装在 <prefix>/include/neon/，而 wdfs 源码用无前缀
          包含 `#include <ne_props.h>`；PkgConfigDeps 生成的 neon.pc 只有
          `Cflags: -I<prefix>/include` → 手写 neon.pc 补 include/neon
          （与上游 neon.pc 的 `Cflags: -I${includedir}/neon` 一致）。

        内容只负责存在性/版本检查与头文件搜索路径；真实 -I/-L/-l 链接闭包
        由 AutotoolsDeps 提供。
        """
        fuse_dir = self.dependencies["libfuse"].package_folder
        with open(os.path.join(pc_dir, "fuse.pc"), "w", encoding="utf-8") as f:
            f.write(f"""Name: fuse
Description: FUSE 2.x API headers/lib (provided by conan libfuse/2.9.9)
Version: 2.9.9
Libs: -L{fuse_dir}/lib -lfuse -lpthread
Cflags: -I{fuse_dir}/include
""")
        neon_dir = self.dependencies["neon"].package_folder
        with open(os.path.join(pc_dir, "neon.pc"), "w", encoding="utf-8") as f:
            f.write(f"""Name: neon
Description: neon WebDAV client library (provided by conan neon/0.34.0)
Version: 0.34.0
Libs: -L{neon_dir}/lib -lneon
Requires: expat zlib
Cflags: -I{neon_dir}/include/neon -I{neon_dir}/include
""")

    def _write_libc_compat(self):
        """生成并编译 OHOS libc 兼容层，返回待链入的目标文件路径。

        OHOS musl libc 未导出 pthread_setcanceltype（仅导出 pthread_cancel/
        pthread_setcancelstate），而 src/cache.c 的缓存回收线程调用它设置
        异步取消类型；缺符号时动态加载器直接拒绝启动（rc=127）。
        兼容实现按 POSIX 校验取消类型、按线程记录当前类型并返回旧值；
        无法写回 libc 内部状态，故本平台保持缺省 PTHREAD_CANCEL_DEFERRED
        —— 取消仍由 pthread_setcancelstate 使能，并在下一个取消点
        （缓存线程的 sleep()）生效，退出时 pthread_cancel 仍能终止该线程。
        """
        src = os.path.join(self.generators_folder, "wdfs_libc_compat.c")
        obj = os.path.join(self.generators_folder, "wdfs_libc_compat.o")
        with open(src, "w", encoding="utf-8") as f:
            f.write("""/* wdfs OHOS libc 兼容层（由 conanfile.py 生成，见其 docstring）。 */
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>

static __thread int wdfs_cancel_type = PTHREAD_CANCEL_DEFERRED;

int pthread_setcanceltype(int type, int *oldtype)
{
\tif (type != PTHREAD_CANCEL_DEFERRED &&
\t    type != PTHREAD_CANCEL_ASYNCHRONOUS)
\t\treturn EINVAL;
\tif (oldtype != NULL)
\t\t*oldtype = wdfs_cancel_type;
\twdfs_cancel_type = type;
\treturn 0;
}
""")
        # R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f'"{cc}" -c -O2 -fPIC "{src}" -o "{obj}"')
        return obj

    def generate(self):
        VirtualBuildEnv(self).generate()
        # 链接闭包：聚合全部 host 依赖（含 neon 的 zlib/expat、glib 的
        # pcre2/libffi 等传递依赖）
        AutotoolsDeps(self).generate()
        # glib 组件 .pc（glib-2.0/gobject-2.0/gio-2.0/gthread-2.0 等）
        # + expat/zlib 等依赖包 .pc
        PkgConfigDeps(self).generate()
        # 队列末尾手写，覆盖同名生成物（fuse.pc / neon.pc）
        self._write_handmade_pc(self.generators_folder)

        tc = AutotoolsToolchain(self)
        # R1: 参数最少化；PKG_CHECK_MODULES 需要 pkg-config 真实解析到模块
        tc.configure_args.append(
            f"PKG_CONFIG_PATH={self.generators_folder}")
        env = tc.environment()
        # E386: SDK bash getcwd 在 HMDFS 构建目录失败，autoconf 经
        # CONFIG_SHELL re-exec —— route 到 /bin/sh（mtpfs 先例）
        env.unset("CONFIG_SHELL")
        env.define("SHELL", "/bin/sh")
        # D3: OHOS musl 忽略 DT_RUNPATH，configure 的 conftest 运行期
        # 找不到依赖共享库 → 注入依赖包 libdirs
        for _, dep in self.dependencies.host.items():
            for d in dep.cpp_info.libdirs:
                path = d if os.path.isabs(d) else os.path.join(
                    dep.package_folder, d)
                env.prepend_path("LD_LIBRARY_PATH", path)
        if str(self.settings.os) == "OHOS":
            # libfuse.a 静态引用 pthread_cancel/pthread_setcancelstate，
            # OHOS SDK 链接期 libc 不导出（运行期 libc 有真实实现）→ 保持
            # 符号未定义交运行期解析
            env.append("LDFLAGS", "-Wl,--unresolved-symbols=ignore-all")
            # 显式目标文件在链接行中最先出现也可被全体目标文件解析
            env.append("LDFLAGS", self._write_libc_compat())
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            # E011/E386: HMDFS 上 config.status 的 umask 077 临时目录不可写
            replace_in_file(self, configure, "umask 077", "umask 022",
                            strict=False)
            # 上游写死 /usr/local/lib/pkgconfig 前缀（R49：去掉共享系统
            # 前缀，只留 conan generators 目录）
            replace_in_file(
                self, configure,
                "PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:",
                "PKG_CONFIG_PATH=", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()  # R9: -j1

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 唯一产物是可执行文件（bin_PROGRAMS = wdfs）；VPATH 构建落在
        # <build_folder>/src/wdfs
        bin_src = os.path.join(self.build_folder, "src")
        copy(self, "wdfs", src=bin_src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        if not os.path.isfile(os.path.join(self.package_folder, "bin", "wdfs")):
            raise ConanInvalidConfiguration(
                f"wdfs binary not found under {bin_src}")

    def package_info(self):
        # 命令行工具，非库（mtpfs 先例）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

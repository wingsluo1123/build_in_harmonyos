#!/usr/bin/env python3
"""Conan recipe — mtpfs 1.1 (FUSE filesystem to mount MTP devices directly).

mtpfs 是一个 FUSE 用户态文件系统工具（bin_PROGRAMS = mtpfs，无库产物），
把 MTP 设备（手机/播放器）挂载成本地目录。上游 2012 年后基本停更，1.1 为
最终版本；cjd/mtpfs 仓库无 tag，规范源取 Debian 快照的 1.1 原始发行包。

构建要点（Windows 侧静态分析 + 历史配方先例推演，真机待验证项见 notes.md）：
  * tarball 自带 2012 年生成的 configure/Makefile.in，无需 bootstrap，也不声明
    automake/libtool tool_requires；configure 不含 AC_CANONICAL_HOST、无
    config.guess，因此不传 --build/--host（termrec/aa3d 之外的第三种 autotools
    形态：无平台检测，靠 CC/CFLAGS/LDFLAGS 直接驱动）。
  * 依赖发现全走 PKG_CHECK_MODULES（fuse >= 2.2 / libmtp >= 1.1.0 / glib-2.0
    gthread-2.0 gio-2.0）。pkg.m4 不会因为用户预设了 FUSE_CFLAGS 等变量而跳过
    探测，所以必须让 pkg-config 真的能解析到模块（abiword-plugin-* 先例）：
    - PkgConfigDeps 生成 glib 组件链 .pc（glib 配方已定义 glib-2.0/gthread-2.0/
      gio-2.0 组件与 requires 链），也生成 libmtp.pc（libmtp/1.1.21 已由
      【依赖项】适配发布，package_info 设 pkg_config_name="libmtp"，且其
      Requires 链把 libusb-1.0.pc 一并带进 PKG_CONFIG_PATH）；
    - libfuse 配方未定义 pkg_config_name（甚至 rmdir 了自带 pkgconfig 目录），
      PkgConfigDeps 不会生成 fuse.pc → 本配方在 generators_folder 手写
      fuse.pc（abiword 手写 glib-2.0.pc 同款先例），路径来自
      self.dependencies 的实际 package_folder，禁止硬编码缓存路径。
      （注：配方编写时 libmtp 尚为旧格式条目，曾手写 libmtp.pc；libmtp
      发布后改为直接使用依赖包自带 .pc，手写 stub 已删除——同名 stub 会
      覆盖 PkgConfigDeps 生成的真实 libmtp.pc。）
  * 链接闭包由 AutotoolsDeps 提供（CPPFLAGS/LDFLAGS/LIBS 聚合全部 host 依赖，
    含 libmtp 的 libusb-1.0 与 glib 的 pcre2/libffi 传递依赖）；pkg-config 只
    负责 PKG_CHECK_MODULES 的存在性检查。
  * libmad（mp3 元数据）为可选依赖，本配方按 termrec 对 curl 的同款处理
    --disable-mad 降级关闭：功能面收窄但不阻塞适配；libmad/libid3tag 均已
    归档，后续需要可再加依赖开启。
  * E011/E386 先例：HMDFS 上 config.status 的 ``umask 077 && mktemp -d`` 会
    造出构建用户写不进的临时目录（libfuse 先例是 sed umask 077→022）；SDK bash
    getcwd 问题用 SHELL=/bin/sh + 不设 CONFIG_SHELL 规避（termrec §12.38①）。
  * D3（libmtp/1.1.21 同款，真机第 1 轮实测）：OHOS musl 忽略 DT_RUNPATH，
    configure 的 conftest 运行期找不到 glib/libusb 共享库（errno 127），伪装成
    "cannot run C compiled programs"（E064 报错形态）→ 依赖包 libdirs 注入
    LD_LIBRARY_PATH 后 conftest 本机可跑通，无需 --host（E064 禁令保持）。
  * E085（真机第 1 轮实测）：libfuse.a 静态引用 pthread_cancel/pthread_setcancelstate
    而 OHOS SDK 链接期 libc 不导出；运行期 libc 有真实实现 → OHOS 下
    -Wl,--unresolved-symbols=ignore-all 保持符号未定义交运行期解析，规避
    E085 空桩方案 fuse 卸载 pthread_join 挂死问题。
  * FUSE_USE_VERSION=22 固定 fuse 2.x API，对应 libfuse/2.9.9（仓库已有，
    3.x 是 meson 且 API 不兼容，不可混用）。
  * R9: make -j1。
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


class MtpfsConan(ConanFile):
    name = "mtpfs"
    version = "1.1"
    description = "FUSE filesystem to mount MTP devices directly (MTP -> POSIX tree)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/cjd/mtpfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 标准脚手架（G1 完整性/libmtp 同款）；conandata patches 为空时 no-op
        export_conandata_patches(self)

    def requirements(self):
        # FUSE_USE_VERSION=22 -> fuse 2.x API；libfuse 3.x 不兼容，禁止升级
        self.requires("libfuse/2.9.9")
        # libmtp/1.1.21 已由【依赖项】适配发布（MateBook 真机第 7 轮全链验证、
        # W4 审计 pass），W0 时期的旧格式条目风险已解除。
        self.requires("libmtp/1.1.21")
        self.requires("glib/2.84.0.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported")
        # fuse 2.x API：显式拒绝 3.x 防止未来依赖漂移
        fuse_version = str(self.dependencies["libfuse"].ref.version)
        if not fuse_version.startswith("2."):
            raise ConanInvalidConfiguration(
                f"mtpfs needs libfuse 2.x (FUSE_USE_VERSION=22), got {fuse_version}")

    def layout(self):
        # src/ 解包 + 独立 build 目录（VPATH 构建；automake 生成物原生支持）
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_pkg_folder(self, ref_name):
        return self.dependencies[ref_name].package_folder

    def _write_handmade_pc(self, pc_dir):
        """手写 fuse.pc（abiword 手写 glib-2.0.pc 先例）。

        libfuse 配方没有定义 pkg_config_name 属性，PkgConfigDeps 不会为它
        生成 .pc；configure 的 PKG_CHECK_MODULES(FUSE, fuse>=2.2) 需要
        pkg-config 能解析到 fuse 模块。libmtp 模块名由依赖包自带的
        libmtp.pc 提供（pkg_config_name="libmtp"），不再手写——否则同名
        stub 会覆盖 PkgConfigDeps 生成的真实 .pc。内容只用于通过存在性
        检查与版本比较，真实 -I/-L/-l 链接闭包由 AutotoolsDeps 提供。
        """
        fuse_dir = self._dep_pkg_folder("libfuse")
        with open(os.path.join(pc_dir, "fuse.pc"), "w", encoding="utf-8") as f:
            f.write(f"""Name: fuse
Description: FUSE 2.x API headers/lib (provided by conan libfuse/2.9.9)
Version: 2.9.9
Libs: -L{fuse_dir}/lib -lfuse -lpthread
Cflags: -I{fuse_dir}/include
""")

    def generate(self):
        VirtualBuildEnv(self).generate()
        # 链接闭包：聚合全部 host 依赖（含 libusb-1.0/pcre2/libffi 传递依赖）
        AutotoolsDeps(self).generate()
        # glib 组件链 .pc（glib-2.0/gthread-2.0/gio-2.0/gobject-2.0）+ 依赖包
        # 自带 .pc（libmtp.pc/pkg_config_name="libmtp"，含 libusb-1.0 Requires 链）
        PkgConfigDeps(self).generate()
        # 仅 fuse.pc 需手写（libfuse 无 pkg_config_name）
        self._write_handmade_pc(self.generators_folder)

        tc = AutotoolsToolchain(self)
        # R1: 参数最少化；--disable-mad 关闭可选 mp3 元数据功能（termrec curl 降级先例）
        tc.configure_args.append("--disable-mad")
        # PKG_CHECK_MODULES 需要 pkg-config 真实解析到模块（abiword 先例：
        # conanbuild 不会自动注入 PKG_CONFIG_PATH，必须显式给）
        tc.configure_args.append(
            f"PKG_CONFIG_PATH={self.generators_folder}")
        env = tc.environment()
        # E386 (§12.38①): SDK bash getcwd 在 HMDFS 构建目录失败，autoconf 经
        # CONFIG_SHELL re-exec，route 到 /bin/sh（termrec 先例）
        env.unset("CONFIG_SHELL")
        env.define("SHELL", "/bin/sh")
        # D3 (libmtp/1.1.21 同款): OHOS musl 忽略 DT_RUNPATH，configure 的
        # conftest 运行期找不到 glib/libusb 共享库（errno 127），伪装成
        # "cannot run C compiled programs" → 依赖包 libdirs 注入
        # LD_LIBRARY_PATH（§12.38③ 先例）
        for _, dep in self.dependencies.host.items():
            for d in dep.cpp_info.libdirs:
                path = d if os.path.isabs(d) else os.path.join(
                    dep.package_folder, d)
                env.prepend_path("LD_LIBRARY_PATH", path)
        # E085 (musl 无 POSIX 线程取消 API): libfuse.a 静态引用 pthread_cancel/
        # pthread_setcancelstate，OHOS SDK 链接期 libc.so 不导出这两个符号
        # （E085 空桩方案会让 fuse 卸载线程 pthread_join 挂死）；真机实测
        # 运行期 /system/lib64/libc.so 有导出（pthread_cancel=T，
        # pthread_setcancelstate=W），--unresolved-symbols=ignore-all 链接后
        # 动态解析成功 → 保持符号未定义交由运行期 libc 提供（libfuse 归档
        # notes"由系统提供或需消费方处理"口径；-z undefs 等价）
        if str(self.settings.os) == "OHOS":
            env.append("LDFLAGS", "-Wl,--unresolved-symbols=ignore-all")
        tc.generate(env=env)

    def build(self):
        # 标准补丁入口（G1 完整性/libmtp 同款）：conandata patches 为空 no-op。
        # E011 的 umask 077→022 走下方内联 sed 而非补丁文件——refresh-patch
        # 政策将 autoconf 生成物（头部 "Generated by GNU Autoconf"）判为生成
        # 文件拒绝出补丁，configure 改动只能内联。
        apply_conandata_patches(self)
        # E011 (libfuse 先例): HMDFS 上 config.status 的 umask 077 临时目录
        # 不可写；sed 成 022。放在 build() 内联，模式缺失时静默跳过（老
        # configure 变体兼容）。
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            replace_in_file(self, configure, "umask 077", "umask 022",
                            strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()  # R9: -j1（Autotools.make 默认非并行）

    def package(self):
        # 唯一产物是 mtpfs 可执行文件（bin_PROGRAMS），aa3d 同款应用打包
        copy(self, "mtpfs", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # 命令行工具，非库（aa3d 先例）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

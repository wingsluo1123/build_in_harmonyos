#!/usr/bin/env python3
"""Conan recipe - OpenGrm Thrax 1.3.10 (WFST grammar compiler on top of OpenFst).

适配要点（鸿蒙 aarch64 / clang / libc++）：
  * configure.ac 声明 AC_DISABLE_STATIC，libthrax 以共享库为主产物
    （libthrax.so.139.0.0）。
  * 上游用裸 -l 链接 OpenFst。FST 类型注册对象（fst/register.h 的 REGISTER_FST）
    只通过静态初始化器可达，链接器按需抽取时会整体丢弃，导致运行期读取
    .far/.fst 报 `Unknown FST type "vector"`、import 语法直接段错误。
    patches/0002 与 0003 让命令行工具以 --whole-archive 拉入 libfst.a
    （0001 是 config.guess 的平台识别补丁）。
  * openfst 包内的 libtool 归档（.la）记录了构建机前缀 "//lib"，libtool 无法
    解析（`cannot find the library '//lib/libfst.la'`）。本配方在构建目录内做一份
    仅含静态库的私有目录并置于 LDFLAGS 首位，使 libtool 解析到 .a 而绕开 .la；
    不改动 Conan 缓存中的 openfst 包。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ThraxConan(ConanFile):
    name = "thrax"
    version = "1.3.10"
    description = "OpenGrm Thrax: a compiler and tools for weighted finite-state grammars over OpenFst"
    license = "Apache-2.0"
    homepage = "https://www.openfst.org/twiki/bin/view/GRM/Thrax"
    url = "https://www.openfst.org/twiki/bin/view/GRM/Thrax"

    # configure.ac 声明 AC_DISABLE_STATIC：libthrax 只以共享库形式产出。
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openfst/1.8.4.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-bin")
        # 私有静态库目录（build_folder 内，不污染任何共享前缀）：
        # 只拷贝 .a，不带 openfst 包里 libdir 为 "//lib" 的 .la。
        # extra_ldflags 落在 LDFLAGS 前段，保证它是链接行上的第一个 -L。
        fst = self.dependencies["openfst"]
        fst_libdir = fst.cpp_info.libdirs[0]
        static_dir = os.path.join(self.build_folder, "fst-static")
        copy(self, "libfst*.a", src=fst_libdir, dst=static_dir)
        tc.extra_ldflags.append(f"-L{static_dir}")
        # AutotoolsToolchain 只把 -D 宏写进 CPPFLAGS（自定义 CPPFLAGS 会被它覆盖，
        # 已实测），依赖的 include 路径不会自动注入；而 thrax 的 configure 对
        # fst/fst.h、far.h、pdt.h、mpdt.h 做 AC_CHECK_HEADER 硬校验（缺一个即
        # AC_MSG_ERROR 中止）。故把 openfst 头文件目录并入 CFLAGS/CXXFLAGS：
        # 该环境文件用 `${CXXFLAGS:-}${CXXFLAGS:+ }` 追加，不与 toolchain 标志冲突。
        fst_include = fst.cpp_info.includedirs[0]
        tc.extra_cflags.append(f"-I{fst_include}")
        tc.extra_cxxflags.append(f"-I{fst_include}")
        tc.generate()

    def build(self):
        # HMDFS FUSE 属主映射（E011/E223）：构建进程创建的 confXXXX 临时目录
        # 会经 FUSE 重映射 owner/权限（实测 0700 → 2771，other 仅 x），umask
        # 放开不能修 mktemp -d（恒 0700）但保证其余裸 mkdir 最大化可写；
        # mktemp 分支本体由 patches/0004 按 DRAFT-6507 CI 实证形式替换。
        os.umask(0o000)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["thrax"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

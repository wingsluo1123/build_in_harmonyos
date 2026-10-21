#!/usr/bin/env python3
"""Conan recipe for sleuthkit 4.12.1 - The Sleuth Kit digital forensics library.

Builds and installs libtsk (filesystem/volume forensics library) plus the
command-line toolkit (fls, icat, mmls, img_stat, tsk_recover, ...).

OHOS notes
----------
* Official autoconf release tarball ships a generated ``configure``; no
  autoreconf needed.
* Device ``uname`` returns ``HarmonyOS`` so ``config.guess`` cannot identify
  the triplet -> pass ``--build=aarch64-unknown-linux-ohos`` explicitly
  (0001 also teaches config.sub the ``*-*-linux-ohos`` triplet for any
  internal canonicalization).
* 0002: autoconf's generated ``configure`` creates its scratch directory
  with ``umask 077 && mktemp -d``; on the OHOS shared filesystem (HMDFS,
  setgid parent) that yields an unwritable ``drwx--S---`` directory
  (E114 / DRAFT-6507; same as tarsnap 1.0.41 and tnef 1.4.18).
* 0003: tsk/pool and tsk/util set ``-Werror``; the OHOS SDK headers emit
  warnings that would abort the build -> drop ``-Werror`` (keep -Wall
  -Wextra).
* E074: parallel make hits the HMDFS jobserver fifo EPERM -> ``make -j1``.
* All external deps are optional upstream (TSK_OPT_DEP_CHECK). zlib comes
  from the Conan package (AutotoolsDeps injects -I/-L/-l, R33); the
  remaining ones (afflib, libewf, libbfio, libvhdi, libvmdk, libvslvm)
  are explicitly disabled with ``--without-*`` for deterministic builds.
* Upstream ``make check`` TESTS are runtests.sh (needs $HOME/from_brian,
  not public) and test_libraries.sh (downloads disk images from Google
  Drive) -> cannot run offline by upstream design. The four check_PROGRAMS
  test binaries ARE executed for real: the recipe ships
  gen_upstream_fixtures.py, which generates six synthetic FAT/NTFS disk
  images at build time (pure stdlib) that satisfy the upstream assertions.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# 上游全部 check_PROGRAMS(tests/Makefile.am);make check 的 TESTS 只有两个
# 依赖外部镜像夹具的 shell 脚本,见模块 docstring。
_CHECK_PROGRAMS = (
    "read_apis", "fs_fname_apis", "fs_attrlist_apis", "fs_thread_test",
)


class SleuthkitConan(ConanFile):
    name = "sleuthkit"
    version = "4.12.1"
    description = ("The Sleuth Kit (TSK): digital forensics library libtsk "
                   "and CLI tools (fls, icat, mmls, img_stat, tsk_recover, ...)")
    license = ("IBM Public License v1.0 (libtsk) / LGPLv2+ 及 BSD 等捆绑组件许可"
               "(见 COPYING)")  # 顶层 LICENSE.md: tsk 主体 IPL 1.0,tools/tests 另有声明
    homepage = "https://www.sleuthkit.org/"
    url = "https://github.com/sleuthkit/sleuthkit/releases"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sleuthkit OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0: 上游唯一默认启用的外部可选依赖是 zlib(TSK_OPT_DEP_CHECK,
        # configure.ac:162);afflib/libewf/libbfio/libvhdi/libvmdk/libvslvm
        # 用 --without-* 显式关闭。zlib/1.3.2 已在制品仓发布,MateBook 阶段
        # 用 conan download 复核二进制包(R35,禁用 conan list 判断)。
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)  # in-source 构建(autotools 上游默认布局)

    def export_sources(self):
        # conandata.yml 声明的 3 个补丁必须随配方导出,否则 source() 无从应用
        export_conandata_patches(self)
        # 合成夹具生成器随配方导出(source() 后在 source_folder 可用,
        # build() 用它生成上游测试所需磁盘镜像)
        # Conan 2 API:self.copy() 已随 Conan 1 移除,用 conan.tools.files.copy
        copy(self, "gen_upstream_fixtures.py",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsToolchain(self).generate()
        # 把 zlib 的 -I/-L/-l 注入 conanbuild 环境的 CPPFLAGS/LDFLAGS/LIBS(R33)
        AutotoolsDeps(self).generate()

    def _compiler(self, name, fallback):
        # R33: 编译器从 Conan conf 获取,禁止裸用 shell 环境变量
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        src = self.source_folder
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        # config.guess 认不出 HarmonyOS,显式给三元组(tarsnap/tnef 先例;
        # 0001 同时让 config.sub 认识 *-*-linux-ohos)
        libtool_flags = ("--with-pic " +
                         ("--enable-shared --disable-static"
                          if self.options.shared else
                          "--disable-shared --enable-static"))
        self.run('CC="{}" CXX="{}" ./configure --build=aarch64-unknown-linux-ohos '
                 '--prefix="{}" {} '
                 "--without-afflib --without-libewf --without-libbfio "
                 "--without-libvhdi --without-libvmdk --without-libvslvm"
                 .format(cc, cxx, self.package_folder, libtool_flags),
                 cwd=src, env="conanbuild")
        # E074: make -j1
        self.run("make -j1", cwd=src, env="conanbuild")
        # 上游 make check 的 TESTS(runtests.sh / test_libraries.sh)按上游
        # 设计依赖非公开/联网镜像夹具,离线必然失败(见模块 docstring)。
        # check_PROGRAMS 的 4 个测试程序必须真实执行:release tarball 不含
        # 任何磁盘镜像,配方自带 gen_upstream_fixtures.py(纯 Python 标准库)
        # 在构建期生成 6 个满足上游断言的合成 FAT12/16/32 + NTFS 镜像,
        # 以下全部真实运行,任一失败即 create 失败。
        self.run("make -j1 " + " ".join(_CHECK_PROGRAMS),
                 cwd=os.path.join(src, "tests"), env="conanbuild")
        fixdir = os.path.join(self.build_folder, "upstream_fixtures")
        self.run('"{}" gen_upstream_fixtures.py "{}"'.format(
            sys.executable, fixdir), cwd=src, env="conanbuild")
        tests = os.path.join(src, "tests")
        # read_apis:6 个子测试全部执行(fat12 / fat slack / fat recover /
        # ntfs fe / ntfs comp / ntfs slack+ADS),全过才退出 0
        self.run("./read_apis " + fixdir, cwd=tests, env="conanbuild")
        # fs_fname_apis:fat12 与 fe NTFS 的目录打开/遍历一致性测试
        self.run("./fs_fname_apis " + fixdir, cwd=tests, env="conanbuild")
        # fs_attrlist_apis:fat12(47/1)与 fe NTFS(35/3、9/7 属性)取属性测试
        self.run("./fs_attrlist_apis " + fixdir, cwd=tests, env="conanbuild")
        # fs_thread_test:按上游 runtests.sh 的确定性协议——先单线程跑一遍
        # 存为基准,重跑后 diff 两个日志;fat 与 ntfs 各做一组
        self.run("./fs_thread_test -f fat {}/fat32.dd 1 1 && "
                 "mv thread-0.log base.log && "
                 "./fs_thread_test -f fat {}/fat32.dd 1 1 && "
                 "diff base.log thread-0.log".format(fixdir, fixdir),
                 cwd=tests, env="conanbuild")
        self.run("./fs_thread_test -f ntfs {}/ntfs-comp-1.img 1 1 && "
                 "mv thread-0.log base.log && "
                 "./fs_thread_test -f ntfs {}/ntfs-comp-1.img 4 3 && "
                 "diff base.log thread-0.log".format(fixdir, fixdir),
                 cwd=tests, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["tsk"]
        self.cpp_info.bindirs = ["bin"]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""netpbm 10.73.42 — OpenHarmony PC (aarch64) 适配配方

构建体系
--------
netpbm 不使用 autotools / CMake，而是自带一套 config.mk + 递归 GNU make 的私有构建
体系：configure.pl 是**交互式** Perl 脚本（逐项提问、不接受 --prefix），无法在 CI
无人值守环境下运行。因此本配方在 generate() 阶段以上游 config.mk.in 为底稿直接生成
config.mk（末尾追加覆写块，利用『后定义覆盖先定义』语义生效），随后调用上游的
make / make package 完成编译与安装。

适配要点
--------
1. 编译器与链接器取自 Conan profile 的 tools.build:compiler_executables，依赖的头文件
   与库路径取自各依赖的 cpp_info（不依赖构建 shell 中的 ${CC}/${CFLAGS} 环境变量，
   也不写死任何本机绝对路径）。
2. PNG / JPEG / TIFF 默认全部打开：关闭会产出"残废包"——pnmtopng、pnmtotiff、
   pnmtojpeg 等工具不构建，上游 png-roundtrip / tiff-roundtrip 用例必然失败。
3. OMIT_NETWORK=Y 只把并行加速模块（psocket / parallel）换成 noparallel 桩，不裁剪
   任何图像功能；构建环境无网络配置，上游默认要求网络可用。
4. 上游写死解释器路径的 Perl 工具（`#!/usr/bin/perl` 与 `#! /usr/bin/perl` 两种形态，
   如 manweb / pbmtox10bm）安装后统一改写为 `#!/usr/bin/env perl`（OHOS 无 /usr/bin/perl，
   直接执行报 "bad interpreter"）；改写时丢弃 shebang 中的解释器参数（如 -w），
   因为 env 只接受一个程序名。其余脚本是 `#!/bin/sh` + `exec perl -x` 形式，无需处理。
5. 包内 link/ 目录是上游老式 installnetpbm 流程的便捷入口（内含 libnetpbm.a 整份
   副本），Conan 消费方走 lib/ 即可，安装后移除以免产物重复。
"""

import os
import re

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               export_conandata_patches, get, load, rmdir, save)


class NetpbmConan(ConanFile):
    name = "netpbm"
    version = "10.73.42"
    description = ("netpbm：便携式位图工具箱 —— libnetpbm 库 + 300 余个图像格式转换/处理"
                   "命令行工具（原生 PBM/PGM/PPM/PAM，并支持 PNG/JPEG/TIFF 等）")
    license = "BSD-3-Clause"
    homepage = "https://netpbm.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "with_png": [True, False],
        "with_jpeg": [True, False],
        "with_tiff": [True, False],
    }
    default_options = {
        "shared": True,
        "with_png": True,
        "with_jpeg": True,
        "with_tiff": True,
    }

    # ── 出口源码（补丁管线）─────────────────────────────────────────────
    def export_sources(self):
        # 本配方当前不含补丁（上游源码可直接构建）；出口保留标准实现，
        # 后续如需补丁，在 conandata.yml 声明 patches 即可自动生效。
        export_conandata_patches(self)

    # ── 依赖 ────────────────────────────────────────────────────────────
    def requirements(self):
        self.requires("zlib/1.3.1.1")
        if self.options.with_png:
            self.requires("libpng/1.6.58")
        if self.options.with_jpeg:
            self.requires("libjpeg-turbo/3.2.0")
        if self.options.with_tiff:
            self.requires("libtiff/4.7.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── 生成 config.mk ──────────────────────────────────────────────────
    def generate(self):
        # 只准备构建环境；config.mk 必须等 source() 取到源码后（build 阶段）才能生成
        VirtualBuildEnv(self).generate()

    def _write_config_mk(self, path):
        template = load(self, os.path.join(self.source_folder, "config.mk.in"))
        save(self, path, template + self._config_overrides())

    def _config_overrides(self):
        """以配置变量形式覆写构建参数（netpbm 的 config.mk 后定义生效）。"""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("clang") or "clang"
        cxx = compilers.get("cpp") or compilers.get("clang++") or "clang++"

        includedirs, libdirs = [], []
        for dependency in self.dependencies.host.values():
            cpp_info = dependency.cpp_info.aggregated_components()
            includedirs.extend(cpp_info.includedirs)
            libdirs.extend(cpp_info.libdirs)
        includedirs = self._unique(includedirs)
        libdirs = self._unique(libdirs)

        # 运行期查找：本包 lib/ 与各依赖 lib/ 写入 RPATH（$$ORIGIN/../lib 对 bin/ 下的
        # 工具解析到本包 lib/，依赖库目录用绝对路径），保证产物开箱即用。
        # 注意必须写双美元符：config.mk 是 Makefile，单个 $O 会被 make 当变量展开成空，
        # 生成 RIGIN/../lib 这种以 CWD 为基准的无效路径（实测 ELF RUNPATH 可证）。
        runtime_dirs = ["$$ORIGIN/../lib"] + list(libdirs)
        flags = self._optimization_flags()

        lines = [
            "",
            "####################################################################",
            "# OpenHarmony 适配覆写块（由 conanfile.py 自动生成，请勿手工修改）",
            "# config.mk 采用『后定义覆盖先定义』语义，本块位于文件末尾故生效。",
            "####################################################################",
            "CC = %s" % cc,
            "CXX = %s" % cxx,
            "LD = $(CC)",
            "LINKERISCOMPILER = Y",
            "CC_FOR_BUILD = $(CC)",
            "LD_FOR_BUILD = $(LD)",
            "AR = ar",
            "RANLIB = ranlib",
            "CFLAGS = -fPIC %s %s" % (flags, " ".join("-I" + d for d in includedirs)),
            "CXXFLAGS = -fPIC -stdlib=libc++ %s %s" % (
                flags, " ".join("-I" + d for d in includedirs)),
            "CFLAGS_SHLIB = -fPIC",
            "LDFLAGS = %s -Wl,-rpath,%s" % (
                " ".join("-L" + d for d in libdirs),
                ":".join("'%s'" % d for d in runtime_dirs)),
            "NETPBMLIBTYPE = %s" % ("unixshared" if self.options.shared else "unixstatic"),
            "STATICLIB_TOO = %s" % ("Y" if self.options.shared else "N"),
            # 并行加速模块需要网络配置，构建环境不具备 → 换成 noparallel 桩（不裁剪功能）
            "OMIT_NETWORK = Y",
            # X11 / XML2 / JBIG 不引入外部依赖（保持上游内建实现）
            "X11LIB = NONE",
            "XML2LIB = NONE",
            "PKGMANDIR = man",
            # 上游默认把安装目录/测试结果目录指向 /tmp（OHOS 上 /tmp 为只读）→ 改用可写目录
            "PKGDIR_DEFAULT = %s" % self.package_folder,
            "RESULTDIR_DEFAULT = %s" % os.path.join(self.build_folder, "netpbm-test"),
        ]

        if self.options.with_png:
            lines += [
                "# libpng 1.6.x：PNGVER=16 使上游 pkg-config/libpng-config 探测与链接库名一致",
                "PNGVER = 16",
                "PNGLIB = %s" % self._link_flags("libpng"),
                "PNGHDR_DIR = %s" % self._include_dir("libpng"),
            ]
        if self.options.with_jpeg:
            lines += [
                "JPEGLIB = %s" % self._link_flags("libjpeg-turbo"),
                "JPEGHDR_DIR = %s" % self._include_dir("libjpeg-turbo"),
            ]
        if self.options.with_tiff:
            lines += [
                "TIFFLIB = %s" % self._link_flags("libtiff"),
                "TIFFHDR_DIR = %s" % self._include_dir("libtiff"),
            ]
        lines += [
            "ZLIB = %s" % self._link_flags("zlib"),
            "ZHDR_DIR = %s" % self._include_dir("zlib"),
        ]
        return "\n".join(lines) + "\n"

    def _optimization_flags(self):
        return {
            "Debug": "-g -O0",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")

    def _cpp_info(self, name):
        return self.dependencies[name].cpp_info.aggregated_components()

    def _link_flags(self, name):
        return " ".join("-l" + lib for lib in self._cpp_info(name).libs)

    def _include_dir(self, name):
        dirs = self._cpp_info(name).includedirs
        return dirs[0] if dirs else ""

    @staticmethod
    def _unique(items):
        seen, result = set(), []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    # ── 编译 / 打包 ─────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)  # 当前无补丁：空操作，保持标准管线
        self._write_config_mk(os.path.join(self.source_folder, "config.mk"))
        with chdir(self, self.source_folder):
            self.run("make -j%s" % build_jobs(self), env="conanbuild")

    def package(self):
        copy(self, "copyright_summary", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*LICENSE*", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "licenses"))

        with chdir(self, self.source_folder):
            # 上游 netpbm-init_package 要求安装目标目录**不存在**（否则报
            # "Directory ... already exists"），而 conan 会预先创建 package_folder，
            # 故先删除、交由上游安装脚本自行创建。
            rmdir(self, self.package_folder)
            self.run("make package pkgdir=%s" % self.package_folder, env="conanbuild")

        # 上游老式安装器的便捷目录（含 libnetpbm.a 副本），Conan 消费方不需要
        rmdir(self, os.path.join(self.package_folder, "link"))
        self._complete_link_artifacts()
        self._fix_perl_shebang()

    def _complete_link_artifacts(self):
        """补齐 `-lnetpbm` 所需的开发用产物。

        上游 `make package` 只往 lib/ 安装带版本号的运行库（libnetpbm.so.11.73 及
        soname 软链 libnetpbm.so.11），开发用的 libnetpbm.so 软链与静态库
        libnetpbm.a 都留在构建树里，导致消费方无法链接（CMakeDeps 报
        "Library 'netpbm' not found in package"）。此处按标准布局补齐。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return

        sonames = sorted(name for name in os.listdir(libdir)
                         if name.startswith("libnetpbm.so."))
        dev_link = os.path.join(libdir, "libnetpbm.so")
        if sonames and not os.path.lexists(dev_link):
            os.symlink(sonames[0], dev_link)
            self.output.info("已补齐开发用软链: lib/%s -> %s" % (os.path.basename(dev_link),
                                                               sonames[0]))

        static_src = os.path.join(self.source_folder, "lib")
        if (os.path.isfile(os.path.join(static_src, "libnetpbm.a"))
                and not os.path.exists(os.path.join(libdir, "libnetpbm.a"))):
            copy(self, "libnetpbm.a", src=static_src, dst=libdir)
            self.output.info("已补入静态库: lib/libnetpbm.a")

    def _fix_perl_shebang(self):
        """把写死 /usr/bin/perl 的 Perl 工具改为 /usr/bin/env perl（OHOS 无该路径）。

        实测踩到的两个坑（缺一即产物运行期报错）：
          1. 上游同时存在 `#!/usr/bin/perl` 与 `#! /usr/bin/perl`（`#!` 后有空格）两种形态，
             必须都覆盖，否则漏改的脚本执行报 "bad interpreter: No such file or directory"；
          2. shebang 的解释器参数（如 `-w`）不能留在 env 之后——env 只接受一个程序名，
             `#!/usr/bin/env perl -w` 会被解释成执行名为 "perl -w" 的程序，实测报
             `env: exec perl -w: No such file or directory`；故改写时丢弃该参数
             （`-w` 仅开启额外告警，不影响功能）。
        """
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        pattern = re.compile(rb"^#!\s*(?:/usr/bin/env\s+perl|/usr/bin/perl)(\s+[^\n]*)?$")
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            with open(path, "rb") as handle:
                content = handle.read()
            if not content.startswith(b"#!"):
                continue
            end = content.find(b"\n")
            head = content if end < 0 else content[:end]
            tail = b"" if end < 0 else content[end:]
            new_head = pattern.sub(b"#!/usr/bin/env perl", head)
            if new_head != head:
                with open(path, "wb") as handle:
                    handle.write(new_head + tail)
                self.output.info("已修正 Perl 解释器路径: bin/%s" % name)

    # ── 消费信息 ────────────────────────────────────────────────────────
    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "netpbm")
        self.cpp_info.set_property("pkg_config_name", "netpbm")
        self.cpp_info.libs = ["netpbm"]
        # 本包同时交付 300+ 个命令行工具（bin/），显式声明 bindirs 供 L0k/R38 识别
        self.cpp_info.bindirs = ["bin"]
        # 上游头文件装在 include/netpbm/：两种包含方式都可用
        #   #include <netpbm/pam.h>   （-I<prefix>/include）
        #   #include "pam.h"          （-I<prefix>/include/netpbm）
        self.cpp_info.includedirs = ["include", os.path.join("include", "netpbm")]
        # RGB 颜色数据库（ppmhist 等工具使用）；上游默认去系统 /usr/share 下找，OHOS 无
        self.runenv_info.define_path(
            "RGBDEF", os.path.join(self.package_folder, "misc", "rgb.txt"))

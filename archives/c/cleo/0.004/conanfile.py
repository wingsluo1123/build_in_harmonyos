#!/usr/bin/env python3
"""Conan recipe for cleo (App::Cleo) 0.004 — Perl CLI diff viewer.

cleo 是 Perl CLI 库（App::Cleo），走 ExtUtils::MakeMaker 构建系统
（Makefile.PL → make → make install），非 C/C++ CMake/Meson。
依赖 5 个 Perl 模块（Term::ReadKey/Term::ANSIColor/File::Slurp/Time::HiRes/
ExtUtils::MakeMaker），通过 Conan Perl 生态包提供。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class CleoConan(ConanFile):
    name = "cleo"
    version = "0.004"
    settings = "os", "build_type", "arch"
    # Perl 模块无 compiler 设置（不编译 C/C++）

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Perl 模块依赖（制品仓已就绪，resolve-deps ✅）
        self.requires("perl-Term-ReadKey/2.38")
        self.requires("perl-Term-ANSIColor/5.01")
        self.requires("perl-File-Slurp/9999.32")
        self.requires("perl-Time-HiRes/1.9742")
        self.requires("perl-ExtUtils-MakeMaker/7.70")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；cleo 无补丁
        # aireview P3: 勿调 apply_conandata_patches（该函数属 source() 非 export_sources，误调致 NameError）
        pass

    def generate(self):
        # Perl 构建无 toolchain 需生成
        pass

    def build(self):
        # Perl 构建系统：Makefile.PL → make
        # PERL5LIB 注入依赖模块路径（Conan Perl 包 package_folder/lib/perl5）
        perl_lib = []
        for dep in ("perl-Term-ReadKey", "perl-Term-ANSIColor",
                    "perl-File-Slurp", "perl-Time-HiRes",
                    "perl-ExtUtils-MakeMaker"):
            pkg = self.dependencies[dep].package_folder
            perl_lib.append(os.path.join(pkg, "lib", "perl5"))
        perl5lib = os.pathsep.join(perl_lib)
        # 1. perl Makefile.PL PREFIX=$package_folder
        self.run(f'perl Makefile.PL INSTALL_BASE={os.path.join(self.build_folder, "staging")}',
                 cwd=self.source_folder, env=["PERL5LIB=" + perl5lib])
        # 2. make
        self.run("make", cwd=self.source_folder, env=["PERL5LIB=" + perl5lib])

    def package(self):
        # make install 安装到 staging
        self.run("make install", cwd=self.source_folder, env=["PERL5LIB="])
        # copy staging 到 package_folder
        copy(self, "*", src=os.path.join(self.build_folder, "staging"),
             dst=self.package_folder)

    def package_info(self):
        # cleo 是 Perl CLI 脚本（bin/cleo），非链接型 lib
        self.cpp_info.libs = []
        # aireview P1: 补 cleo 自身 PERL5LIB 路径，避消费者 perl -c 找不到 App::Cleo 模块
        for dep in ("perl-Term-ReadKey", "perl-Term-ANSIColor",
                    "perl-File-Slurp", "perl-Time-HiRes",
                    "perl-ExtUtils-MakeMaker"):
            pkg = self.dependencies[dep].package_folder
            self.runenv_info.append_path("PERL5LIB", os.path.join(pkg, "lib", "perl5"))
        # cleo 自身模块路径（lib/perl5/.../App/Cleo.pm）
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
        # aireview P3: 删 self.info.site 无效 API（Conan 2.x 无此属性，应改 self.info.settings ego if needed）

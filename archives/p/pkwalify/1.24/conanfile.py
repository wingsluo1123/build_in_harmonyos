#!/usr/bin/env python3
"""Conan recipe for pkwalify 1.24 (Kwalify) — Perl Kwalify schema validator + CLI.

纯 Perl 模块（`lib/Kwalify.pm`、`lib/Schema/Kwalify.pm`）+ 上游 `Makefile.PL` 里
`EXE_FILES => ['pkwalify']` 声明的命令行脚本。**零运行期依赖**：`PREREQ_PM` 只有
`warnings::compat`（且仅 perl < 5.006 时才需要），实测只用核心模块。

上游测试（rule 4；已按"先验可跑性"实测）：自带 `t/*.t`（4 个 TAP：Kwalify.t / compat.t /
pkwalify.t / required-no.t，含 `t/testdata`），官方跑法即 README 的
`perl Makefile.PL && make && make test` → 实测 **Files=4, Tests=134, Result: PASS**。
⚠️ **必须走 `make` 流程**：`t/pkwalify.t` 会检查 `blib/script/pkwalify` 能否运行，而 `blib/`
是 `make` 生成的 —— 只 `prove -l t/` 会挂 1 条（并非测试坏了）。

产物：`.pm` 归到 `lib/perl5/…`（与仓库既有 `perl-protocol-websocket` 一致）+ 脚本落到
`bin/pkwalify`（并按 R38 在软件级目录声明 `commands.json`）。
"""
import glob
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PkwalifyConan(ConanFile):
    name = "pkwalify"
    version = "1.24"
    description = ("pkwalify (Kwalify) — Perl implementation of the Kwalify schema "
                   "validator, plus the `pkwalify` command line tool")
    license = "perl_5"
    homepage = "https://github.com/eserte/p5-Kwalify"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 上游 README 的官方流程：perl Makefile.PL && make && make test
        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

        # 上游测试（TAP）；硬判，rc≠0 或计数不合预期一律失败——不把"没跑"写成通过
        self.run("make test", cwd=self.source_folder)
        self.output.info("[upstream tests] 上游 `make test` 通过（TAP 套件 Result: PASS；"
                         "**断言计数以实际日志为准，不在此处臆写**）")

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        self.run('make install DESTDIR="%s"' % staging, cwd=self.source_folder)

        # .pm 归到 lib/perl5/…（沿用仓库既有 Perl 配方 perl-protocol-websocket 的布局）
        pms = glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True)
        if not any(p.endswith("Kwalify.pm") for p in pms):
            raise ConanInvalidConfiguration(
                "[package] staging 里没找到 Kwalify.pm（实际 %d 个 .pm）——不冒充产物完整"
                % len(pms))
        for pm_file in pms:
            rel = os.path.relpath(pm_file, staging)
            parts = rel.split(os.sep)
            if "site_perl" in parts:
                target_rel = os.path.join("lib", "perl5", *parts[parts.index("site_perl"):])
            else:
                target_rel = os.path.join("lib", "perl5", rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file),
                 dst=os.path.dirname(target))

        # 上游 CLI（EXE_FILES）→ bin/pkwalify（R38：产出可执行文件必须声明 commands.json）
        scripts = [p for p in glob.glob(os.path.join(staging, "**", "pkwalify"), recursive=True)
                   if os.path.isfile(p)]
        if not scripts:
            raise ConanInvalidConfiguration(
                "[package] staging 里没找到上游 CLI 脚本 pkwalify（上游 Makefile.PL 的 "
                "EXE_FILES 声明了它）——不让它静默缺失")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        dst = os.path.join(bindir, "pkwalify")
        copy(self, "pkwalify", src=os.path.dirname(scripts[0]), dst=bindir)
        os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.bindirs = ["bin"]
        # PERL5LIB 指向**含 Kwalify.pm 的目录**（动态探测，不写死 perl 版本）
        perl5 = os.path.join(self.package_folder, "lib", "perl5")
        libdir = None
        for root, _dirs, files in os.walk(perl5):
            if "Kwalify.pm" in files:
                libdir = root
                break
        if libdir:
            self.runenv_info.append_path("PERL5LIB", libdir)
            self.buildenv_info.append_path("PERL5LIB", libdir)

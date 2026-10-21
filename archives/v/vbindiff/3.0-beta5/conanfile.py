#!/usr/bin/env python3
"""Conan recipe for vbindiff 3.0-beta5 (Visual Binary Diff).

The upstream release archive already contains ``configure`` and
``Makefile.in``, so the HarmonyOS device never regenerates Autotools files.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# E386 家族（AGENTS §12.1 首选修法）：profile 的 [buildenv] 把 CONFIG_SHELL 与
# SHELL 指向 /data/service/hnp/bin/bash，autoconf 的 configure 会用 $CONFIG_SHELL
# 重新 exec 自己，所以那条路径不可用时 configure 直接终止。手工调用 configure 时
# 只剥掉这一层 shell 选择，工具链环境（CC/CXX/flags）原样保留。
SH = "env -u CONFIG_SHELL SHELL=/bin/sh"

# 手工调用 configure 必须自带 AutotoolsToolchain 默认注入的目录参数，否则 DESTDIR
# 打包会落到 /bin 而不是 <package_folder>/bin。这六项取自本任务上一次构建生成的
# conanbuild.conf（[toolchain] configure_args），其中没有 --host/--build。
CONFIGURE_ARGS = (
    "--prefix=/"
    " '--bindir=${prefix}/bin'"
    " '--sbindir=${prefix}/bin'"
    " '--libdir=${prefix}/lib'"
    " '--includedir=${prefix}/include'"
    " '--oldincludedir=${prefix}/include'"
)


class VbindiffConan(ConanFile):
    name = "vbindiff"
    version = "3.0-beta5"
    description = "Visual Binary Diff: curses viewer and differ for binary files"
    license = "GPL-2.0-or-later"
    homepage = "https://www.cjmweb.net/vbindiff/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("diff", "hexdump", "curses", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("vbindiff is supported only on Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("vbindiff is packaged for the aarch64 target")

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def _repair_configure_temp_dir(self):
        """Make config.status usable on HMDFS.

        Autoconf 2.69 embeds a temp-dir dance in the ``config.status`` it
        writes: ``(umask 077 && mktemp -d "./confXXXXXX")``.  On HMDFS the
        Toybox ``mktemp -d`` creates the directory as ``2700`` and a restricted
        ``umask 077`` inherits the parent setgid bit as an uppercase ``S``, so
        the ``echo 'BEGIN {' >"$ac_tmp/subs1.awk"`` write fails and configure
        dies with ``could not setup config files machinery``.  A plain
        ``mkdir`` instead inherits a writable ``drwxrws--x`` directory, so
        replace the mktemp branch while still creating a private temp dir.
        """
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self,
            configure,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"',
            'tmp=./conf$$-$RANDOM && mkdir "$tmp"',
            strict=False,
        )

    def _ensure_executable_helpers(self):
        """Tar extraction on HMDFS does not always keep the exec bit."""
        for relative in ("configure", "install-sh", "missing", "depcomp"):
            path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

    def _ncurses_flags(self):
        dep = self.dependencies["ncurses"]
        return (
            os.path.join(dep.package_folder, "include"),
            os.path.join(dep.package_folder, "lib"),
            " ".join(f"-l{item}" for item in dep.cpp_info.libs),
        )

    def build(self):
        apply_conandata_patches(self)
        self._repair_configure_temp_dir()
        self._ensure_executable_helpers()
        # Upstream probes for the non-wide library names (ncurses, tinfo,
        # panel) while the published ncurses/6.6 package only ships the wide
        # variants, and the Autotools toolchain does not fold dependency
        # cpp_info into the compilation flags.  Pass them as configure
        # variables instead of shell globals: LIBS lands in the substituted
        # Makefile and is appended *after* the objects by the automake link
        # rule, which is the order a static archive link requires.  CPPFLAGS
        # is the only overridden variable because the toolchain contributes no
        # defines here, while LDFLAGS and CXXFLAGS keep the toolchain values.
        include_dir, lib_dir, libs = self._ncurses_flags()
        configure_path = os.path.join(self.source_folder, "configure")
        self.run(
            f'{SH} "{configure_path}" {CONFIGURE_ARGS} '
            f'CPPFLAGS=-I{include_dir} LIBS="-L{lib_dir} {libs}"',
            env="conanbuild",
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # The upstream 3.0_beta5 release registers no test cases, so this
        # invokes automake's empty check target: it proves the test entry
        # point runs without pretending a suite exists.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []

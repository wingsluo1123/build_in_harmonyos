#!/usr/bin/env python3
"""Conan recipe — tcpkali 1.1.1 (Autotools)

tcpkali is a high-performance TCP/WebSocket load testing tool based on libev.
Core executable: tcpkali (CLI tool for TCP/WebSocket stress testing).

OHOS adaptation notes:
- OHOS musl libc lacks __containerof/QUEUE_TYPEOF macros in sys/queue.h
- OHOS musl libc does not provide sys/sysctl.h
- Source archive has no pre-generated configure; requires autoreconf -fi
- ncurses statically linked (system prebuilt), binary only depends on libc.so
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TcpkaliConan(ConanFile):
    name = "tcpkali"
    version = "1.1.1"
    package_type = "application"
    description = "High-performance TCP/WebSocket load testing tool based on libev"
    license = "BSD-2-Clause"
    homepage = "https://github.com/MumiaiGene/tcpkali"
    url = ""

    # R32: settings.os must allow both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses is available as system prebuilt (like bash recipe).
        # Not declared as conan requires to avoid /lib pollution (R26).
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: ncurses is a system library, static link to avoid polluting /lib
        tc.extra_ldflags.append("-static")
        # Force build triplet for OHOS cross-compilation (config.guess may not
        # recognize HarmonyOS)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        # OHOS: umask 000 needed for config.status temp dir creation
        os.umask(0)
        apply_conandata_patches(self)
        # Ensure autotools (automake, aclocal, libtoolize) are in PATH.
        # CI worker has them in system PATH; local dev machines may have them
        # installed via cmd-pkgs in ~/usr/local/bin.
        for prefix in (
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
            "/data/service/hnp/bin",
        ):
            if os.path.isdir(prefix) and prefix not in os.environ.get("PATH", ""):
                os.environ["PATH"] = prefix + os.pathsep + os.environ.get("PATH", "")
        # Ensure aclocal can find autoconf-archive m4 macros
        for aclocal_dir in (
            os.path.join(os.path.expanduser("~"), "usr", "local", "share", "aclocal"),
            "/data/service/hnp/autoconf.org/autoconf_2.72/share/aclocal",
        ):
            if os.path.isdir(aclocal_dir):
                existing = os.environ.get("ACLOCAL_PATH", "")
                if aclocal_dir not in existing:
                    os.environ["ACLOCAL_PATH"] = (
                        aclocal_dir + os.pathsep + existing if existing else aclocal_dir
                    )
                break
        # GitHub archive tarball is missing m4/ directory (exists in repo but
        # not in archive). Create it and populate with required macros.
        m4_dir = os.path.join(self.source_folder, "m4")
        os.makedirs(m4_dir, exist_ok=True)
        # ax_check_compile_flag.m4: from autoconf-archive (may be on system)
        for search_dir in [
            os.path.join(os.path.expanduser("~"), "usr", "local", "share", "aclocal"),
            "/data/service/hnp/autoconf.org/autoconf_2.72/share/aclocal",
        ]:
            src = os.path.join(search_dir, "ax_check_compile_flag.m4")
            if os.path.isfile(src):
                import shutil
                shutil.copy2(src, os.path.join(m4_dir, "ax_check_compile_flag.m4"))
                break
        # ax_pthread.m4: from autoconf-archive
        for search_dir in [
            os.path.join(os.path.expanduser("~"), "usr", "local", "share", "aclocal"),
            "/data/service/hnp/autoconf.org/autoconf_2.72/share/aclocal",
        ]:
            src = os.path.join(search_dir, "ax_pthread.m4")
            if os.path.isfile(src):
                import shutil
                shutil.copy2(src, os.path.join(m4_dir, "ax_pthread.m4"))
                break
        # ax_make_optional_include.m4: custom tcpkali macro (not in autoconf-archive,
        # missing from GitHub archive tarball but present in upstream repo)
        ax_make_opt = os.path.join(m4_dir, "ax_make_optional_include.m4")
        if not os.path.isfile(ax_make_opt):
            save(self, ax_make_opt,
                 "# Check to see how 'make' supports optional includes.\n"
                 "\n"
                 "# serial 1\n"
                 "\n"
                 "# AX_CHECK_GNU_STYLE_OPTIONAL_INCLUDE()\n"
                 "# -------------------------------------\n"
                 "AC_DEFUN([AX_CHECK_GNU_STYLE_OPTIONAL_INCLUDE],\n"
                 "[am_make=${MAKE-make}\n"
                 "AC_MSG_CHECKING([for style of optional includes used by $am_make])\n"
                 "cat > confmf << 'END'\n"
                 "-include confinc.nonexistent\n"
                 "all:\n"
                 "\t@-:\n"
                 "END\n"
                 "_am_result=none\n"
                 'if $am_make -s -f confmf 2>/dev/null; then _am_result=GNU; fi\n'
                 'AM_CONDITIONAL([GNU_STYLE_OPTIONAL_INCLUDE], [test "x$_am_result" = "xGNU"])\n'
                 'AC_MSG_RESULT([$_am_result])\n'
                 "rm -f confmf\n"
                 "])\n")
        # deps/libstatsd/libstatsd.m4: missing from commit 6c23ac28 archive
        # (added in a later commit on the master branch)
        libstatsd_m4 = os.path.join(self.source_folder, "deps", "libstatsd", "libstatsd.m4")
        if not os.path.isfile(libstatsd_m4):
            save(self, libstatsd_m4,
                 "#                                               -*- Autoconf -*-\n"
                 "# Process this file with autoconf to produce a configure script.\n"
                 "\n"
                 "LT_INIT\n"
                 "\n"
                 "# Checks for programs.\n"
                 "AC_PROG_CC\n"
                 "\n"
                 "# Checks for libraries.\n"
                 "\n"
                 "# Checks for header files.\n"
                 "AC_CHECK_HEADERS([arpa/inet.h netdb.h netinet/in.h stdlib.h string.h sys/socket.h unistd.h])\n"
                 "\n"
                 "# Checks for typedefs, structures, and compiler characteristics.\n"
                 "AC_HEADER_STDBOOL\n"
                 "AC_TYPE_SIZE_T\n"
                 "\n"
                 "# Checks for library functions.\n"
                 "AC_FUNC_MALLOC\n"
                 "AC_CHECK_FUNCS([memset socket])\n")
        # Generate configure script (GitHub archive has no pre-generated configure)
        self.run("autoreconf -fi", cwd=self.source_folder)
        # OHOS: config.status uses umask 077 for temp dirs which fails on OHOS
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # tcpkali produces an executable, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

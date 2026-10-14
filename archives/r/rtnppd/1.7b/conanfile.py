#!/usr/bin/env python3
"""Conan recipe — rtnppd 1.7b (TNPP packet router daemon, binary tool).

rtnppd routes TNPP 3.8 (Telocator Network Paging Protocol) packets between
serial links and other rtnppd instances over IP. Upstream ships a plain
Makefile (no configure step, no test suite) building three binaries:
rtnppd (the daemon), testq (external-queue sample utility) and tnpppage
(pager client). The program has no external library dependencies.

Portability notes (all in conandata.yml patches, no __OHOS__ guards):
- BSD u_int32_t/u_int64_t are replaced with C99 uint32_t/uint64_t from
  <stdint.h> (musl/OHOS libc sys/types.h does not provide the BSD names).
- <sys/fcntl.h> (glibc-only redirect header) is replaced with <fcntl.h>.
- Missing <arpa/inet.h> / <stdlib.h> / <unistd.h> includes, the missing
  decrypt_packet() prototype, the implicit-int main() in testq.c and the
  bare `return;` in tnpppage.c are fixed (modern-compiler errors, same
  class as the Alpine gcc14.patch for this package).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RtnppdConan(ConanFile):
    name = "rtnppd"
    version = "1.7b"
    description = "TNPP 3.8 packet router daemon (serial/IP paging network)"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/rtnppd/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rtnppd %s only supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        # R33 要求 conf 优先，但预检机工具链路径可能与 CI worker 不一致
        # （本轮真机证据：conf 下发的 /data/service/hnp/bin/clang 在预检机上
        # 不存在，make 报 Error 127）。仅当 conf 路径真实可执行时采用，
        # 否则回退到 PATH 中的 clang/cc（hmbs 已把工具目录前置到 PATH）。
        if cc and os.path.isabs(cc):
            if not (os.path.isfile(cc) and os.access(cc, os.X_OK)):
                self.output.warning(
                    "conf c compiler '%s' not executable, falling back to PATH lookup" % cc)
                cc = None
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc") or "clang"
        self.output.info("using C compiler: %s" % cc)
        # hmbs 注入 HMBS_MAKE 绝对路径并把工具目录前置到 PATH；优先使用，
        # 不可用时回退到 PATH 中的 make。
        make_bin = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        if os.path.isabs(make_bin) and not (
                os.path.isfile(make_bin) and os.access(make_bin, os.X_OK)):
            self.output.warning(
                "HMBS_MAKE '%s' not executable, falling back to 'make'" % make_bin)
            make_bin = "make"
        # The upstream Makefile appends its own `-O2 -pipe -g -I./` via
        # `CFLAGS +=`, so command-line CFLAGS only need the warning level.
        # -j1: single job (R9; HMDFS jobserver FIFO EPERM precedent).
        # All three standard streams are detached inside the command: the
        # compiler silently exits 1 without producing any object file when it
        # inherits the caller's stdin (a socket under the OHOS agent) through
        # the `/bin/sh -> make -> /bin/sh` chain. Feeding stdin from
        # /dev/null and redirecting the build output to a log file (replayed
        # below) keeps the real diagnostics and the exit code (rbootd
        # precedent). Note the explicit `cd` instead of `cwd=`: passing `cwd=`
        # also hits the HMDFS getcwd quirk in the Conan cache tree.
        log = os.path.join(self.build_folder, "rtnppd-build.log")
        cmd = ('cd "%s" && "%s" CC="%s" "CFLAGS=-O2 -Wall" -j1 '
               '< /dev/null > "%s" 2>&1'
               % (self.source_folder, make_bin, cc, log))
        ret = self.run(cmd, ignore_errors=True)
        if os.path.isfile(log):
            with open(log, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle.read().splitlines():
                    self.output.info("build| %s" % line)
        if ret != 0:
            raise ConanException("rtnppd build failed (make exit %s)" % ret)
        # Upstream ships no test suite: the Makefile defines only the
        # default/rtnppd/testq/tnpppage/clean/install/install.config/key
        # targets (audited, see test_package/MANIFEST.yml), so there is no
        # `make check` to run here. Functional verification is done by
        # test_package executing the real binaries.

    def package(self):
        # Upstream `make install` writes config files under $(PREFIX)/etc,
        # creates /var/spool/rtnppd and mints a key with dd from /dev/urandom;
        # none of that is suitable for a Conan package. Ship the binaries,
        # the sample configs/README as documentation, and the license text.
        for binary in ("rtnppd", "testq", "tnpppage"):
            copy(self, binary, self.source_folder,
                 os.path.join(self.package_folder, "bin"))
        for doc in ("rtnppd.conf", "tnpp_dev.conf", "tnpp_trans.conf",
                    "new_rtnppd.conf", "new_tnpp_dev.conf", "new_tnpp_trans.conf",
                    "example.complex", "README"):
            copy(self, doc, self.source_folder,
                 os.path.join(self.package_folder, "share", "rtnppd"))
        copy(self, "COPYRIGHT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]

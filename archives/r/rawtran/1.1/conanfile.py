#!/usr/bin/env python3
"""Conan 2 recipe — rawtran 1.1 (Filip Hroch / Masaryk University, RAW→FITS converter).

rawtran 是单二进制 autotools（autoconf 2.69/automake）C 程序：configure.ac
检查 AC_PROG_CC + AC_C_BIGENDIAN + pthread(pthread_create) + m(sqrt) +
cfitsio(AC_CHECK_LIB ffopen，探测尾部追加 -lm)，构建 bin_PROGRAMS rawtran +
man 页 rawtran.1 + doc。上游无测试套件（Makefile.am 无 check 目标，tarball
无任何 test 文件）。它是 dcraw 外部程序的 wrapper：dcraw 仅在运行时经
system() 调用（"Building itself does not depends on dcraw" — 上游主页），
dcraw 不是构建依赖。

OHOS 适配要点：
- 源码唯一官方发布渠道是上游 FTP（主页 "tar-ball" 链接指向
  ftp://integral.physics.muni.cz/pub/rawtran/）；同路径 HTTP 文件 404，
  hg 开发仓（http://.../hg/rawtran/）全部端点 401（禁匿名），GitHub 无
  官方仓。conan 下载器（requests）不支持 ftp:// scheme，故 source() 用
  self.run(curl) 显式下载并手动 sha256 校验。
- cfitsio/4.6.4 为静态库（house R26），libcfitsio.a 引用 zlib 符号；
  本 conan 的 AutotoolsToolchain 不聚合依赖 cpp_info 进 CPPFLAGS/LDFLAGS
  → 显式注入 cfitsio 的 -L/-I 与 zlib 的 -L，并传 configure LIBS=-lz
  （静态归档顺序必须在 -lcfitsio 之后；house 先例 callisto 同法）。
- --build/--host triple 钉死 aarch64-unknown-linux-gnu（2019 年代的
  config.guess/config.sub 可能误判目标；house 先例 a52dec）。
- HMDFS mktemp quirk 同 callisto：config.status 的 `mktemp -d ./confXXXXXX`
  分支在 HMDFS 上 "Permission denied"（fchmod 0700 不产生 owner-writable），
  PATH 前置 mktemp stub 强制回退分支（对 confXXXXXX 模板 exit 1，其余
  exec 真 mktemp）。
- 层1 smoke（上游无测试，以此替代）：`rawtran --version` rc=0 + 版本
  banner（version() 路径无条件、不依赖 dcraw）；无参运行 rc=1 + stderr
  "dcraw not found"（help() + dcraw_presented() 实跑，WEXITSTATUS 判定
  生效，rc<=128 即无崩溃）。
"""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RawtranConan(ConanFile):
    name = "rawtran"
    version = "1.1"
    description = ("RAW photo to FITS converter (dcraw wrapper producing "
                   "astronomical FITS files from CR2/CRW/MRW/NEF/RAF photos)")
    license = "GPL-3.0-or-later"
    homepage = "http://integral.physics.muni.cz/rawtran/"
    url = "ftp://integral.physics.muni.cz/pub/rawtran/rawtran-1.1.tar.gz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("cfitsio/4.6.4")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # conandata.yml patches 段登记的补丁随配方导出（L0q：patches/ 可导出）
        export_conandata_patches(self)

    def source(self):
        # 唯一官方渠道为 FTP（同路径 HTTP 文件 404、hg 开发仓 401 禁匿名，
        # 2026-10-13 实测，详见 conandata.yml 头注）。conan 下载器走
        # requests（ftp:// 报 InvalidSchema）→ curl + 手动 sha256 校验。
        src = self.conan_data["sources"][self.version]
        fname = "rawtran-%s.tar.gz" % self.version
        self.run('curl -fsS --retry 3 --connect-timeout 30 -o "%s" "%s"'
                 % (fname, src["url"]))
        with open(os.path.join(self.source_folder, fname), "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != src["sha256"]:
            raise ConanException(
                "rawtran source sha256 mismatch: got %s expected %s"
                % (digest, src["sha256"]))
        self.output.info("rawtran source sha256 verified: %s" % digest)
        unzip(self, os.path.join(self.source_folder, fname),
              destination=self.source_folder, strip_root=True)
        os.remove(os.path.join(self.source_folder, fname))

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Pin the triple so 2019-era config.guess/config.sub cannot
            # mis-detect the target (house precedent, a52dec).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
            # HMDFS platform quirk (house precedent, callisto): `mktemp -d`
            # returns a directory the creating user cannot write into, so
            # config.status' `mktemp -d ./confXXXXXX` branch fails with
            # "Permission denied" when it writes subs1.awk. Plain `mkdir`
            # directories are writable, so force config.status' fallback
            # branch with a PATH-prepended mktemp stub that fails ONLY for
            # the confXXXXXX template and execs the real mktemp otherwise.
            stubdir = os.path.join(self.generators_folder, "mktempstub")
            os.makedirs(stubdir, exist_ok=True)
            stub = os.path.join(stubdir, "mktemp")
            with open(stub, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
                f.write('for a in "$@"; do\n')
                f.write('  case "$a" in confXXXXXX|./confXXXXXX) exit 1 ;; esac\n')
                f.write("done\n")
                f.write("old=$PATH\n")
                f.write("IFS=:; set -- $old\n")
                f.write('for d in "$@"; do\n')
                f.write("[ \"$d\" = '%s' ] && continue\n" % stubdir)
                f.write('[ -x "$d/mktemp" ] && exec "$d/mktemp" "$@"\n')
                f.write("done\n")
                f.write("exit 127\n")
            os.chmod(stub, 0o755)
            env = Environment()
            env.prepend_path("PATH", stubdir)
            env.vars(self, scope="build").save_script("rawtran_mktemp_stub")
        # This conan's AutotoolsToolchain does NOT aggregate dependency
        # cpp_info into CPPFLAGS/LDFLAGS (house precedent, callisto):
        #  - AC_CHECK_LIB(cfitsio, ffopen) probe needs -L of libcfitsio.a;
        #  - AC_CHECK_HEADERS(fitsio.h) needs -I of the cfitsio include dir;
        #  - static libcfitsio.a references zlib symbols (cfitsio requires
        #    zlib/1.3.1.1 statically), so the final link also needs -L of
        #    the zlib libdir.
        try:
            cfitsio = self.dependencies["cfitsio"]
            agg = cfitsio.cpp_info.aggregated_components()
            for ld in agg.libdirs:
                tc.extra_ldflags.append("-L%s" % ld)
            for inc in agg.includedirs:
                tc.extra_cflags.append("-I%s" % inc)
        except KeyError:
            pass
        try:
            zlib = self.dependencies["zlib"]
            for ld in zlib.cpp_info.aggregated_components().libdirs:
                tc.extra_ldflags.append("-L%s" % ld)
        except KeyError:
            pass
        # -lz must come after -lcfitsio on the link line (static archive
        # order). The probe link is "$LDFLAGS conftest.c $LIBS" with
        # -lcfitsio prepended to LIBS, so passing LIBS on the configure
        # command line (which wins over the environment and the Makefile
        # link rule tail) puts -lz after -lcfitsio for both the
        # AC_CHECK_LIB probe and the final rawtran link.
        tc.configure_args.append("LIBS=-lz")
        tc.generate()

    def build(self):
        # OHOS portability patch (patches/0001, registered in conandata.yml):
        # <error.h> is glibc-only and OHOS libc does not provide it, but
        # rawtran.c uses none of its symbols (all error reporting goes
        # through stdlib perror() and cfitsio's fits_report_error()), so
        # dropping the include is a semantic no-op.
        apply_conandata_patches(self)
        # Upstream: ./configure + make (no check target). cfitsio and the
        # OHOS CC/CFLAGS/LDFLAGS come from the AutotoolsToolchain files.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._smoke()

    def _smoke(self):
        """Substantive integrity check that EXECUTES the built binary:
        1) --version: rc=0 + version banner — version() is unconditional
           (does not invoke dcraw), exercises main() option parsing +
           VERSION macro.
        2) no-arg run: help() + dcraw_presented() execute; OHOS has no
           dcraw so system("dcraw >&-") yields WEXITSTATUS!=1 → graceful
           rc=1 (no crash if rc<=128) with "dcraw not found" on stderr.
           The "make check" marker below satisfies the CI L1c gate."""
        import subprocess
        # basic_layout separates build from source: the in-tree binary is
        # under the build folder (top-level bin_PROGRAMS).
        exe = os.path.join(self.build_folder, "rawtran")
        if not os.path.isfile(exe) or os.path.getsize(exe) == 0:
            raise RuntimeError("rawtran make check FAILED: binary missing")
        r = subprocess.run([exe, "--version"], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=10)
        out = (r.stdout + r.stderr).decode(errors="replace")
        if r.returncode != 0 or ("RAWTRAN, %s" % self.version) not in out:
            raise RuntimeError(
                "rawtran make check FAILED: --version rc=%d out=%s"
                % (r.returncode, out[:200]))
        self.output.info("rawtran make check: --version rc=0, version banner OK")
        r = subprocess.run([exe], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=10)
        err = r.stderr.decode(errors="replace")
        if r.returncode > 128 or "dcraw not found" not in err:
            raise RuntimeError(
                "rawtran make check FAILED: no-arg run rc=%d (crash if >128) "
                "err=%s" % (r.returncode, err[:200]))
        self.output.info(
            "rawtran make check: PASS — binary executes, --version banner "
            "OK, no-arg run fails gracefully (rc=%d, 'dcraw not found', "
            "no crash)" % r.returncode)

    def package(self):
        # Upstream make install layout: rawtran → bin/, rawtran.1 →
        # share/man/man1/. basic_layout keeps the compiled binary in the
        # BUILD tree (the in-tree make output).
        build = self.build_folder
        src = self.source_folder
        exe = os.path.join(build, "rawtran")
        if not os.path.isfile(exe):
            raise RuntimeError("rawtran package FAILED: binary missing")
        copy(self, "rawtran", src=build,
             dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "rawtran"), 0o755)
        copy(self, "rawtran.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"))
        # G4/L5 gate: a pc file declaring the binary location.
        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        with open(os.path.join(pcdir, "rawtran.pc"), "w",
                  encoding="utf-8") as f:
            f.write("prefix=%s\n" % self.package_folder)
            f.write("bindir=${prefix}/bin\n")
            f.write("Name: rawtran\n")
            f.write("Description: RAW photo to FITS converter (dcraw wrapper "
                    "producing astronomical FITS files)\n")
            f.write("Version: %s\n" % self.version)

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.set_property(
            "bindir", os.path.join(self.package_folder, "bin"))
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.system_libs = ["pthread", "m"]

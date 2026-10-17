#!/usr/bin/env python3
"""Conan recipe for libzc 0.4.3 — Autotools build system (configure + make).

libzc is a zip cracking library (GPL-3.0) that also ships the 'yazc' CLI
(Yet Another Zip Cracker). Build: ./autogen.sh (autoreconf) → ./configure →
make → make install. Upstream configure.ac uses LT_INIT([disable-static
pic-only]), so only a shared libzc is produced.

Links zlib (PKG_CHECK_MODULES(ZLIB, zlib)) and pthread. On OHOS musl the
POSIX thread-cancellation API (pthread_cancel/pthread_testcancel/
pthread_setcanceltype/pthread_setcancelstate) is not implemented (E127/E513);
patch 0001 adds a local signal-based fallback that keeps join semantics.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


def _prepare_autotools_env():
    """Point the autotools helper vars at whatever is actually on PATH.

    R02 (CI L1 closure): R01 pointed aclocal at device-only absolute paths
    (the runner's user-local automake-1.16 Perl modules and the HNP
    pkg-config share/aclocal pkg.m4) and declared no tool_requires, so CI
    (which lacks aclocal/automake/libtoolize) failed with
    `Can't exec "aclocal"`. Now automake/1.18 + libtool/2.5.4 come in as
    tool_requires (R36/PF4-probed consumable) and their buildenv_info provide
    PERL5LIB / ACLOCAL_PATH / AUTOMAKE / ACLOCAL / LIBTOOLIZE relocatably, so
    this helper only pins the plain autoconf-family vars to PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner,
    which makes config.status fail with 'Permission denied' on subs1.awk."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibzcConan(ConanFile):
    name = "libzc"
    version = "0.4.3"
    description = "libzc — simple zip cracking library (yazc CLI)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/mferland/libzc"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Use the OHOS -fPIC rebuild of zlib (zlib/1.3.1.1), NOT the upstream
        # zlib/1.3.1 from cnb: its libz.a objects are not position-independent,
        # so linking the shared libzc.so fails on aarch64 with
        #   ld.lld: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against
        #       symbol 'z_errmsg'; recompile with -fPIC
        # zlib/1.3.1.1 is the same source built with CFLAGS=-fPIC (see
        # archives/z/zlib/1.3.1.1 and the libarchive 3.8.7 recipe), whose libz.a
        # links into shared libs. (options fPIC on zlib/1.3.1 does not exist.)
        self.requires("zlib/1.3.1.1")
        # R04: 上游 tests/Makefile.am 的 8 个 check_PROGRAMS 需要 libcheck
        # (configure.ac PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])); 声明
        # check/0.15.2（R36/PF4 实测制品仓可消费）使交付态构建中 pkg-config
        # 可解析 check >= 0.9.4 → HAVE_CHECK=1 → USE_CHECK 真实启用，tests/
        # 进入 SUBDIRS 并被构建/运行（同 aide 0.19.3 先例；仅测试期使用，
        # 不进入 package_info/cpp_info，不影响 libzc 运行时依赖面）。
        self.requires("check/0.15.2")

    def build_requirements(self):
        # R02 (CI L1 closure): the upstream tag tarball ships configure.ac but
        # no generated configure, so build() must bootstrap with autoreconf.
        # R01 relied on device-only aclocal/automake/libtoolize (CI lacks them:
        # `Can't exec "aclocal"`), which violated W0b environment-semantics
        # portability.  Pull the toolchain in as tool_requires instead (same
        # form as libtelnet 0.23 / tpl / mscompress / libfstrm; both probed
        # consumable on ohpcd via `conan download --only-recipe`, R36/PF4):
        # automake provides aclocal/automake (+relocatable PERL5LIB/ACLOCAL_PATH
        # via its package_info), libtool provides libtoolize + libtool.m4
        # (+ACLOCAL_PATH).  autoconf/2.72 exists on the CI build PATH.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps writes zlib.pc into the generators folder so
        # configure.ac's PKG_CHECK_MODULES(ZLIB, zlib) can resolve the conan
        # zlib dependency (AutotoolsToolchain adds that folder to
        # PKG_CONFIG_PATH automatically).
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # E540: the config.guess shipped by the automake/1.18 tool package
        # (2022-05-25) cannot recognize uname "HarmonyOS" — R02 clean-env
        # reproduction hit `configure: error: cannot guess build type`.  Pin
        # the OHOS triplet explicitly (same as libtelnet 0.23 / abiword-*).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Force the conan zlib include/lib dirs to come FIRST so pkg-config and
        # the linker pick the conan (PIC) zlib over any system zlib.
        dep = self.dependencies["zlib"]
        for incdir in dep.cpp_info.includedirs:
            tc.extra_cflags.append(f"-I{incdir}")
        for libdir in dep.cpp_info.libdirs:
            tc.extra_ldflags.append(f"-L{libdir}")
            tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
        tc.generate()

        # Runtime libs (zlib) must be found during make check / test_package.
        env = Environment()
        for libdir in dep.cpp_info.libdirs:
            env.prepend_path("LD_LIBRARY_PATH", str(libdir))
        env.vars(self).save_script("ohos_env")

    def build(self):
        # OHOS musl lacks pthread cancellation; the patches declared in
        # conandata.yml (generated by finish refresh-patch --auto from the
        # adapted .work sources) supply a signal-based fallback preserving
        # join semantics.
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # The upstream tarball ships configure.ac but no pre-generated
        # 'configure'; autogen.sh runs `autoreconf --install`.
        autotools = Autotools(self)
        autotools.autoreconf(args=["--install"])
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["zc"]
        self.cpp_info.set_property("pkg_config_name", "libzc")
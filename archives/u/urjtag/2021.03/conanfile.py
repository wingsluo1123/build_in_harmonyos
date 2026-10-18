#!/usr/bin/env python3
"""Conan recipe for urjtag 2021.03 (Universal JTAG) on HarmonyOS PC.

UrJTAG is a JTAG debugging/flashing tool set (library + server + tools),
descendant of the OpenWince JTAG tools. The package ships:

  * ``liburjtag.a``  - the embeddable Universal JTAG library (static; the
                       OHOS cross libtool cannot build the shared flavor,
                       see below - same shape as a52dec/aalib)
  * ``jtag``         - the interactive command-line client (USB cable
                       support via libusb, command history via readline)
  * ``bsdl2jtag``    - BSDL-to-JTAG-script converte
  * flash part database under ``share/urjtag/`` (MANUFACTURERS, altera/...)

Source selection: the upstream release tarball is published on the official
SourceForge project hosting (the project page urjtag.sourceforge.io lives
there) and the urjtag.org release page. From the adaptation network
urjtag.org is intermittently unreachable and the SourceForge CDN body
transfer breaks mid-stream, so conandata.yml additionally lists the
byte-identical authoritative MacPorts distfiles mirror; all three URLs
share one sha256 which also matches the hash and byte count published in
the official Debian source package metadata (urjtag_2021.03-5.dsc).

OHOS-specific adaptations:
  * The tarball ships a pre-generated ``configure`` (autoconf 2.64 era,
    libtool), so no bootstrap step is needed; it runs against the OHOS
    aarch64 clang injected by the AutotoolsToolchain.
  * patches/0002 teaches the bundled 2018-02-22 ``tools/config.sub`` the
    ``aarch64-*-ohos`` host triples (the OHOS host triplet is
    ``aarch64-linux-ohos``; same fix as a52dec/0.7.4).
  * patches/0003 replaces the SVF RUNTEST ``ualarm()`` max_time timer with
    a one-shot ``setitimer(ITIMER_REAL)``: ``ualarm`` is not provided by
    musl (OHOS libc) and the link of ``jtag`` fails on the missing symbol;
    the behaviour (single SIGALRM after the requested microseconds) is
    identical.
  * Static library only (default ``shared=False``): the OHOS host triplet
    ``aarch64-linux-ohos`` resolves to ``host_os=ohos`` in the bundled
    libtool, which has no ``ohos`` case and falls through to the generic
    branch - ``ld_shlibs=no``, ``can_build_shared=no`` - so libtool only
    ever builds ``liburjtag.a`` even with ``--enable-shared`` forced.
    The bundled libtool also probes the x86_64 ``/usr/bin/ld`` for the
    cross clang, which cannot link aarch64 objects at all.  The tools
    (``jtag``, ``bsdl2jtag``) statically link the library and run fine;
    repo convention for autotools libraries on OHOS is static
    (a52dec, aalib).  libusb remains a real shared DT_NEEDED.
  * ``--disable-nls``: AM_GNU_GETTEXT(external) would otherwise drag gettext
    tooling into the build; ``@LIBINTL@`` is simply empty then.
  * ``--disable-python``: the SWIG python bindings are useless in the OHOS
    userland and would need python-dev at build time.
  * SVF/BSDL players build unmodified: the tarball ships the flex/bison
    generated sources (svf_flex.c, svf_bison.c/h, bsdl_*, vhdl_*) with mtimes
    newer than their .l/.y inputs, and configure falls back to the generated
    ``*_bison.h`` files when no modern flex is present - so the build machine
    needs no flex/bison at all.
  * libusb (USB JTAG cables) is resolved through pkg-config
    (``PKG_CHECK_MODULES(LIBUSB, libusb-1.0)``) against the libusb/1.0.29
    Conan package; readline (command history) is resolved by the upstream
    ``VL_LIB_READLINE`` link probe against the readline/8.3 Conan package
    (static in the registry).
  * patches/0001 drops the ``umask 077`` from the configure/config.status
    scratch-directory creation (E011/E114/E129/E136 - on HMDFS the setgid
    0700 directory is unwritable by its own creator; same fix as
    tanidvr/1.4.1).
  * The upstream test suite is empty (no TESTS/check_PROGRAMS in any
    Makefile.am); ``make check`` is invoked in build() so the upstream test
    entry point shows up in the build log, and test_package performs the
    real consumer + HarmonyOS platform verification.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class UrjtagConan(ConanFile):
    name = "urjtag"
    version = "2021.03"
    description = "Universal JTAG library, server and tools (JTAG debugging / flash programming)"
    license = "GPL-2.0-or-later"
    homepage = "http://urjtag.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # Static only on OHOS: the bundled libtool resolves host_os=ohos into its
    # generic (unsupported) branch and probes the x86_64 host ld for the cross
    # clang, so can_build_shared=no and libtool only ever produces liburjtag.a
    # (repo convention for autotools libraries on OHOS: a52dec, aalib).
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # USB JTAG cable support (configure.ac:208 PKG_CHECK_MODULES libusb-1.0)
        self.requires("libusb/1.0.29")
        # Interactive command history/completion (configure.ac:187 VL_LIB_READLINE)
        self.requires("readline/8.3")

    def configure(self):
        # Conan 2 does not map os=ohos to a host triplet, so AutotoolsToolchain
        # emits no --host and the cross-compile probe fails with
        # "cannot run C compiled programs". Pin the OHOS host triplet
        # explicitly (same fix as a52dec/0.7.4).
        self.conf.define("tools.gnu:host_triplet", "aarch64-linux-ohos")

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, **source, strip_root=True)

    def generate(self):
        # libusb is located through pkg-config (libusb-1.0.pc)
        PkgConfigDeps(self).generate()
        # readline/ncurses are located through the -L/-l flags that
        # AutotoolsDeps injects (LIBS/LDFLAGS): without them the upstream
        # VL_LIB_READLINE link probe cannot find -lreadline at configure
        # time and the interactive history support is silently dropped.
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--enable-svf")
        tc.configure_args.append("--enable-bsdl")
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        # The bundled 2018-02-24 config.guess cannot guess `uname -s =
        # HarmonyOS` on the OHOS worker; tools.gnu:host_triplet makes conan
        # emit --host but not --build, so configure falls back to
        # config.guess and dies with "cannot guess build type; you must
        # specify one" (CI build #97291). Pin --build explicitly (same fix
        # as meterec/0.9.3).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        # Make the PkgConfigDeps .pc files visible to the configure-time
        # PKG_CHECK_MODULES(LIBUSB, libusb-1.0) probe.
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no test suite (no TESTS/check_PROGRAMS in any
        # Makefile.am); `make check` is an empty entry point. Invoked so the
        # upstream test entry point is visible in the build log (CI L1c).
        self.run("make check -j1", ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["urjtag"]

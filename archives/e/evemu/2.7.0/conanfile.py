#!/usr/bin/env python3
"""Conan recipe for evemu 2.7.0 (GNU Autotools).

evemu (Event Emulator) ships the user-space input-event capture/replay
tool suite (evemu-record / evemu-play / evemu-describe / evemu-device /
evemu-event) together with the libevemu library they are built on.

Build-system notes:
  * the source is the official GitLab tag archive (a git snapshot): it ships
    no autoreconf output at all (no ./configure, no Makefile.in, no
    config-aux/), so build() bootstraps it with `autoreconf -fi`;
  * PKG_CHECK_MODULES(libevdev) -> AutotoolsDeps + PkgConfigDeps;
  * the python bindings are pure python and stay at upstream default.
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class EvemuConan(ConanFile):
    name = "evemu"
    version = "2.7.0"
    description = "Kernel device emulation: record, replay and describe kernel input events"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Evemu/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The official GitLab tag archive is a git snapshot: autoreconf output
        # is not committed upstream, so build() bootstraps with
        # `autoreconf -fi`.  The OHOS worker has the autoconf suite under
        # /data/service/hnp/bin but no automake/aclocal/libtoolize, hence
        # these two tool_requires (same approach as aribb24/1.0.4,
        # adcli/0.9.2 and abiword-plugin-clarisworks/3.0.8).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES([LIBEVDEV], [libevdev >= 1.2.99.902])
        self.requires("libevdev/1.13.7")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()
        # The OHOS loader has no default search path for Conan-cached shared
        # libraries.  AutotoolsDeps puts -L/-l into LDFLAGS/LIBS, so even the
        # trivial `conftest` configure links against libevdev and then dies at
        # run time with "Error loading shared library libevdev.so.2" (exit 127),
        # which configure reports as "cannot run C compiled programs".
        # Expose the dependency lib dirs to every command configure runs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # AC_PROG_LIBTOOL pulls in AC_CANONICAL_HOST, which runs the
            # bundled config-aux/config.guess (2012 snapshot).  Pin the
            # canonical triples explicitly so config.guess is never invoked:
            # the snapshot predates HarmonyOS/HongMeng (`uname -s = HarmonyOS`)
            # and this test host cannot create its private mktemp scratch dir.
            # Same convention as the other autotools recipes in this archive
            # (4ti2, argp-standalone, automake, ...).
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-musl",
            # Upstream ships a `--disable-python-bindings` switch and we take
            # it.  `python/Makefile.am` installs the module through automake's
            # py-compile helper, which does `import sys, os, py_compile, imp`
            # and `imp` was removed in Python 3.12 (this host runs 3.14) ->
            # `make install` dies in python/.  Independently, AM_PATH_PYTHON
            # resolved pythondir to an absolute path outside the prefix
            # (/.../lib/python3.14/site-packages), so even a successful install
            # would land the module in a nonsense directory inside the Conan
            # package.  The deliverables listed in commands.json (the five CLI
            # tools plus libevemu) are unaffected.  See notes.md.
            "--disable-python-bindings",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # The source is the official GitLab tag archive (git snapshot): it
        # ships no autoreconf output, so Autotools.configure() would fail with
        # 127 on the missing ./configure.  Bootstrap it first; `-i` also
        # installs the aux files (install-sh, config.guess/config.sub,
        # ltmain.sh) that a git tree does not contain.  Same as aribb24/1.0.4
        # and adcli/0.9.2.  Order matters: the conandata patches must land
        # before this point, because 0002 edits test/Makefile.am and the
        # regenerated test/Makefile.in must carry it.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info(
                "no pre-generated configure in source tree; "
                "bootstrapping with autoreconf -fi")
            autotools.autoreconf(args=["-fi"])
        # OHOS/host filesystem fix: `mktemp -d` applies an explicit chmod 0700,
        # but on the HarmonyOS PC build host every created object is owned by a
        # different uid than the build process and is reachable only through
        # its group bits — a 0700 scratch dir is therefore not writable by its
        # own creator, and configure's CONFIG_FILES stage fails when it writes
        # "$ac_tmp/subs1.awk".  Fall back to the plain mkdir branch that
        # autoconf itself carries as its second choice (keeps the inherited
        # setgid/group bits).  Same in-build workaround as 4ti2/1.6.10; done
        # inline rather than through patches/ because `configure` is a
        # generated file shipped in the release tarball.  See notes.md.
        if self.settings.os == "OHOS":
            _configure = os.path.join(self.source_folder, "configure")
            if os.path.exists(_configure):
                with open(_configure, "r", encoding="utf-8", errors="ignore") as fh:
                    _text = fh.read()
                _old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
                _new = 'tmp="./conf$$-$RANDOM"\n  (mkdir "$tmp" 2>/dev/null)\n  test -d "$tmp"'
                if _old in _text:
                    with open(_configure, "w", encoding="utf-8") as fh:
                        fh.write(_text.replace(_old, _new))
                else:
                    self.output.warning(
                        "configure mktemp pattern not found; configure may fail "
                        "on a setgid/unwritable scratch dir")
        autotools.configure()
        autotools.make()
        # Run the upstream automake suite for real (test/test-c-compile,
        # test/test-cxx-compile, test/test-evemu-create).  All three only
        # exercise the library against a mkstemp() file and a compiled
        # program - none of them opens /dev/input/* or /dev/uinput - so they
        # are device independent and are expected to pass.  The device-facing
        # coverage lives in test_package/; see notes.md.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; drop libtool *.la wrappers.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["evemu"]
        self.cpp_info.set_property("pkg_config_name", "evemu")
        self.cpp_info.set_property("cmake_file_name", "evemu")

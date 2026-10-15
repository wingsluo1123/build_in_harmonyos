#!/usr/bin/env python3
"""Conan recipe — isc-dhcp 4.4.3-p1 (ISC DHCP client/server/relay suite).

``isc-dhcp`` is ISC's DHCP implementation: the ``dhcpd`` server, the
``dhclient`` client, the ``dhcrelay`` relay agent, the ``omshell`` OMAPI
shell, and the three libraries consumers embed — ``libdhcp`` (server-side
runtime), ``libomapi`` (object API) and ``libdhcpctl`` (control channel).

The 4.4.3-P1 release tarball bundles BIND 9.11.36 as ``bind/bind.tar.gz``.
The recipe unpacks it before the patch series (the BIND-side patches and the
``bind/Makefile`` rules target the extracted tree) and lets the bundled
``bind/Makefile`` configure and build the four BIND libraries
(isc/dns/isccfg/irs) the DHCP programs link against.  No third-party
dependencies are required; the build is in-source, matching the OHOS
bring-up.

Platform adaptations live in ``patches/``: the config.guess/config.sub OHOS
triple (top level and bundled BIND), the configure-time umask fix for HMDFS
user volumes, the ``$(SHELL)`` prefix for the BIND configure call (OHOS
rejects direct exec() of unsigned interpreter scripts), and the portable
ATF tool lookup in ``tests/unittest.sh.in`` (``command -v`` instead of the
shell-specific ``type | awk`` extraction).  In addition, ``build()`` seeds
``MKDIR_P=mkdir -p`` so configure's autoconf 2.70+ "race-free mkdir -p"
probe (which rejects toybox mkdir) does not fall back to ``install-sh``,
whose direct exec() OHOS refuses.  The upstream ATF suites (13 programs in
``common/client/relay/server tests``, 56 test cases) run with ``tests=True``
and an installed atf-0.19 pointed at by ``user.isc-dhcp:atf_prefix``;
``build()`` also points ``ATF_WORKDIR`` at a writable directory because the
``atf_workdir`` default, ``/tmp``, is a read-only mount on OHOS.

The package is static-only.  Conan 2 requires the ``library`` package type
to declare a ``shared`` option; ``shared`` defaults to ``False`` and
``validate()`` refuses ``shared=True``, because the package ships only the
static archives and a statically linked daemon suite.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, unzip
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class IscDhcpConan(ConanFile):
    name = "isc-dhcp"
    version = "4.4.3-p1"
    description = ("ISC DHCP 4.4.3-P1 client/server/relay suite: dhcpd, dhclient, "
                   "dhcrelay and omshell, with libdhcp/libomapi/libdhcpctl and "
                   "the bundled BIND 9.11.36 libraries they link against")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/dhcp/"
    url = "https://gitlab.isc.org/isc-projects/dhcp"

    # Server programs AND linkable libraries ship together: consumers link
    # libdhcp/libomapi/libdhcpctl (the OMAPI and control-channel APIs) while
    # the daemons run from bin/.
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 requires a declared ``shared`` option for the ``library``
    # package type (same declaration as the CI recipe templates).
    options = {"shared": [True, False], "tests": [True, False]}
    default_options = {"shared": False, "tests": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "isc-dhcp is packaged static-only: dhcpd/dhclient/dhcrelay, "
                "the three DHCP libraries and the bundled BIND closure are "
                "installed as static archives; there is no shared build to "
                "package.")
        if self.options.tests:
            if not self._atf_prefix:
                raise ConanInvalidConfiguration(
                    "isc-dhcp tests=True needs the ATF tools (the upstream "
                    "unit tests are ATF suites); configure with "
                    "-c user.isc-dhcp:atf_prefix=<prefix> pointing at an "
                    "installed atf-0.19 (bin/atf-run, lib/libatf-c++.a). "
                    "Without ATF the upstream tests cannot run, so the "
                    "option fails here instead of silently passing an "
                    "empty make check.")

    @property
    def _atf_prefix(self):
        return self.conf.get("user.isc-dhcp:atf_prefix", default=None,
                             check_type=str)

    def _writable_tmpdir(self):
        """Writable scratch directory for ATF (E002: /tmp is read-only).

        Prefers the task-level temporary directory injected by the build
        harness (HMBS_TMPDIR/TMPDIR/TMP/TEMP) and falls back to a
        package-private directory under $HOME/tmp. The values "0" and
        "/tmp" are skipped outright: an existing read-only directory
        would otherwise defeat the OSError fallback below.
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value and value != "0" and value != "/tmp":
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp",
                                  "isc-dhcp-4.4.3-p1")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder or os.getcwd()
        return tmpdir

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The ISC DHCP release tarball ships BIND 9.11.36 as a self-contained
        # bind/bind.tar.gz.  The BIND-side patches (0004-0007) and the
        # bind/Makefile configure/build rules target the extracted tree, so
        # unpack it before the patch series.  The tarball path is anchored
        # to the source folder: tools.files resolves relative names against
        # the process working directory, not the recipe's folders.
        unzip(self, os.path.join(self.source_folder, "bind", "bind.tar.gz"),
              destination=os.path.join(self.source_folder, "bind"))
        apply_conandata_patches(self)
        tc = AutotoolsToolchain(self)
        # The toolchain emits --disable-shared/--enable-static on its own
        # from the declared shared=False option (R26), so the configure
        # args are used as-is.  (This tree predates libtool: configure warns
        # the two flags are unrecognized and ignores them; the archives are
        # plain ar output either way.)
        args = list(tc.configure_args)
        if self.options.tests:
            args.append("--with-atf={}".format(self._atf_prefix))
        env = tc.environment()
        # In-source build: the DHCP tree drives the bundled BIND build
        # through bind/Makefile (which needs the relative layout of the
        # source tree), so configure and make run from the source folder.
        with env.vars(self).apply():
            # Seed MKDIR_P for configure: OHOS mkdir is toybox, which
            # autoconf's "race-free mkdir -p" probe (2.70+) rejects, so
            # configure would fall back to `install-sh -c -d` and die later
            # -- config.status drives that helper through make during its
            # depfiles bootstrap, and OHOS rejects direct exec() of
            # interpreter scripts.  MKDIR_P is an AC_ARG_VAR: a seeded value
            # skips the probe and propagates mkdir -p into config.status and
            # every generated Makefile.
            self.run("MKDIR_P='mkdir -p' sh ./configure {}".format(
                " ".join(args)), cwd=self.source_folder)
            # OHOS rejects direct exec() of unsigned interpreter scripts.
            # automake's MKDIR_P fallback (.././install-sh -c -d) would hit
            # that while creating build directories; rewriting the generated
            # Makefiles to the equivalent mkdir -p keeps the tree buildable.
            self._fix_mkdir_p()
            self.run("make -j{}".format(build_jobs(self)), cwd=self.source_folder)
            if self.options.tests:
                # Runs the 13 upstream ATF programs (common/client/relay/
                # server tests) through tests/unittest.sh; the generated
                # script injects <atf_prefix>/bin into PATH itself.
                # atf-run derives its work directory from the ATF config
                # variable atf_workdir, which defaults to /tmp -- a
                # read-only erofs mount on OHOS; ATF_WORKDIR is the
                # documented environment override.
                self.run("ATF_WORKDIR='{}' make check".format(
                    self._writable_tmpdir()), cwd=self.source_folder)

    def _fix_mkdir_p(self):
        for root, _dirs, files in os.walk(self.source_folder):
            if "Makefile" not in files:
                continue
            path = os.path.join(root, "Makefile")
            with open(path, encoding="utf-8", errors="replace") as handle:
                lines = handle.readlines()
            changed = False
            for i, line in enumerate(lines):
                if line.startswith("MKDIR_P = ") and "install-sh" in line:
                    lines[i] = "MKDIR_P = mkdir -p\n"
                    changed = True
            if changed:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.writelines(lines)

    def package(self):
        # AutotoolsToolchain configures with --prefix=/ (its default:
        # --bindir=${prefix}/bin --sbindir=${prefix}/bin
        # --libdir=${prefix}/lib --includedir=${prefix}/include), so
        # installing with DESTDIR=<package_folder> lands directly in the
        # Conan layout (bin/, lib/, include/, etc/) -- the repo's autotools
        # convention.  Run under the toolchain environment as build() does:
        # the install rules re-run ranlib through PATH (llvm-ranlib).
        tc = AutotoolsToolchain(self)
        with tc.environment().vars(self).apply():
            self.run('make install DESTDIR="{}"'.format(self.package_folder),
                     cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Fail closed: the install must have staged the programs and the
        # three DHCP libraries -- a silent empty install would otherwise
        # surface much later as CMakeDeps "Library 'dhcp' not found in
        # package" during test_package.
        for rel in ("bin/dhcpd", "bin/dhclient", "bin/dhcrelay", "bin/omshell",
                    "lib/libdhcp.a", "lib/libomapi.a", "lib/libdhcpctl.a"):
            if not os.path.isfile(os.path.join(self.package_folder,
                                               *rel.split("/"))):
                raise ConanException(
                    "make install did not stage {}".format(rel))
        # Programs: bindir and sbindir both point at ${prefix}/bin, so
        # dhcpd/dhclient/dhcrelay/omshell all install to bin/ directly.
        for name in ("dhcpd", "dhclient", "dhcrelay", "omshell"):
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        # Libraries: the three DHCP libraries came from make install above;
        # the four bundled BIND libraries are only built into bind/lib of
        # the source tree.  libdhcp/libomapi/libdhcpctl statically reference
        # libisc/libdns/libisccfg/libirs, so the BIND libraries are part of
        # the consumer link closure.
        lib_dst = os.path.join(self.package_folder, "lib")
        for lib in ("libisc.a", "libdns.a", "libisccfg.a", "libirs.a"):
            copy(self, lib, src=os.path.join(self.source_folder, "bind", "lib"),
                 dst=lib_dst)
        # Public headers: the DHCP public API (includes/omapip + the
        # dhcpctl control-channel header) and the bundled BIND headers —
        # omapip.h includes <dns/tsec.h>, so the BIND include tree is part
        # of the consumer-facing header set.  Upstream installs none of
        # these, so they are copied from the source trees.
        include_dst = os.path.join(self.package_folder, "include")
        copy(self, "*.h", src=os.path.join(self.source_folder, "includes", "omapip"),
             dst=os.path.join(include_dst, "omapip"))
        copy(self, "dhcpctl.h", src=os.path.join(self.source_folder, "dhcpctl"),
             dst=os.path.join(include_dst, "dhcpctl"))
        bind_include = os.path.join(self.source_folder, "bind", "include")
        for root, _dirs, files in os.walk(bind_include):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), bind_include)
                dst = os.path.join(include_dst, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(os.path.join(root, name), dst)
        # Reference configurations: upstream's install lands the config
        # samples under etc/, which is not part of the Conan layout; move
        # them wholesale to res/isc-dhcp.
        copy(self, "*", src=os.path.join(self.package_folder, "etc"),
             dst=os.path.join(self.package_folder, "res", "isc-dhcp"))
        shutil.rmtree(os.path.join(self.package_folder, "etc"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # Static link order: libdhcp and libdhcpctl consume libomapi; the
        # DHCP libraries consume the BIND closure (irs -> isccfg -> dns ->
        # isc).
        self.cpp_info.libs = ["dhcp", "dhcpctl", "omapi",
                              "irs", "isccfg", "dns", "isc"]

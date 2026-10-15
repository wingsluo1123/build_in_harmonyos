#!/usr/bin/env python3
"""Conan recipe — ddccontrol 1.0.3 (DDC/CI monitor control) for OHOS (HarmonyOS PC).

ddccontrol controls monitor parameters (brightness, contrast, RGB, ...) over
the DDC/CI bus.  It ships a CLI (`ddccontrol`), a D-Bus service
(`ddccontrol_service`), a privileged PCI/i2c helper (`ddcpci`), the
`libddccontrol` library with its headers and a pkg-config file.

Bootstrap: the source is the upstream GitHub *git tag* archive (codeload,
R39/PF7 — the Debian pool is blacklisted), so it ships **no** configure:
build() runs `autoreconf -fi` first.  Two device facts drive the
tool_requires list:

* The device's own ``/usr/local/bin/aclocal`` is a 1.17 driver paired with the
  1.16 share dir and aborts with ``Can't locate Automake/Config.pm`` (verified
  on this device; same as archives/l/l3afpad) — automake/1.18 comes from
  tool_requires so autoreconf finds a working aclocal on PATH.
* configure.ac uses ``IT_PROG_INTLTOOL`` (intltool.m4 at aclocal time,
  intltool-update on PATH at configure time) and ``AM_GNU_GETTEXT([external])``
  (autopoint runs inside autoreconf and installs po/Makefile.in.in + gettext
  m4; msgfmt/msgmerge are needed at configure and make time) — hence
  intltool/0.51.0 + gettext/0.22.5.1.

Configure features on OHOS:

* ``--disable-gnome``: the gddccontrol GUI hard-errors without gtk+-2.0
  development files, which are not packaged for OHOS.
* ``ac_cv_header_sys_io_h=no``: OHOS ships a stub <sys/io.h> that *compiles*
  but declares no inb/outb (verified), so HAVE_SYS_IO would pull
  intel810.c/sis.c — x86 legacy port-I/O VGA backends — and fail ddcpci's
  link with undefined ``inb``.  The pciutils/libpci path and the
  nvidia/radeon/via backends are unaffected.
* i2c-dev support stays ON: it is an open()-time runtime path; compile only
  needs <linux/types.h>/<linux/i2c-dev.h>, both verified present.
* ddcpci stays ON: configure's AC_CHECK_HEADERS(<pci/pci.h>) /
  AC_CHECK_LIB(pci, pci_alloc) probes are fed -I/-L of the conan pciutils
  package through CPPFLAGS/LDFLAGS.

Runtime capability disclosure (see notes.md): /dev/i2c-* and
/sys/class/i2c-dev do not exist (ENOENT), /dev/dri does not exist,
/sys/class/drm is EACCES for this process and no i2c/drm/smbus kernel module
is loaded — both hardware paths of DDC/CI are unusable at run time on this
device.  The consumer test therefore exercises only the -h / no-argument
text paths, which return before any device is opened.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DdccontrolConan(ConanFile):
    name = "ddccontrol"
    version = "1.0.3"
    description = "DDC/CI monitor control tool (CLI + D-Bus service + libddccontrol)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ddccontrol/ddccontrol"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be checked with `in ("Linux", "OHOS")`.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("ddccontrol supports OHOS armv8 only")

    def requirements(self):
        # configure.ac:91 PKG_CHECK_MODULES([LIBXML2], [libxml-2.0]) — hard
        # requirement (conf/monitor db are XML).
        self.requires("libxml2/2.15.3.1")
        # configure.ac:184 PKG_CHECK_MODULES([GIO_UNIX], [gio-unix-2.0 >= 2.30.0])
        # is unconditional (the D-Bus service/client is built on GDBus).
        self.requires("glib/2.88.3.1")
        # configure.ac:103-106 --enable-ddcpci (the default) probes
        # <pci/pci.h> and -lpci.
        self.requires("pciutils/3.13.0")
        # src/ddcpci/ddcpci.h and src/ddcpci/i2c-algo-bit.c include
        # <libintl.h> unconditionally and main.c calls bindtextdomain() under
        # HAVE_GETTEXT; musl has no gettext in libc, so the real libintl comes
        # from gettext (pmount/0.9.23 precedent).
        self.requires("gettext/0.22.5.1")

    def build_requirements(self):
        # Broken device aclocal (1.17 driver / 1.16 share dir, "Can't locate
        # Automake/Config.pm") — bootstrap must not use it (l3afpad precedent).
        self.tool_requires("automake/1.18")
        # LT_INIT needs ltmain.sh from a healthy libtoolize.
        self.tool_requires("libtool/2.5.4")
        # IT_PROG_INTLTOOL: intltool.m4 at aclocal time, intltool-update on
        # PATH at configure time.
        self.tool_requires("intltool/0.51.0")
        # AM_GNU_GETTEXT([external]) probes msgfmt/msgmerge/xgettext at
        # configure time and builds po/ at make time ("GNU gettext tools not
        # found; required for intltool" otherwise).
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URLs end in the tag name (".../tar.gz/refs/tags/1.0.3"),
        # which has no file extension, so Conan's get() deduces filename
        # "1.0.3" and unzip() falls back to the zip decoder → BadZipFile.
        # Pass an explicit *.tar.gz filename so unzip() selects the tar.gz
        # decoder (abcmidi/20260609 precedent, same first error verbatim).
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="ddccontrol-1.0.3.tar.gz",
        )

    def generate(self):
        # Upstream configure.ac asks pkg-config for `gio-unix-2.0`; conan glib
        # exposes that project as the `gio` component whose .pc name is
        # gio-2.0.  Same project, same headers (the unix API lives in gio/),
        # so alias the generated .pc name (appres/xproto precedent).
        self.dependencies["glib"].cpp_info.components["gio"].set_property(
            "pkg_config_name", "gio-unix-2.0"
        )
        PkgConfigDeps(self).generate()

        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-gnome",  # gtk+-2.0 not packaged for OHOS
                # Explicit (equal) build/host triplets: skips config.guess
                # entirely (its HarmonyOS support depends on which automake
                # copy autoreconf happens to pick) while keeping
                # cross_compiling=no semantics (klavaro precedent).  host_os
                # becomes `linux`, which the i2c block's `case linux*` expects.
                "--build=aarch64-linux",
                "--host=aarch64-linux",
                # Stub <sys/io.h> compiles but declares no inb/outb — forcing
                # the header probe false keeps the x86-only intel810.c/sis.c
                # backends out of ddcpci (see module docstring).
                "ac_cv_header_sys_io_h=no",
            ]
        )
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # Consumer-side environment rides the AutotoolsToolchain script, NOT
        # buildenv_info: conan 2.29.1's VirtualBuildEnv composes only the
        # *dependencies'* buildenv_info (profile + direct build requires +
        # host requires) and silently ignores the root recipe's own — verified
        # by source read and a `conan install` probe where a
        # `buildenv_info.define(...)` logged "DEFINED" yet never reached the
        # generated conanbuildenv script.  klavaro/3.14 uses this same
        # env=tc.environment() channel for its PATH/LD_LIBRARY_PATH additions.
        env = tc.environment()

        # (1) The daemon's BUILT_SOURCES rule runs `gdbus-codegen` from PATH;
        # it ships in glib's bindir.
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        if os.path.isdir(glib_bin):
            env.prepend_path("PATH", glib_bin)

        # (2) aclocal must find the macros configure.ac uses; the git archive
        # ships an empty AC_CONFIG_MACRO_DIR(m4), so collect every aclocal/m4
        # dir from the whole dependency graph (host AND build contexts —
        # intltool.m4 lives in the tool_requires intltool package) and prepend
        # them (conanbuild's dep-provided ACLOCAL_PATH stays appended).
        aclocal_dirs = []
        for ctx in (self.dependencies, self.dependencies.build):
            for dep in ctx.values():
                root = getattr(dep, "package_folder", None)
                if not root or not os.path.isdir(root):
                    continue
                for dirpath, dirnames, _ in os.walk(root):
                    if dirpath[len(root):].count(os.sep) > 3:
                        dirnames[:] = []
                        continue
                    if os.path.basename(dirpath) in ("aclocal", "m4"):
                        if dirpath not in aclocal_dirs:
                            aclocal_dirs.append(dirpath)
        own_m4 = os.path.join(self.source_folder, "m4")
        if os.path.isdir(own_m4):
            aclocal_dirs.append(own_m4)
        if aclocal_dirs:
            env.prepend_path("ACLOCAL_PATH", os.pathsep.join(aclocal_dirs))

        # (3) The conan gettext package bakes `prefix="/"` into its autopoint
        # shell script and compiles the relocation branch OUT
        # (`if test "no" = yes`), so autoreconf's autopoint call looks for its
        # data at "//share/gettext/archive.dir.tar.xz" and dies with
        # "infrastructure files for version 0.18.1 not found" (round-2 first
        # error, verbatim).  The script guards the default with
        # `: ${gettext_datadir="${datarootdir}/gettext"}` — an env-set value
        # wins — so export the package's real data dir (verified against the
        # cached package: archive.dir.tar.xz lives at share/gettext/).
        for dep in self.dependencies.build.values():
            if dep.ref.name != "gettext" or not dep.package_folder:
                continue
            data = os.path.join(dep.package_folder, "share", "gettext")
            if os.path.isfile(os.path.join(data, "archive.dir.tar.xz")):
                env.define("gettext_datadir", data)
                break

        # (4) PkgConfigDeps covers libxml2 (libxml-2.0.pc) and glib
        # (gio-unix-2.0.pc), but configure probes pciutils and libintl with
        # plain AC_CHECK_* — feed their -I/-L through the toolchain env.
        # (AutotoolsDeps is deliberately not used: it flattens every dep's
        # cpp_info.libs into LIBS, and gettext's flattening adds bogus -l
        # flags — pmount precedent.)
        for ref in ("pciutils", "gettext"):
            dep = self.dependencies[ref]
            agg = dep.cpp_info.aggregated_components()
            for inc in agg.includedirs:
                env.append("CPPFLAGS", "-I%s" % os.path.join(dep.package_folder, inc))
            for libdir in agg.libdirs:
                env.append("LDFLAGS", "-L%s" % os.path.join(dep.package_folder, libdir))

        # (5) -lintl into the global LIBS (round-6 first error, verbatim:
        # "ld.lld: error: undefined symbol: libintl_gettext" while linking
        # ddcpci).  The gettext package's libintl.h:169 does
        # `# define gettext libintl_gettext`, so every gettext() call in
        # src/ddcpci resolves to a symbol that only libintl.{a,so} defines;
        # AM_GNU_GETTEXT puts -lintl in INTLLIBS/LIBINTL, which upstream
        # wires into ddccontrol/service's LDFLAGS but NOT into
        # src/ddcpci/Makefile.am (its LDFLAGS is only -Wl,-z,now) — upstream
        # assumes glibc, where gettext lives in libc, so musl + external
        # gettext necessarily loses it (that "only ddcpci fails" contrast is
        # the root-cause proof).  Precedent: klavaro/3.14 docstring —
        # "recipe appends -L{libdir} -lintl to LIBS".  Counter-precedent
        # handled: l3afpad warns a bare -lintl in LIBS breaks configure's
        # conftest link — inapplicable here because -L<gettext>/lib is
        # already in LDFLAGS (verified present in the ddcpci link line), so
        # conftest's -lintl resolves too; automake's link line places LIBS
        # last, after the -L flags, which is the right order for static
        # libintl.a as well.
        env.append("LIBS", "-lintl")
        tc.generate(env=env)

    def _intltool_shim_dir(self):
        """Dir holding a patched `intltoolize` with the right data prefix.

        `autoreconf -fi` runs `intltoolize` (IT_PROG_INTLTOOL is in its
        known-programs list), and the conan intltool package's script bakes
        `prefix=/` (line 39, verified in the cached package) — so it looks
        for `//share/intltool/Makefile.in.in` and dies with
        "intltoolize: cannot copy …" (round-4 first error, verbatim).
        intltoolize derives nothing from $0, so no PATH wrapper helps: COPY
        the script and rewrite that one constant to the package folder, which
        makes pkgdatadir=<pkg>/share/intltool and aclocaldir=<pkg>/share/aclocal
        correct (l3afpad/0.8.18.1.11 shim, same class of baked-prefix bug as
        autopoint's).  Idempotent: replaced each bootstrap with the current
        package's path.
        """
        intltool_bin = None
        intltool_root = None
        for dep in self.dependencies.build.values():
            if dep.ref.name != "intltool" or not dep.package_folder:
                continue
            cand = os.path.join(dep.package_folder, "bin", "intltoolize")
            if os.path.isfile(cand):
                intltool_bin = cand
                intltool_root = dep.package_folder
                break
        if not intltool_bin:
            raise ConanException("intltoolize not found in the intltool package")
        shim_dir = os.path.join(self.build_folder, "toolshim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "intltoolize")
        with open(intltool_bin, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        if "prefix=/" not in text:
            raise ConanException(
                "unexpected intltoolize layout: no 'prefix=/' constant to rewrite"
            )
        text = re.sub(r"^prefix=/", "prefix=%s" % intltool_root, text, count=1, flags=re.M)
        with open(shim, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)
        os.chmod(shim, 0o755)
        self.output.info("intltoolize shim prefix -> %s" % intltool_root)
        return shim_dir

    def _bootstrap_configure(self):
        """Run autoreconf -fi — the git tag archive ships no configure.

        autopoint runs from inside autoreconf and installs po/Makefile.in.in
        plus the gettext m4 set into the tree (its `gettext_datadir` comes
        from the toolchain env); intltoolize runs next and takes the prefix
        shim; the remaining macro (intltool.m4) comes from ACLOCAL_PATH.
        The inline PATH assignment is deliberate: it is evaluated by the
        shell on top of the conanbuild env, so the shim definitively wins.
        """
        if os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("configure already present, skipping autoreconf")
            return
        shim_dir = self._intltool_shim_dir()
        self.run(
            'PATH="%s:$PATH" autoreconf -fi' % shim_dir,
            cwd=self.source_folder,
            env="conanbuild",
        )

    def _patch_configure_generated(self):
        """Idempotent patches on the freshly generated configure (build artifact).

        (a) Drop `umask 077` from config.status' scratch-dir creation:
        `(umask 077 && mktemp -d ./confXXXXXX)` on the setgid hmdfs volume
        makes a 0700 dir unwritable even for its creator (`can't create
        ./confXXXXXX/subs1.awk: Permission denied` — E110/E112;
        l3afpad/appres/pmount precedent).

        (b) Bypass the XML::Parser probe: intltool.m4:146 guards it with
        `if test "x$2" != "xno-xml"` — intltool's own official off-switch
        (second argument `no-xml`).  In the generated configure the literal
        appears exactly once (`if test "x" != "xno-xml"; then`, grep -c = 1
        verified); inverting it to `=` skips the block.  Skipping is correct
        for this package on three counts: the device perl has NO XML::Parser
        at all (`perl -MXML::Parser` -> rc=2 `Can't locate XML/Parser.pm`,
        hnp perl identical, so the probe can never pass here); building with
        `--disable-gnome` + doc off leaves **zero xml.in consumers**
        (klavaro/3.14 needed its extra `-x` merge shim only for
        klavaro.appdata.xml.in — none exists in this tree); and
        klavaro/3.14's patch0001 already shipped the same bypass verbatim
        ("XML::Parser perl module cannot dlopen its XS extension from OHOS
        app-sandbox paths — patch 0001 bypasses the configure check").
        Same class as the `ac_cv_header_sys_io_h=no` cache override: a
        bypass of a probe inapplicable to this build, not a mock — nothing
        fakes a module load.
        """
        path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(path):
            raise ConanException("configure not found after autoreconf")
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()

        if "umask 077" in text:
            text, n = re.subn(r"umask 077", "umask 022", text)
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(text)
            self.output.info("patched %d umask 077 occurrence(s) in configure" % n)
        else:
            self.output.info("configure has no umask 077 (nothing to patch)")

        guard = 'if test "x" != "xno-xml"; then'
        if guard in text:
            text = text.replace(guard, 'if test "x" = "xno-xml"; then')
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(text)
            self.output.info("bypassed XML::Parser probe (intltool.m4 no-xml off-switch)")
        elif 'if test "x" = "xno-xml"; then' in text:
            self.output.info("XML::Parser probe already bypassed")
        else:
            raise ConanException(
                "intltool no-xml guard not found in generated configure — "
                "unexpected intltool.m4 layout, refusing to configure blindly"
            )

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_configure()
        self._patch_configure_generated()

        autotools = Autotools(self)
        autotools.configure()
        # -j1: the hmdfs jobserver fifo raises EPERM (E074).
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Installed: lib/libddccontrol.a + lib/libddccontrol_dbus_client.a,
        # include/ddccontrol/*.h, lib/pkgconfig/ddccontrol.pc,
        # bin/ddccontrol, libexec/ddccontrol/{ddcpci,ddccontrol_service},
        # man page, D-Bus spec/service/conf, locale catalogs.
        self.cpp_info.libs = ["ddccontrol", "ddccontrol_dbus_client"]
        # Headers land in include/ddccontrol/ (pkgincludedir) — -Iinclude
        # matches the shipped ddccontrol.pc Cflags.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]

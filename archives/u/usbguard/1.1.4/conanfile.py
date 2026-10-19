#!/usr/bin/env python3
"""Conan recipe for usbguard 1.1.4 — USB device authorization toolset.

USBGuard protects a machine against rogue USB devices by implementing a
device authorization policy: `libusbguard` (the API library), the `usbguard`
CLI, `usbguard-rule-parser` and the `usbguard-daemon` service.  Build system
is autotools (configure.ac/Makefile.am); the C++ sources are C++17.

Upstream source tree
--------------------
The GitHub tag archive ships `configure.ac`/`Makefile.am` only — no generated
`configure` — so build() bootstraps the tree with `autoreconf` (dnstap-ldns
0.2.1 / zvbi 0.2.44 precedents: `automake`/`libtool`/`m4` come from
tool_requires, `autoconf` from the device under /data/service/hnp/bin).

usbguard keeps PEGTL and Catch2 as **git submodules** under
`src/ThirdParty/`; GitHub archives never contain submodule contents, so the
two directories arrive empty.  source() therefore fetches exactly the two
commits pinned in the 1.1.4 tree (PEGTL 3.2.5, Catch2 v2.13.8 — see
conandata.yml) and unpacks them in place, mirroring what upstream's own
release/distcheck flow does with `--with-bundled-pegtl --with-bundled-catch`.

Dependency footprint and OHOS degradations
------------------------------------------
Required: libqb (IPC/event loop), libsodium (default crypto backend used by
`Hash`), protobuf + protoc (IPC message code generation).

Optional back-ends that have no meaning / no headers on the OHOS PC target
are switched off with their own upstream switches (all declare a clean
"turned OFF" path in configure.ac):

  --disable-audit      Linux Audit backend (no auditd; ohpcd libaudit 2.7.4
                       is also below the >= 2.7.7 the recipe wants)
  --disable-seccomp    seccomp allow-list sandbox
  --disable-libcapng   POSIX 1003.1e capability dropping
  --disable-umockdev   umockdev-based device manager
  --without-dbus       D-Bus bridge service (no dbus/gio/polkit on target)
  --without-polkit     PolicyKit policy install (checked independently of
                       --without-dbus by configure.ac, so it must be set too)
  --without-ldap       LDAP rule source
  --with-bash-completion-dir=no   bash-completion data files

Only the crypto backend is selected explicitly: `--with-crypto-library=sodium`
(the upstream default), satisfied by the ohpcd libsodium package.

OHOS machinery (each item re-probed against this tarball / the device)
----------------------------------------------------------------------
* Compilers come from the profile's `tools.build:compiler_executables` via
  AutotoolsToolchain; no bare `$CC`/`$CXX` in self.run() (R33).
* The generated `configure` carries `umask 077` for its scratch directory;
  hmdfs decides traversal on the group bits where chmod is a no-op, so the
  directory is untraversable (EACCES on everything inside).  Rewritten to 022
  after autoreconf, before configure (zvbi/dnstap-ldns precedent).  A missing
  `umask 077` is an error so a future regenerated configure cannot silently
  void the workaround.
* `make -j1`: parallel make on hmdfs has hit the jobserver mkfifo EPERM
  (E074, dnstap-ldns precedent).
* Static libusbguard + dynamically-linked-libc++ binaries (`--disable-shared
  --enable-static`), so the packaged CLI/daemon run without an rpath into the
  Conan cache; consumers still get libusbguard.a.
"""

import hashlib
import os
import shutil
import ssl
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               rm, unzip)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class UsbguardConan(ConanFile):
    name = "usbguard"
    version = "1.1.4"
    description = ("USB device authorization toolset: libusbguard, usbguard CLI, "
                   "usbguard-rule-parser and usbguard-daemon")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/usbguard/usbguard"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libqb/2.0.10")
        self.requires("libsodium/1.0.22")
        # protobuf/3.17.3 pins zlib/1.3.1 while libqb -> glib/2.84.0.1 pins
        # zlib/1.3.1.1, which conan reports as a graph version conflict.
        # Unify on the HarmonyOS-published 1.3.1.1 (zbackup 1.5 precedent:
        # same override, same reasoning).
        self.requires("protobuf/3.17.3")
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        # The tag archive has no generated configure; autoreconf needs the
        # automake/libtool/m4 family (autoconf + m4 exist on the device under
        # /data/service/hnp/bin).  protobuf is also a *build* requirement so
        # that VirtualBuildEnv puts its bin/protoc on PATH: configure.ac does
        # AC_CHECK_PROGS(PROTOC) and the %.pb.cc rule invokes it (zbackup 1.5
        # precedent for the same requires+tool_requires pairing).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")
        self.tool_requires("protobuf/3.17.3")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"usbguard is adapted for Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch the three official tarballs and lay out the source tree.

        PEGTL/Catch are git submodules and are absent from the usbguard
        archive, so the exact commits pinned by the 1.1.4 tree are unpacked
        into src/ThirdParty/ (see conandata.yml for the commit ids).
        """
        layouts = {
            "usbguard": "",
            "pegtl": "src/ThirdParty/PEGTL",
            "catch": "src/ThirdParty/Catch",
        }
        for name, relative in layouts.items():
            entry = self.conan_data["sources"][name]
            archive = os.path.join(self.source_folder, f"{name}-source.tar.gz")
            self._fetch(entry["url"], archive, entry["sha256"])
            destination = (os.path.join(self.source_folder, relative)
                           if relative else self.source_folder)
            os.makedirs(destination, exist_ok=True)
            unzip(self, archive, destination=destination, strip_root=True)
            os.unlink(archive)

    def generate(self):
        # .pc files for libqb/libsodium/protobuf land in the generators
        # folder, which AutotoolsToolchain prepends to PKG_CONFIG_PATH — this
        # is how the PKG_CHECK_MODULES() calls in configure.ac resolve.
        PkgConfigDeps(self).generate()
        self._drop_spurious_libqb_requires()
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        # E119: the OHOS sysroot's <linux/socket.h> and <sys/socket.h> both
        # define `struct sockaddr_storage` (unlike glibc, where UAPI
        # linux/libc-compat.h suppresses the duplicate).  usbguard pulls both
        # into the same TU (DeviceManagerBase.cpp: <linux/netlink.h> then
        # <sys/socket.h>).  OHOS's sys/socket.h guards its copy with
        # `#ifndef __MUSL__`, so defining __MUSL__ removes the duplicate and
        # leaves the UAPI definition (agetty/aircrack precedent).  __MUSL__ is
        # referenced by exactly one sysroot header (sys/socket.h), so the flag
        # is narrowly scoped.
        toolchain.extra_defines.append("__MUSL__")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_private_tmpdir()
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub tag 归档常见），先 autoreconf 自举")
            autotools.autoreconf()
        self._restore_script_modes()
        self._relax_umask_in_autotools_scripts()
        self._teach_config_guess_harmonyos()
        autotools.configure()
        autotools.make(args=["-j1"])
        # ── 上游官方测试 (必做, R51) ──
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # libtool archives are not relocatable and must not be shipped.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["usbguard"]
        self.cpp_info.bindirs = ["bin"]
        # libusbguard.a is a static archive whose objects reference libqb
        # (qb_ipcc_*), libsodium (crypto_hash_sha256_*) and protobuf (IPC
        # message types), so consumers must link them as well.  Upstream's
        # installed libusbguard.pc only lists libqb, which is not enough for
        # a static consumer.
        self.cpp_info.requires = ["libqb::libqb", "libsodium::libsodium",
                                  "protobuf::protobuf"]
        self.cpp_info.system_libs = ["pthread"]
        # Upstream installs its headers to <includedir>/usbguard and ships
        # libusbguard.pc; keep both names so pkg-config / CMake consumers match.
        self.cpp_info.set_property("pkg_config_name", "libusbguard")
        self.cpp_info.set_property("cmake_file_name", "usbguard")
        self.cpp_info.set_property("cmake_target_name", "usbguard::usbguard")

    # ── pkg-config shim ─────────────────────────────────────────────────

    def _drop_spurious_libqb_requires(self):
        """Drop the `Requires:` line from the generated libqb.pc.

        libqb/2.0.10's recipe declares glib/libxml2/check as *host*
        requirements (they are only meaningful for libqb's own test suite),
        and PkgConfigDeps turns those into `Requires: glib-2.0-unofficial
        libxml-2.0 check` in the generated libqb.pc.  Through
        PKG_CHECK_MODULES([qb], [libqb]) that propagates into usbguard's link
        line, so the built binaries pick up DT_NEEDED entries for the glib
        family and check, which then are unresolvable at run time
        ("Error loading shared library libgthread-2.0.so.0") and fail every
        `make check` case.

        libqb itself does not use any of them: `nm -u libqb.a` shows only
        libc/pthread references (plus its own qb_* symbols), and the
        ohpcd glib/2.84.0.1 package only ships a *shared* variant, so a
        static-link workaround is not available.  Removing the spurious
        Requires keeps `-lqb -lpthread` (libqb.a is self-contained) and
        leaves the installed binaries free of glib.
        """
        pc = Path(self.generators_folder, "libqb.pc")
        if not pc.is_file():
            raise ConanException(f"generated pkg-config file is missing: {pc}")
        kept = [line for line in pc.read_text(encoding="utf-8").splitlines(True)
                if not line.startswith(("Requires:", "Requires.private:"))]
        dropped = len(pc.read_text(encoding="utf-8").splitlines()) - len(kept)
        pc.write_text("".join(kept), encoding="utf-8", newline="\n")
        self.output.info(
            f"libqb.pc: dropped {dropped} spurious Requires line(s) "
            f"(glib/libxml2/check are not used by libqb itself)")

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            "--prefix=/",
            "--disable-dependency-tracking",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--with-crypto-library=sodium",
            "--disable-audit",
            "--disable-seccomp",
            "--disable-libcapng",
            "--disable-umockdev",
            "--without-dbus",
            "--without-polkit",
            "--without-ldap",
            "--with-bash-completion-dir=no",
            # Bundled PEGTL/Catch (unpacked into src/ThirdParty in source()).
            "--with-bundled-pegtl",
            "--with-bundled-catch",
        ]

    # ── OHOS build machinery ────────────────────────────────────────────

    def _prepare_private_tmpdir(self):
        """Export a writable TMPDIR for the build and the upstream test suite.

        /tmp on the OHOS device is a read-only filesystem (mount attempt
        returns EROFS), and the upstream regression test derives its scratch
        path from TMPDIR (see patch 0004).  A private directory under the
        Conan build folder is used so `make check` is runnable without
        depending on a TMPDIR supplied by the caller (abiword-plugin-* /
        accel-config precedent).
        """
        tmpdir = Path(self.build_folder, ".tmp")
        tmpdir.mkdir(parents=True, exist_ok=True)
        os.environ["TMPDIR"] = str(tmpdir)
        self.output.info(f"TMPDIR for build/test: {tmpdir}")

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490).

        On hmdfs the executable bit of files unpacked from the source archive
        is not guaranteed to survive, which breaks `./configure` and the
        install helpers.  autoreconf normally recreates them with the right
        mode, but restoring it explicitly is cheap and removes the failure
        mode entirely.
        """
        candidates = [
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "ar-lib",
            "mkinstalldirs", "test-driver",
        ]
        for relative in candidates:
            path = Path(self.source_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)
        for helper in Path(self.source_folder, "config").glob("*"):
            if helper.is_file():
                helper.chmod(helper.stat().st_mode | 0o111)
        for helper in Path(self.source_folder, "m4").glob("*.sh"):
            if helper.is_file():
                helper.chmod(helper.stat().st_mode | 0o111)

    def _relax_umask_in_autotools_scripts(self):
        """Rewrite `umask 077` -> `umask 022` in the generated autotools scripts.

        Device-verified: hmdfs forces the setgid bit on every directory and
        decides traversal/write access on the group bits, where chmod is a
        no-op.  `umask 077 && mktemp -d` therefore yields a `drwx--S---`
        directory that even its owner cannot write into (E114 / E011).

        Both the top-level configure (its own confXXXXXX scratch dir) and the
        auxiliary scripts it spawns are affected, so every generated helper
        that carries the pattern is rewritten — configure would otherwise
        still fail inside `config.guess`, which creates its `cgXXXXXX`
        directory with `umask 077` too.  Must run *after* autoreconf, which
        regenerates these files.

        A future regeneration of the scripts cannot silently void the fix:
        when no file carries the pattern any more the build stops here.
        """
        candidates = ["configure", "config.sub", "config.guess", "ltmain.sh",
                      "config.status", "depcomp", "install-sh"]
        paths = [Path(self.source_folder, name) for name in candidates]
        config_dir = Path(self.source_folder, "config")
        if config_dir.is_dir():
            paths.extend(sorted(config_dir.glob("*")))
        rewritten = []
        for path in paths:
            if not path.is_file() or path.is_symlink():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "umask 077" not in content:
                continue
            path.write_text(content.replace("umask 077", "umask 022"),
                            encoding="utf-8", newline="\n")
            rewritten.append(path.name)
        if not rewritten:
            raise ConanException(
                "umask contract changed: no 'umask 077' found in the generated "
                "autotools helper scripts; the hmdfs workaround has nothing to "
                "rewrite")
        self.output.info("rewrote umask 077 -> 022 in: "
                         + ", ".join(sorted(set(rewritten))))

    def _teach_config_guess_harmonyos(self):
        """Teach the generated config.guess about HarmonyOS.

        Iron rule R1 forbids passing `--build`/`--host`: a native build must
        let configure determine its own triplet.  On this device `uname -s`
        reports "HarmonyOS" (HongMeng kernel) over a standard aarch64 Linux
        toolchain/userland, so upstream config.guess matches none of its
        cases, cannot compile its probe and aborts with "cannot guess build
        type; you must specify one".

        Normalizing UNAME_SYSTEM to Linux yields `aarch64-unknown-linux-gnu`
        — the very triplet this archive's other recipes obtain by passing
        `--build`/`--host` explicitly.  Doing it here keeps the configure
        command line minimal and lets the *native* detection work.
        """
        anchor = 'UNAME_SYSTEM=`(uname -s) 2>/dev/null` || UNAME_SYSTEM=unknown'
        injection = anchor + '''
# HarmonyOS PC: uname -s reports HarmonyOS while the toolchain and userland
# are the standard aarch64 Linux ones.  Normalize so the Linux detection path
# (and the aarch64-unknown-linux-* triplet) applies.
case $UNAME_SYSTEM in
  [Hh]armonyOS) UNAME_SYSTEM=Linux ;;
esac'''
        patched = []
        for relative in ("config/config.guess", "config.guess"):
            path = Path(self.source_folder, relative)
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if "[Hh]armonyOS) UNAME_SYSTEM=Linux" in text:
                continue
            if anchor not in text:
                raise ConanException(
                    f"config.guess anchor not found in {path}: refusing to "
                    f"guess a build triplet silently")
            path.write_text(text.replace(anchor, injection, 1),
                            encoding="utf-8", newline="\n")
            patched.append(relative)
        if not patched:
            raise ConanException(
                "no config.guess found after autoreconf — cannot teach it "
                "about HarmonyOS")
        self.output.info("taught config.guess about HarmonyOS: "
                         + ", ".join(patched))

    # ── download helpers ────────────────────────────────────────────────

    def _ca_bundle(self):
        candidates = []
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        conan_home = os.getenv("CONAN_HOME") or os.path.join(
            os.path.expanduser("~"), ".conan2")
        candidates.append(os.path.join(conan_home, "cacert.pem"))
        candidates.append(os.getenv("SSL_CERT_FILE") or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "no CA bundle found for the source download: looked for certifi's "
            "cacert, $CONAN_HOME/cacert.pem and $SSL_CERT_FILE")

    def _fetch(self, url, destination, sha256, attempts=3):
        destination = Path(destination)
        staging = destination.with_name(destination.name + ".part")
        candidates = list(url) if isinstance(url, (list, tuple)) else [url]
        # Prefer a local file:// candidate (CI pre-download rewrites the
        # official URL to a cached file:// path) so the build never depends
        # on network when a pre-downloaded copy exists.
        candidates = ([c for c in candidates if c.startswith("file:")]
                      + [c for c in candidates if not c.startswith("file:")])
        last = None
        for candidate in candidates:
            tries = 1 if candidate.startswith("file:") else attempts
            for attempt in range(1, tries + 1):
                try:
                    if candidate.startswith("file:"):
                        shutil.copyfile(url2pathname(urlparse(candidate).path),
                                        staging)
                    else:
                        context = ssl.create_default_context(
                            cafile=self._ca_bundle())
                        request = urllib.request.Request(
                            candidate, headers={"User-Agent": "conan"})
                        with urllib.request.urlopen(request, timeout=120,
                                                    context=context) as response:
                            payload = response.read()
                            status = response.status
                        staging.write_bytes(payload)
                        self.output.info(
                            f"downloaded {len(payload)} bytes (HTTP {status}) "
                            f"from {candidate}")
                    digest = hashlib.sha256(staging.read_bytes()).hexdigest()
                    if digest != sha256:
                        raise ConanException(
                            f"sha256 mismatch for {candidate}: expected "
                            f"{sha256}, got {digest}")
                    os.replace(staging, destination)
                    return
                except Exception as error:  # noqa: BLE001 - reported verbatim
                    last = error
                    self.output.warning(
                        f"attempt {attempt}/{tries} failed for {candidate}: "
                        f"{type(error).__name__}: {error}")
                    if staging.exists():
                        staging.unlink()
                    if attempt < tries:
                        time.sleep(5)
        raise ConanException(f"could not download {url}: {last}")

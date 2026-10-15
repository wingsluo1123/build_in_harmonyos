#!/usr/bin/env python3
"""Conan recipe — libreswan pluto 5.24.1 (OHOS / HarmonyOS PC adaptation).

pluto is the IPsec IKEv1/IKEv2 daemon of libreswan. Upstream ships a custom
top-level Makefile (no configure, no CMake), so this recipe drives the native
`make programs` build directly.

The OHOS adaptation (see notes.md / patches/) is encoded here:
  * OSDEP=linux + LINUX_VARIANT=generic  (no HarmonyOS.mk, no /etc/os-release)
  * 10 optional deps disabled (unbound/dnssec/ldns/libcurl/systemd-watchdog/
    nflog/nftables/iptables/pam/libcap-ng/cat) — absent from the OHOS registry
  * crypto backend = NSS (NOT OpenSSL): NSS_CFLAGS/NSS_LDFLAGS are derived from
    the conan nss/nspr/libevent packages (see _dep_paths below)
  * -Werror relaxed (WERROR_CFLAGS=) — OHOS bionic-style headers emit warnings
    that upstream's -Werror rejects (e.g. CMSG_NXTHDR sign-compare)
  * OHOS <linux/socket.h> lacks the glibc struct guard around sockaddr_storage,
    so it collides with <sys/socket.h>. The build pre-defines its file guard
    (-D_UAPI_LINUX_SOCKET_H) and force-includes ohos_compat.h (re-provides the
    kernel typedef __kernel_sa_family_t) — a pure build-time fix, no source
    modification of the kernel-header consumers.
  * source patches (patches/): getpass(3) stdin fallback (absent from OHOS
    libc) + XFRM uAPI compat block (newer XFRM attributes the OHOS kernel
    header predates; best-effort, R40: compiles != functional)
  * xmlto stub: manpage generation is doc-only and xmlto is not in the OHOS
    registry, so a stub emits empty manpages and the build completes cleanly.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    chmod,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    save,
)


# Stub xmlto: the real tool is unavailable on OHOS and manpages are
# documentation-only. It mirrors the upstream manpage contract (mk/manpages.mk):
# for the "man" format it emits one empty file per <refname> that
# packaging/utils/refnames.sh derives from the input XML (a single XML may hold
# several manpages, e.g. ipsec-add.8.xml -> ipsec-add.8 + ipsec-ondemand.8);
# for "html" it emits <stem>.html. Empty content is acceptable (doc-only).
_XMLTO_STUB = r"""#!/bin/sh
# OHOS stub xmlto (doc-only manpage placeholder; real xmlto unavailable).
out=""; fmt="man"; prev=""; xml=""; marg=""
for a in "$@"; do
  case "$prev" in
    -o) out="$a" ;;
    -m) marg="$a" ;;
  esac
  case "$a" in
    *html*) fmt="html" ;;
    *.xml) xml="$a" ;;
  esac
  prev="$a"
done
[ -z "$xml" ] && exit 0
[ -n "$out" ] && mkdir -p "$out"
top_srcdir=""
if [ -n "$marg" ]; then
  top_srcdir=$(dirname "$(dirname "$marg")")
fi
refs=""
if [ -n "$top_srcdir" ] && [ -f "$top_srcdir/packaging/utils/refnames.sh" ]; then
  refs=$(sh "$top_srcdir/packaging/utils/refnames.sh" "$xml" 2>/dev/null)
fi
[ -z "$refs" ] && refs=$(basename "$xml" .xml)
if [ "$fmt" = "html" ]; then
  [ -n "$out" ] && : > "$out/$(basename "$xml" .xml).html"
else
  for r in $refs; do
    [ -n "$out" ] && : > "$out/$r"
  done
fi
exit 0
"""

# OHOS header-compat shim, force-included by the build (-include ohos_compat.h)
# together with -D_UAPI_LINUX_SOCKET_H. OHOS ships a bionic-style
# <linux/socket.h> with only a *file* guard and no struct-level guard on
# sockaddr_storage, so any <linux/...> header pulling it in (e.g.
# <linux/rtnetlink.h> via <linux/netlink.h>) redefines sockaddr_storage,
# clashing with the libc <sys/socket.h> definition. Pre-defining the file
# guard suppresses the redundant kernel copy; this header then re-provides the
# kernel typedef that the suppressed <linux/socket.h> would otherwise define.
# It is created at build time (not shipped as a patch) because it is a
# build-only shim, not part of the public interface.
_OHOS_COMPAT_HEADER = """\
#ifndef __KERNEL_SA_FAMILY_T_DEFINED
# define __KERNEL_SA_FAMILY_T_DEFINED
/* <linux/netlink.h> and other <linux/...> headers use this kernel typedef. */
typedef unsigned short __kernel_sa_family_t;
#endif
"""


class PlutoConan(ConanFile):
    name = "pluto"
    version = "5.24.1"
    description = ("Libreswan IPsec IKEv1/IKEv2 daemon (pluto), adapted to "
                   "OpenHarmony PC (aarch64, clang).")
    license = "GPL-2.0-or-later"
    homepage = "https://libreswan.org"
    # Official upstream release (R39); the same URL + sha256 is pinned in
    # conandata.yml, which source() actually reads.
    url = "https://github.com/libreswan/libreswan/releases/download/v5.4.1/libreswan-5.4.1.tar.gz"
    topics = ("ipsec", "ike", "vpn", "libreswan")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # NSS is libreswan's crypto backend (NOT OpenSSL).
        self.requires("nss/3.118.1")
        # libreswan includes NSPR headers directly (prinit.h via NSS) and links
        # libnspr4/libplc4/libplds4; nss pulls nspr transitively, but we
        # reference it explicitly (its headers/libs are on the build line).
        self.requires("nspr/4.37", transitive_headers=True, transitive_libs=True)
        self.requires("libevent/2.1.13")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_paths(self):
        """Resolve the NSS/NSPR/libevent include & lib dirs from the conan
        dependency package folders (matches the verified OHOS package layout).
        NSS: <pkg>/include (flat headers)  <pkg>/lib
        NSPR: <pkg>/include/nspr          <pkg>/lib
        libevent: <pkg>/include           <pkg>/lib
        """
        nss = self.dependencies["nss"]
        nspr = self.dependencies["nspr"]
        le = self.dependencies["libevent"]
        return {
            "nss_inc": os.path.join(nss.package_folder, "include"),
            "nspr_inc": os.path.join(nspr.package_folder, "include", "nspr"),
            "le_inc": os.path.join(le.package_folder, "include"),
            "nss_lib": os.path.join(nss.package_folder, "lib"),
            "nspr_lib": os.path.join(nspr.package_folder, "lib"),
            "le_lib": os.path.join(le.package_folder, "lib"),
        }

    def build(self):
        apply_conandata_patches(self)

        # Stub xmlto into the build tree and point the make system at it.
        # NOTE: invoke via `sh <stub>` — on HMDFS (HarmonyOS) chmod is ignored
        # (permissions are fixed at 660, no execute bit; see knowledge E046 /
        # R49), so a directly-executed file gets "Permission denied". Running
        # the stub through the shell interpreter only needs read permission.
        tools_dir = os.path.join(self.build_folder, "ohc-tools")
        os.makedirs(tools_dir, exist_ok=True)
        xmlto = os.path.join(tools_dir, "xmlto")
        save(self, xmlto, _XMLTO_STUB)
        try:
            chmod(self, xmlto, 0o755)  # best-effort (no-op on HMDFS)
        except Exception:
            pass

        p = self._dep_paths()
        nss_cflags = "-I{0} -I{1} -I{2}".format(
            p["nss_inc"], p["nspr_inc"], p["le_inc"])
        nss_ldflags = (
            "-L{0} -L{1} -L{2} "
            "-lnss3 -lsmime3 -lnssutil3 -lfreebl3 -lplc4 -lplds4 "
            "-lnspr4 -levent_core -levent_pthreads").format(
                p["nss_lib"], p["nspr_lib"], p["le_lib"])
        # Build-time OHOS header-compat fix (see _OHOS_COMPAT_HEADER): create
        # the shim in the source tree and force-include it. Created here (not
        # via a patch) because it is a build-only shim, not a source change.
        ohos_compat = os.path.join(self.source_folder, "ohos_compat.h")
        save(self, ohos_compat, _OHOS_COMPAT_HEADER)
        cflags = "-O2 -D_UAPI_LINUX_SOCKET_H -include {0}".format(ohos_compat)

        # Optional deps absent from the OHOS registry (feature-trimmed, R40).
        disabled = [
            "USE_UNBOUND=false", "USE_DNSSEC=false", "USE_LDNS=false",
            "USE_LIBCURL=false", "USE_SYSTEMD_WATCHDOG=false",
            "USE_NFLOG=false", "USE_NFTABLES=false", "USE_IPTABLES=false",
            "USE_AUTHPAM=false", "USE_LIBCAP_NG=false", "USE_CAT=false",
        ]
        prefix = self.package_folder
        # Quote the multi-word flag values: self.run() executes through a shell
        # (shell=True), so CFLAGS/NSS_CFLAGS/NSS_LDFLAGS must be a SINGLE shell
        # argument, else e.g. `-include` is parsed as make's own top-level
        # option (make -include reads a makefile) and the build aborts with
        # make's usage. Single quotes are safe here (values contain no quotes,
        # no $, no backticks).
        make_flags = " ".join(disabled) + " " + " ".join([
            "OSDEP=linux",
            "LINUX_VARIANT=generic",
            "WERROR_CFLAGS=",
            "XMLTO='sh {0}'".format(xmlto),
            "CFLAGS='{0}'".format(cflags),
            "NSS_CFLAGS='{0}'".format(nss_cflags),
            "NSS_LDFLAGS='{0}'".format(nss_ldflags),
            "PREFIX={0}".format(prefix),
        ])
        # In-source build (upstream Makefile writes OBJ.linux.aarch64/ inside
        # the source tree).
        cwd = self.source_folder
        # CI workers run under a tight cgroup pids limit: bare cpu_count()
        # (-j20 on a 20-core host) exhausts it (make: "Resource temporarily
        # unavailable", EAGAIN on fork). Read tools.build:jobs conf (CI
        # profile can override) and clamp the resolved value to 4 regardless
        # of source, so a profile override cannot re-exhaust the pids limit.
        jobs = min(int(self.conf.get("tools.build:jobs",
                                     default=os.cpu_count() or 1)), 4)
        # `make programs` covers all of programs/ (pluto, whack, cavp,
        # algparse, ...). algparse is shipped as an upstream self-test entry
        # (see package()/test.sh).
        self.run("make programs " + make_flags + " -j{0}".format(jobs), cwd=cwd)
        # Upstream self-test checkers live under testing/programs/ (outside
        # `make programs`). Build the three zero-arg self-test tools
        # explicitly so package() can ship them for the L1 suite. The other
        # testing/programs entries are unrunnable here: getpeercon_server is
        # USE_LABELED_IPSEC-gated (libselinux absent from the OHOS registry),
        # kernel/ is a KVM guest template, ttodatacheck is a manual
        # diagnostic with no upstream test harness (see notes.md).
        for tool in ("enumcheck", "hunkcheck", "keyidcheck"):
            self.run("make -C testing/programs/{0} {1}".format(tool, make_flags),
                     cwd=cwd)

    def package(self):
        # pluto is a daemon (application); ship the built binary. The build
        # tree (in-source) is <source_folder>/OBJ.<osdep>.<arch>/programs/pluto.
        objdir = os.path.join(self.source_folder, "OBJ.linux.aarch64")
        pluto = os.path.join(objdir, "programs", "pluto", "pluto")
        if not os.path.isfile(pluto):
            raise ConanException("pluto binary not found at {0}".format(pluto))
        mkdir(self, os.path.join(self.package_folder, "bin"))
        copy(self, "pluto", src=os.path.dirname(pluto),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Upstream self-test entry points (see build() above): shipped so the
        # L1 suite (test.sh) executes real upstream test code in CI, not just
        # the daemon banner. Names keep the upstream convention (internal
        # tools carry a leading underscore).
        for rel, binname in (
            (os.path.join("programs", "algparse"), "algparse"),
            (os.path.join("testing", "programs", "enumcheck"), "_enumcheck"),
            (os.path.join("testing", "programs", "hunkcheck"), "_hunkcheck"),
            (os.path.join("testing", "programs", "keyidcheck"), "_keyidcheck"),
        ):
            src = os.path.join(objdir, rel, binname)
            if not os.path.isfile(src):
                raise ConanException("{0} not found at {1}".format(binname, src))
            copy(self, binname, src=os.path.dirname(src),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # The OHOS compat header (ohos_compat.h) is a build-only shim, force
        # -included during the build; it is not part of the package.

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # pluto is a daemon (application); it provides no libraries.
        self.cpp_info.libs = []
        # Runtime dependency fix: pluto is dynamically linked against the NSS
        # shared libraries (libnss3.so / libsmime3.so / libnssutil3.so /
        # libfreebl3.so — the nss package ships both .a and .so, and the build
        # links the .so via explicit -L/-l). But the nss package is registered
        # as STATIC (options.shared defaults to False) in the conan graph, so
        # conan does NOT add its lib dir to the consumer's LD_LIBRARY_PATH
        # (VirtualRunEnv only propagates libdirs of "shared" requires). Add the
        # nss lib dir to the runenv explicitly so the NSS .so runtime deps
        # resolve. NSPR (shared=True default) and libevent are already in the
        # runenv.
        nss = self.dependencies["nss"]
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(nss.package_folder, "lib"))

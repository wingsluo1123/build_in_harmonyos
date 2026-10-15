#!/usr/bin/env python3
"""Conan recipe — dma 0.14 (Makefile).

dma (DragonFly Mail Agent) is a minimalist MTA: it delivers mail locally to
/var/mail and relays to a smart host over plain SMTP or SSL/TLS, playing the
sendmail(8) role for small setups. Upstream ships a bare BSD-style Makefile —
no configure, no Makefile.am, no CMakeLists.txt, no meson.build — so the build
system is `makefile` (verified by exhaustive file presence check: every
autotools/cmake/meson marker is absent while Makefile exists).

Upstream make targets used here:
    all   -> dma + dma-mbox-create        (aliases_parse.y / aliases_scan.l are
                                           regenerated, hence bison+flex)
    install is deliberately NOT invoked: see the OHOS notes below.

OHOS notes (measured on-device, 2026-10-08):
  - The upstream `install` target is unusable on OHOS as written
    (Makefile:53-54):
        ${INSTALL} -m 2755 -o root -g mail dma            ${SBIN}
        ${INSTALL} -m 4754 -o root -g mail dma-mbox-create ${LIBEXEC}
    four stacked walls, each individually confirmed:
      1. `install` is not on PATH at all  -> rc=127 (command not found)
      2. `-o root`  -> running uid is 20020084, not root
      3. `-g mail`  -> the `mail` group does not exist
                       (grp.getgrnam('mail') -> KeyError)
      4. `-m 4754` (setuid) / `-m 2755` (setgid) bits are not preserved by
         the filesystem: chmod u+s returns ok but a follow-up stat reports
         setuid=False (mode observed 0o770, not even the 0o755 requested)
    Therefore package() hand-installs the build outputs with copy()+chmod,
    which is the documented Makefile-family approach and does not modify any
    upstream file.
  - musl/OHOS bundles the resolver into libc, so the upstream default
    `LDADD?=-lssl -lcrypto -lresolv` (Makefile:18) must be overridden to
    drop `-lresolv` (see 经验文档/适配检查清单.md, Makefile §2). The override
    is passed on the make command line, which has higher precedence than the
    Makefile's `LDADD?=` — no upstream file is edited.
  - CFLAGS is intentionally NOT overridden: the Makefile appends
    -DDMA_VERSION/-DLIBEXEC_PATH/-DCONF_PATH to it, and losing those would
    trip `#error Please define CONF_PATH` in dma.h. OpenSSL include paths
    travel via CPPFLAGS, which the .c.o suffix rule already consumes.
  - `lex` does not exist on this host (only `flex`), so YACC/LEX are passed
    explicitly and pinned through tool_requires so CI has them too.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class DmaConan(ConanFile):
    name = "dma"
    version = "0.14"
    description = "DragonFly Mail Agent — 极简 MTA（本地投递 + SSL relay 的 sendmail 替代）"
    license = "BSD-3-Clause"
    homepage = "https://github.com/corecode/dma"
    url = "https://github.com/corecode/dma"
    topics = ("mta", "mail", "sendmail", "smtp", "tls")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SSL relay support (Makefile:18 LDADD links -lssl -lcrypto).
        # 1.1.1w matches crypto.c:126 `#if (OPENSSL_VERSION_NUMBER >= 0x10100000L)`
        # which selects TLS_client_method(), and matches the version the
        # sibling sendmail emulators in this archive use (ssmtp 2.64 requires
        # openssl/1.1.1w as well).
        self.requires("openssl/1.1.1w")

    def build_requirements(self):
        # aliases_parse.y / aliases_scan.l are generated during `make` and are
        # not shipped in the GitHub tag archive; pin the tools so CI has them.
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dma supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def _have_bsd_progname(self, cc):
        """Build-time capability probe (R8 / PF5 compliant).

        The patch on dfcompat.c keys its non-glibc branch on the neutral
        capability macro HAVE_BSD_PROGNAME instead of any platform macro, so
        `patches/` stays free of platform macros entirely and the recipe
        decides the macro by *linking* the BSD-style `__progname` symbol the
        same way the Makefile's HAVE_* convention (Makefile:1-9) is meant to
        be used.

        Returns the flag to append to CPPFLAGS ("" when the symbol is absent,
        in which case the build falls through to the upstream `#error`, i.e.
        non-probing platforms keep upstream behaviour exactly).
        """
        src = os.path.join(self.build_folder, "_probe_bsd_progname.c")
        out = os.path.join(self.build_folder, "_probe_bsd_progname.bin")
        save(
            self,
            src,
            "extern char *__progname;\n"
            "int main(void) { return (__progname == 0); }\n",
        )
        # ignore_errors: a failed probe is a *result* (symbol missing), not a
        # build failure; the fall-through is the upstream #error path.
        rc = self.run(f'{cc} -o "{out}" "{src}"', ignore_errors=True)
        found = rc == 0
        self.output.info(
            "build-time probe __progname: {} (cc rc={})".format(
                "found -> -DHAVE_BSD_PROGNAME" if found else "missing -> no define", rc
            )
        )
        return " -DHAVE_BSD_PROGNAME" if found else ""

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()

        # OpenSSL include/lib injection (aggregated_components() yields
        # absolute paths in conan 2).
        info = self.dependencies["openssl"].cpp_info.aggregated_components()
        includes = " ".join(f"-I{d}" for d in info.includedirs)
        ld_paths = " ".join(f"-L{d}" for d in info.libdirs)
        libs = " ".join(f"-l{l}" for l in info.libs)

        # CPPFLAGS (not CFLAGS) carries the capability macro: the Makefile
        # appends -DDMA_VERSION/-DLIBEXEC_PATH/-DCONF_PATH to CFLAGS itself
        # (Makefile:17), and its .c.o rule (Makefile:95-96) consumes both
        # CFLAGS and CPPFLAGS, so nothing upstream is overwritten.
        cppflags = f"{includes}{self._have_bsd_progname(cc)}"

        # LDADD is overridden on the command line to drop `-lresolv` (musl
        # bundles the resolver); CFLAGS is left alone so the Makefile keeps
        # its own -DDMA_VERSION/-DLIBEXEC_PATH/-DCONF_PATH.
        # R9: -j1 (also avoids the HMDFS jobserver mkfifo restriction).
        self.run(
            f'make CC="{cc}" YACC=bison LEX=flex '
            f'CPPFLAGS="{cppflags}" LDFLAGS="{ld_paths}" LDADD="{libs}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        libexecdir = os.path.join(self.package_folder, "lib")
        mandir = os.path.join(self.package_folder, "share", "man", "man8")
        confdir = os.path.join(self.package_folder, "etc", "dma")

        # `make install` is not used — see the module docstring for the four
        # measured walls. Hand-install instead (checklist Makefile §3).
        copy(self, "dma", src=self.source_folder, dst=bindir, keep_path=False)
        copy(self, "dma-mbox-create", src=self.source_folder, dst=libexecdir, keep_path=False)
        copy(self, "dma.8", src=self.source_folder, dst=mandir, keep_path=False)
        copy(self, "dma.conf", src=self.source_folder, dst=confdir, keep_path=False)
        copy(self, "auth.conf", src=self.source_folder, dst=confdir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        for rel in ("bin/dma", "lib/dma-mbox-create"):
            path = os.path.join(self.package_folder, rel)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables. The hnp tools resolve
        # libc++ via their own location, so LD_LIBRARY_PATH must be dropped
        # (otherwise binary-sign-tool fails with "Error relocating ...").
        # Method taken from archives/c/connect-proxy/1.105/conanfile.py.
        if self.settings.os != "OHOS":
            return
        targets = (
            glob.glob(os.path.join(self.package_folder, "bin", "*"))
            + glob.glob(os.path.join(self.package_folder, "lib", "*"))
        )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            # `--remove-section .codesign || true` is intentional: llvm-objcopy
            # exits non-zero when the ELF has no .codesign section (the common
            # case — this is a pre-sign cleanup meant to be idempotent), and a
            # missing section must not abort the signing loop. The signature
            # itself is NOT best-effort: the following binary-sign-tool call has
            # no `|| true` and its failure does fail the build.
            self.run(
                'env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                .format(oc=objcopy, f=f)
            )
            self.run(
                'env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                .format(sg=signer, f=f)
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dma")
        # dma is a pure CLI/MTA: it ships no library and no headers.
        self.cpp_info.bindirs = ["bin", "lib"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

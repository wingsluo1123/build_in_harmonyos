#!/usr/bin/env python3
"""Conan recipe — sispmctl 4.12 (Autotools + libtool, command-line tool).

Controls GEMBIRD (m)SiS-PM USB power switches; ships the `sispmctl` CLI
tool together with `libsispmctl`. Built with the pre-generated `configure`
shipped in the upstream release tarball. OHOS adaptation is done in
generate()/build() following the repo's verified autotools OHOS pattern
(aibb24/aribb24): config.guess/config.sub HarmonyOS support, configure run
through the HMFS-safe /bin/sh (NOT the OHOS system bash, which fails getcwd
on HMFS — E386), and a pkg-config shim for the libusb-0.1 API dependency.

Dependency: libusb-compat/0.1.7 (provides the libusb-0.1 `usb.h` + `-lusb`
API that sispmctl's configure.ac `PKG_CHECK_MODULES(LIBUSB, libusb>=0.1.11)`
requires).
"""

import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SispmctlConan(ConanFile):
    name = "sispmctl"
    version = "4.12"
    description = "Control GEMBIRD (m)SiS-PM USB power switches"
    license = "GPL-2.0-or-later"
    homepage = "https://sispmctl.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libusb-compat provides the legacy libusb-0.1 API (usb.h / -lusb)
        # that sispmctl's configure.ac (PKG_CHECK_MODULES libusb>=0.1.11) uses.
        self.requires("libusb-compat/0.1.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # libusb-compat installs a libusb.pc reporting Version 0.1.7, which
        # does NOT satisfy sispmctl's "libusb >= 0.1.11" pkg-config gate.
        # Author a shim reporting the upstream libusb-0.1 API version 0.1.12
        # (matching libusb-compat's own LIBUSB01_VERSION), and pull in both the
        # libusb-compat and underlying libusb-1.0 link dirs so the static
        # transitive chain resolves for the final sispmctl binary.
        libusb1 = self.dependencies["libusb-compat"]
        libusb10 = libusb1.dependencies["libusb"]
        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        compat_lib = os.path.join(libusb1.package_folder, "lib")
        compat_inc = os.path.join(libusb1.package_folder, "include")
        usb10_lib = os.path.join(libusb10.package_folder, "lib")
        usb10_inc = os.path.join(libusb10.package_folder, "include")
        pc = (
            "prefix={prefix}\n"
            "exec_prefix=${{prefix}}\n"
            "libdir={compat_lib}\n"
            "includedir={compat_inc}\n"
            "\n"
            "Name: libusb\n"
            "Description: USB access library (libusb-0.1 API via libusb-compat)\n"
            "Version: 0.1.12\n"
            "Libs: -L{compat_lib} -lusb -L{usb10_lib} -lusb-1.0\n"
            "Libs.private: -L{usb10_lib} -lusb-1.0\n"
            "Cflags: -I{compat_inc} -I{usb10_inc}\n"
        ).format(prefix=libusb1.package_folder, compat_lib=compat_lib,
                 compat_inc=compat_inc, usb10_lib=usb10_lib,
                 usb10_inc=usb10_inc)
        with open(os.path.join(pc_dir, "libusb.pc"), "w", encoding="utf-8") as f:
            f.write(pc)

        env = tc.environment()
        env.append_path("PKG_CONFIG_PATH", pc_dir)
        env.append_path("PKG_CONFIG_PATH", compat_lib + "/pkgconfig")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_for_ohos()

        # E386: the OHOS system bash (/data/service/hnp/bin/bash, injected by
        # the profile [buildenv] as CONFIG_SHELL/SHELL during self.run) cannot
        # getcwd() on the HMFS working directory, so configure dies with
        # "working directory cannot be determined" plus a getcwd storm. The
        # HMFS-safe shell is /bin/sh (HMBS-injected SHELL=/bin/sh). We inline
        # `env -u CONFIG_SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh` at the
        # front of every self.run() command so it overrides whatever
        # conanbuild.sh re-exports from the profile buildenv at run time
        # (classads/hamlib/remctl precedent).
        #
        # ac_cv_func_malloc_0_nonnull=yes: configure.ac calls AC_FUNC_MALLOC,
        # whose generated check turns `no` on HarmonyOS (the `case "$host_os"`
        # "guess yes" list covers *-gnu*/BSD/Solaris etc., not linux-ohos, and
        # the cross/runtime conftest cannot verify malloc(0) on OHOS).  When
        # `no`, config.h gets `#define malloc rpl_malloc` plus nonexistent
        # malloc.o appended to LIBOBJS, so src/main.c fails to compile with
        # "incompatible integer to pointer conversion assigning to 'char *'
        # from 'int'" at `usbdevsn[i] = malloc(5);`.  Pinning the autoconf
        # cache variable `yes` (documented override mechanism) sets
        # HAVE_MALLOC, emits no rpl_malloc, and avoids the bogus LIBOBJS entry.
        # OHOS's libc malloc(0) returns a valid non-NULL pointer like any
        # modern libc, so the override is correct.
        prefix = ("env -u CONFIG_SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh "
                  "ac_cv_func_malloc_0_nonnull=yes")
        configure = os.path.join(self.source_folder, "configure")
        srcdir = self.source_folder

        # HMBS platform diagnostic [unsafe_local_mktemp]: on the real-machine
        # (HMFS/HMDFS) filesystem, config.status's AS_TMPDIR
        # ``(umask 077 && mktemp -d "./confXXXXXX")`` creates the temp dir with
        # drwx--S--- (group/other unwritable) and the build process cannot write
        # subs1.awk into it, aborting with "could not setup config files
        # machinery" (observed several times, e.g. "./confLJkGEp/subs1.awk:
        # Permission denied").  configure generates config.status from a quoted
        # heredoc at the end and runs it in the same process, so any post-hoc
        # config.status rewrite is too late — the fix must be baked into the
        # configure text BEFORE configure runs.
        # Round-1 (umask 077->022) and round-2 (mkdir rewrite) both gated the
        # patch on the HMBS_AUTOCONF_MKTEMP_FALLBACK env var, which is NOT
        # reaching this recipe process — the failing temp dirs were still named
        # `confXXXXXX` (6 random chars, mktemp-style), proving the mktemp branch
        # kept running and the patch never applied.  We therefore apply the
        # rewrite UNCONDITIONALLY for this HarmonyOS target (the recipe's only
        # build target, where the HMFS problem exists): replace the AS_TMPDIR
        # block so the temp dir is created with `mkdir` (not mktemp) under a
        # relaxed umask 022.  mkdir on this filesystem yields a writable temp
        # dir (cpdb-libs/inn evidence; mktemp's explicit chmod 0700 is what
        # produces the unwritable drwx--S---).  Idempotent: already-rewritten
        # configure returns without change.
        self._patch_configure_tmpdir_bypass_mktemp(configure)

        # Fix configure shebang for HarmonyOS (E165 pattern): make it robust.
        with open(configure, "r", errors="replace") as f:
            content = f.read()
        if "#!/bin/sh" in content[:20]:
            content = content.replace("#!/bin/sh", "#!/system/bin/sh", 1)
            with open(configure, "w") as f:
                f.write(content)

        # Pre-create libtool build subdirs
        for d in ["src/.libs", "src/.deps", ".libs"]:
            os.makedirs(os.path.join(srcdir, d), exist_ok=True)

        # In-tree build from the source folder (simplest, avoids libtool
        # VPATH/srcdir edge cases on OHOS). Self.run() applies the conanbuild
        # env (CC, CFLAGS, PKG_CONFIG_PATH with the libusb shim) from
        # generate(). configure runs ./config.status itself at its end; the
        # temp-dir fix must therefore already be baked into configure (above).
        self.run(
            f'{prefix} /bin/sh "./configure" --prefix=/ '
            f'"--bindir=${{prefix}}/bin" "--sbindir=${{prefix}}/bin" '
            f'"--libdir=${{prefix}}/lib" '
            f'"--includedir=${{prefix}}/include" '
            f'"--oldincludedir=${{prefix}}/include"',
            cwd=srcdir,
        )

        self.run(f"{prefix} make -j1 V=1", cwd=srcdir)

    def _patch_configure_tmpdir_bypass_mktemp(self, configure):
        """Rewrite the AS_TMPDIR block in the packaged `configure` to bypass
        `mktemp` and create the temp dir with `mkdir` under umask 022.

        config.status generated by configure runs
        ``(umask 077 && mktemp -d "./confXXXXXX")`` to create its temp dir (the
        AS_TMPDIR pattern).  On the OHOS real-machine (HMFS/HMDFS) filesystem,
        `mktemp -d` produces an unwritable drwx--S--- dir (its explicit chmod
        0700 doesn't survive the setgid/uid-mapping semantics), so configure
        aborts writing subs1.awk into it ("could not setup config files
        machinery").  mkdir (which relies on umask, not an explicit chmod)
        yields a writable temp dir here (cpdb-libs/inn evidence).  We rewrite
        the AS_TMPDIR block (emitted verbatim into config.status via the quoted
        _ACEOF heredoc) to create the temp dir directly with
        `(umask 022 && mkdir "$tmp")`, i.e. Autoconf's own mkdir fallback,
        independent of any mktemp implementation and of the (not-always-
        exported) HMBS_AUTOCONF_MKTEMP_FALLBACK env var.  Applied
        unconditionally for this HarmonyOS-only target; idempotent — an already
        rewritten configure returns without modification.  Stdin/program flow
        after the block (ac_tmp, CONFIG_FILES) is unchanged.
        """
        old_block = (
            "{\n"
            '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"\n'
            "}  ||\n"
            "{\n"
            "  tmp=./conf$$-$RANDOM\n"
            '  (umask 077 && mkdir "$tmp")\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." '
            '"$LINENO" 5'
        )
        new_block = (
            "{\n"
            "  tmp=./conf$$-$RANDOM\n"
            '  (umask 022 && mkdir "$tmp")\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." '
            '"$LINENO" 5'
        )
        with open(configure, "r", errors="replace") as f:
            content = f.read()
        if old_block not in content:
            return False
        new_content = content.replace(old_block, new_block, 1)
        if new_content == content:
            return False
        with open(configure, "w") as f:
            f.write(new_content)
        return True

    def _patch_config_for_ohos(self):
        """Patch config.guess/config.sub to recognize HarmonyOS (E007)."""
        src = self.source_folder
        for d in [src, os.path.join(src, "admin")]:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                self._patch_config_guess(cg)
                self._patch_config_sub(cs)
                return

    def _patch_config_guess(self, cg_path):
        with open(cg_path, "r", errors="replace") as f:
            content = f.read()
        changed = False
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android"
                   "\n#elif defined(__OHOS__)\n    LIBC=ohos")
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _patch_config_sub(self, cs_path):
        with open(cs_path, "r", errors="replace") as f:
            content = f.read()
        changed = False
        if "ohos-linux" not in content:
            pattern = (r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown'
                       r'\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)')
            replacement = (r'\1\tohos-linux)\n'
                           r'\tbasic_machine=$field1-unknown\n'
                           r'\tbasic_os=linux-ohos\n\t;;\n')
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
        if "ohos*" not in content:
            content = content.replace("gnu* | android*",
                                      "gnu* | android* | ohos*", 1)
            changed = True
        if "linux-ohos*)" not in content:
            # NOTE: guard must be "linux-ohos*)" not "linux-ohos" — the
            # ohos-linux case inserted above already contains the literal
            # "linux-ohos" (basic_os=linux-ohos), which would make a bare
            # "not in content" guard skip this kernel-os combo insertion.
            # Anchor on "| linux-uclibc* )" (leading "| "). A bare
            # "linux-uclibc" regex would ALSO match inside "uclinux-uclibc* )"
            # (third kernel-combo clause), corrupting config.sub into a shell
            # syntax error / failing the linux-ohos kernel-os validation.
            old_combo = "| linux-uclibc* )"
            if old_combo in content:
                content = content.replace(old_combo,
                                          "| linux-uclibc* | linux-ohos*)", 1)
                changed = True
        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        # make install DESTDIR=package_folder; --prefix=/ so DESTDIR prefixing.
        # E386: keep CONFIG_SHELL=/bin/sh so make's recursive shells do not use
        # the OHOS system bash that fails getcwd on HMFS.
        #
        # 'INSTALL_DATA=cp -f': the automake data rules (src/Makefile's
        # install-pkgdata{1,2,3}DATA and man/Makefile's install-man) expand
        # $(INSTALL_DATA) to `install -c -m 644 <file...> <destdir>`.  On the
        # OHOS real machine HMBS injects an install shim (capabilities
        # install_shim=true, chmod=0) in front of PATH because `install` would
        # chmod on HMFS (E046 chmod is a no-op).  That shim errors with exit 64
        # (EX_USAGE) on the multi-source-to-directory form — the single-file
        # libtool install-exec (binary/libs) succeeded, but the 13-file skin
        # `install -c -m 644 web1/... web1/style.css destdir` aborts with
        # "make[2]: *** [Makefile:572: install-pkgdata1DATA] Error 64".  These
        # are pure file copies (HTML/CSS/PNG + the man page) whose modes HMFS
        # normalizes anyway, so use `cp -f` as INSTALL_DATA: it does a plain
        # copy without the install shim and correctly handles multiple sources
        # into a destination directory.  `install-exec` (libtool) is untouched.
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh "
            "make install 'INSTALL_DATA=cp -f' "
            "DESTDIR={}".format(self.package_folder),
            cwd=self.source_folder, env="conanbuild")
        # Upstream Makefile.am declares no include_HEADERS, so the public API
        # header (sispm_ctl.h, which includes <usb.h> from libusb-compat) is
        # not installed; make it available for downstream consumers/tests.
        copy(self, "sispm_ctl.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # Upstream installs no public header (no include_HEADERS), so
        # package() copies src/sispm_ctl.h into <package>/include.  Export
        # that include dir explicitly so CMakeDeps-generated
        # sispmctl::sispmctl carries -I<package>/include for test_package /
        # downstream consumers (Relies on-conan-2-default would otherwise be
        # implicit; being explicit matches the repo's aribb24/remctl pattern
        # and guarantees #include <sispm_ctl.h> resolves).
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["sispmctl"]
        self.cpp_info.bindirs = ["bin"]

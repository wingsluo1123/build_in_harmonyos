#!/usr/bin/env python3
"""Conan recipe for Berkeley DB 18.1.40.

Berkeley DB uses autotools but requires running configure from the
build_unix/ subdirectory: cd build_unix && ../dist/configure --prefix=...
The source tarball contains a src/ directory with the actual source code.

R26: Not a system-name library, so shared builds are fine.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import re


class BerkeleyDbConan(ConanFile):
    name = "berkeley-db"
    version = "18.1.40"
    description = "Berkeley DB 18.1.40 — embedded key/value database library"
    license = "Sleepycat"  # Berkeley DB Sleepycat Public License
    homepage = "https://www.oracle.com/database/technologies/related/berkeleydb.html"
    url = "https://github.com/berkeleydb/berkeley-db"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # shared 选项语义（消费点见 generate() 与 build() 的 configure_cmd）：
    #   shared=True（默认）→ --enable-static --enable-shared，交付双库
    #   shared=False       → --enable-static --disable-shared，仅静态库
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Berkeley DB needs to run configure from build_unix/, not from source root.
        # The autotools.configure() helper runs ./configure at source root, which
        # doesn't work for this project. We pass args via configure_args for
        # consistency, then run configure manually in build().
        tc.configure_args.append("--enable-static")
        tc.configure_args.append(
            "--enable-shared" if self.options.shared else "--disable-shared"
        )
        tc.configure_args.append("--with-repmgr-ssl=no")
        if self.settings.os == "OHOS":
            # dist/config.guess (2017-08-08) cannot name the OHOS target triple;
            # pass explicit build/host so configure never tries to guess it.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        build_dir = os.path.join(src_dir, "build_unix")
        os.makedirs(build_dir, exist_ok=True)

        # Pre-patch dist/configure BEFORE running it. Two HMDFS issues force us
        # to intercept configure BEFORE it runs:
        #
        # (A) configure probes `print -r --` as an echo mechanism. On HMDFS the
        #     probe succeeds (ksh-style `print` builtin exists in the probe shell),
        #     but config.status later runs in a context where `print` is unavailable
        #     → "print: command not found" spam and failure.
        #     Fix: rewrite configure so it never picks `print -r --`, forcing the
        #     POSIX `printf %s\n` fallback for both as_echo and ECHO.
        #
        # (B) configure's LAST step is `$SHELL $CONFIG_STATUS ...` — it execs the
        #     freshly-written config.status immediately. config.status creates temp
        #     awk scripts in ./confXXXX/ then executes them directly (`./subs1.awk`),
        #     but HMDFS denies execute permission on newly-created scripts and also
        #     blocks writes under umask 077 + setgid. We need to patch config.status
        #     BEFORE it runs, so we neuter the auto-exec in configure and re-run
        #     config.status ourselves after patching it below.
        configure = os.path.join(src_dir, "dist", "configure")
        if os.path.isfile(configure):
            with open(configure) as f:
                cfg = f.read()
            # (A) Force printf fallback — drop every `print -r --` probe branch.
            cfg = cfg.replace("as_echo='print -r --'", "as_echo='printf %s\\n'")
            cfg = cfg.replace("as_echo_n='print -rn --'", "as_echo_n='printf %s'")
            cfg = cfg.replace("ECHO='print -r --'", "ECHO='printf %s\\n'")
            cfg = cfg.replace("print -r --", "printf %s\\n")
            cfg = cfg.replace("print -rn --", "printf %s")
            # (B) Stop configure from auto-execing config.status. We re-run it
            #     manually after patching. The auto-exec line looks like:
            #       $SHELL $CONFIG_STATUS $ac_config_status_args || ac_cs_success=false
            #     Replace it with a no-op so configure exits cleanly first.
            cfg = re.sub(
                r'\$SHELL \$CONFIG_STATUS \$ac_config_status_args \|\| '
                r'ac_cs_success=false',
                ': # config.status deferred (HMDFS patch pending)',
                cfg,
            )
            with open(configure, "w") as f:
                f.write(cfg)

        # Configure from build_unix/ using ../dist/configure
        # Conan's AutotoolsToolchain sets --prefix=/ for library packages,
        # and DESTDIR handles the actual install path.
        shared_flags = (
            "--enable-static --enable-shared"
            if self.options.shared
            else "--enable-static --disable-shared"
        )
        configure_cmd = (
            # OHOS has no binfmt_script: execve() of a #! script fails with
            # EACCES/126 regardless of its mode bits (verified: -rwxrwx---
            # and after chmod +x). Run every shell script through an explicit
            # interpreter prefix.
            # Also export SHELL=sh: configure internally execs
            # `$SHELL "$ac_aux_dir/config.sub"` etc., and $SHELL must never
            # be empty (empty → bare path → direct execve → 126).
            "cd {build_dir} && SHELL=sh sh ../dist/configure "
            "--prefix=/ "
            "{shared_flags} --with-repmgr-ssl=no"
        ).format(build_dir=build_dir, shared_flags=shared_flags)
        if self.settings.os == "OHOS":
            # OHOS toolchain triple is unknown to the bundled config.guess;
            # give configure explicit build/host so it skips guessing.
            configure_cmd += " --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        self.run(configure_cmd, env="conanbuild")

        # Patch config.status for HMDFS temp dir perms, THEN run it manually
        # (configure's auto-exec was neutered above).
        # Root cause of "can't create ./confXXXXXX/subs1.awk: Permission denied":
        # config.status creates its temp dir via `mktemp -d` (mode 0700 fixed,
        # umask does not apply), and HMDFS denies creating files inside the
        # resulting 0700/setgid dir. Fix: replace the mktemp branch with an
        # explicit umask-022 mkdir under $TMPDIR (device /tmp is read-only, so
        # fall back to $PWD — the build dir — which is always writable).
        # NOTE: do NOT rewrite awk script invocation to `awk -f` — every
        # `subs*.awk` occurrence in config.status is a redirection target
        # (">", ">>", "<"), not a direct execution. Patching those breaks
        # filenames. Once temp dir is writable, awk scripts run fine.
        config_status = os.path.join(build_dir, "config.status")
        if os.path.isfile(config_status):
            with open(config_status) as f:
                content = f.read()
            # Use regex — literal replace fails because of nested backticks
            # in the real config.status text. The replacement creates the dir
            # itself, so the `test -d "$tmp"` right after passes and the
            # umask-077 fallback branch is never reached.
            content = re.sub(
                r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null` &&',
                'tmp="${TMPDIR:-$PWD}"/conf$$-$RANDOM && (umask 022 && mkdir -p "$tmp") &&',
                content,
            )
            # Fallback branch (same block): normalize to the same scheme.
            content = re.sub(
                r'tmp=\./conf\$\$-\$RANDOM\n  \(umask 077 && mkdir "\$tmp"\)',
                'tmp="${TMPDIR:-$PWD}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
                content,
            )
            # Fallback: any remaining `umask 077 && mkdir "$tmp"` → umask 022
            content = re.sub(
                r'umask 077 && mkdir "\$tmp"',
                'umask 022 && mkdir -p "$tmp"',
                content,
            )
            # The generated Makefile runs `$(LIBTOOL)` = `./libtool`, a #! script;
            # make execve()s it directly → EACCES 126 on OHOS (no binfmt_script).
            # Prefix the substitution value so every expansion becomes `sh ./libtool`.
            content = content.replace(
                'S["LIBTOOL"]="./libtool"', 'S["LIBTOOL"]="sh ./libtool"'
            )
            # Defensive: if configure still emitted `print -r --`, swap it.
            content = content.replace("print -r --", "printf %s\\n")
            content = content.replace("print -rn --", "printf %s")
            with open(config_status, "w") as f:
                f.write(content)

            # Now manually run the patched config.status. Use an explicit `sh`
            # prefix: $SHELL may be empty in the conanbuild env (empty expands
            # to a bare ./config.status → direct execve → EACCES 126), and
            # OHOS has no binfmt_script anyway.
            self.run(f"cd {build_dir} && sh ./config.status", env="conanbuild")

            # Belt-and-braces Makefile fixes for make recipes:
            #  - LIBTOOL: never exec ./libtool directly (no binfmt_script on
            #    OHOS → EACCES 126). No-op when the S["LIBTOOL"] patch applied.
            #  - $(LN) -s: symlink(2) is EPERM device-wide (HMDFS) — BDB's
            #    `$(LN) -s src dst` convenience links become plain copies
            #    (verified: `ln -s .libs/libdb-18.1.a libdb.a` → Permission
            #    denied; 23 sites in the Makefile).
            makefile = os.path.join(build_dir, "Makefile")
            if os.path.isfile(makefile):
                with open(makefile) as f:
                    mk = f.read()
                mk_fixed = re.sub(
                    r'^(LIBTOOL=)(\s*)\./libtool',
                    r'\1\2sh ./libtool',
                    mk,
                    flags=re.M,
                )
                mk_fixed = mk_fixed.replace("$(LN) -s ", "cp -f ")
                #  - install-time llvm-strip drops the .codesign section the
                #    OHOS toolchain adds at link → installed tools get EACCES
                #    126 ("Permission denied") when executed. Disable it
                #    (verified: 27008B signed → 10104B unsigned without this).
                mk_fixed = mk_fixed.replace(
                    "$(STRIP) $(DESTDIR)$(bindir)/$$e;",
                    ": # strip disabled (drops .codesign);",
                )
                #  - DOCLIST: two docs entries are symlinks in the upstream
                #    tarball; HMDFS cannot materialize symlinks so extraction
                #    skips them and `cp -pr $(DOCLIST)` errors. Drop them.
                mk_fixed = mk_fixed.replace("bdb-sql ", "")
                mk_fixed = mk_fixed.replace("gsg_db_server ", "")
                if mk_fixed != mk:
                    with open(makefile, "w") as f:
                        f.write(mk_fixed)

        self.run(f"cd {build_dir} && make -j1", env="conanbuild")
        self.run(
            f"cd {build_dir} && make install DESTDIR={self.package_folder}",
            env="conanbuild"
        )

    def package(self):
        # build() already handles install via DESTDIR
        pass

    def package_info(self):
        self.cpp_info.libs = ["db-18.1"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 包同时交付 15 个 db_* 命令行工具（bin/），显式声明 bindirs 与安装目录一致
        # （R38：工具类型包必须可通过 commands.json 发现，L0k 依据 cpp_info.bindirs 判断）
        self.cpp_info.bindirs = ["bin"]

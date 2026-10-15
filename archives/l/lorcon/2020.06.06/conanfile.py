#!/usr/bin/env python3
"""Conan recipe for lorcon 2020.06.06 (Autotools).

LORCON (Loss Of Radio CONtrol) is a generic library for injecting
802.11 frames. Upstream tag 2020.06.06 builds a libtool library
liborcon2 plus packet forge / packasm helpers.

OHOS note (5th strategy cycle): lorcon hard-requires libpcap at
configure time (AC_CHECK_LIB(pcap) is a hard error), but libpcap
cannot be consumed as a Conan requirement on the preflight worker:
every libpcap version the team could require (1.10.6 published,
1.10.1 built) is also hosted on conancenter under one `all` recipe
whose build_requirements() unconditionally tool_requires bison/3.8.2
+ flex/2.6.4, and the preflight dual-remote resolution keeps selecting
the conancenter recipe. Its bison pulls conancenter m4/1.4.19, whose
configure dies on the profile SHELL (/data/service/hnp/bin/bash is
inaccessible in the container) -- a recipe this package cannot patch.
Pinning to another shared version was falsified in round 2 for the
same reason, and there is no ohpcd-only libpcap version to pin to
(the multimail/0.52 trick does not apply here).

This recipe therefore builds the official libpcap 1.10.6 sources
privately (same URL/SHA as published archives/l/libpcap/1.10.6, zero
committed patches) with an Autotools configure + static install into
a private prefix, links lorcon against it, and bundles libpcap.a plus
the pcap headers inside this package. No Conan-level libpcap
requirement exists, so neither preflight nor CI can enter the
conancenter bison/flex/m4 chain.

Generator problem and replay shims: the libpcap 1.10.6 archive ships
only scanner.l / grammar.y.in (verified: no scanner.c/grammar.c in
the archive; both are git-ignored generated files), so configure
hard-errors without flex+bison (AC_PROG_LEX + capable-lex functional
test + AC_CHECK_PROGS(bison), and CMake find_program FATAL_ERROR).
The worker has neither. vendor/pcap_gen/ therefore commits the four
generator outputs produced offline by REAL flex 2.6.4 + GNU Bison
3.8.2 (winflexbison v2.5.25 -- the exact versions of the conancenter
flex/2.6.4 and bison/3.8.2 toolchain) from this exact tag's
scanner.l / grammar.y.in with upstream's own flags, and
vendor/tools/{lex,bison}_shim.py replay those bytes through the
LEX / YACC slots (BISON/BYACC/BISON_BYACC as aliases; invoked as
`python3 shim.py ...`, so no
executable bit is needed on the chmod-less worker fs). The final
libpcap.a is bit-equivalent to a native generator build; this is the
same bootstrapping that release tarballs with pre-generated files do.
"""

import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LorconConan(ConanFile):
    name = "lorcon"
    version = "2020.06.06"
    description = "Generic library for injecting 802.11 frames"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kismetwireless/lorcon"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        copy(self, "*.py", src=os.path.join(self.recipe_folder, "vendor"),
             dst=os.path.join(self.export_sources_folder, "vendor"))
        copy(self, "*.c", src=os.path.join(self.recipe_folder, "vendor"),
             dst=os.path.join(self.export_sources_folder, "vendor"))
        copy(self, "*.h", src=os.path.join(self.recipe_folder, "vendor"),
             dst=os.path.join(self.export_sources_folder, "vendor"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Deliberately empty: libpcap 1.10.6 is vendored privately in
        # build() (see module docstring). Any shared-version
        # requires("libpcap/...") resolves to the conancenter recipe
        # on the preflight worker and dies in its bison/flex/m4 chain.
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lorcon is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["lorcon"], strip_root=True)
        get(self, **self.conan_data["sources"]["libpcap"],
            strip_root=True, destination=self._pcap_src_folder)

    @property
    def _pcap_src_folder(self):
        # NOTE: Conan 2.x has no `base_source_folder` (Conan 1.x name);
        # the writable sources root in source()/build() is `source_folder`.
        return os.path.join(self.source_folder, "libpcap-src")

    @property
    def _pcap_build_folder(self):
        return os.path.join(self.build_folder, "libpcap-build")

    @property
    def _pcap_install_folder(self):
        return os.path.join(self.build_folder, "libpcap-install")

    @property
    def _pcap_flags_file(self):
        return os.path.join(self.build_folder, "libpcap-flags.env")

    def _save_pcap_flags(self, cflags, ldflags):
        # Persisted as VAR=VALUE lines; read back in build().
        lines = ["CFLAGS=%s" % " ".join(cflags),
                 "LDFLAGS=%s" % " ".join(ldflags)]
        try:
            os.makedirs(self.build_folder, exist_ok=True)
        except OSError:
            pass
        save(self, self._pcap_flags_file, "\n".join(lines) + "\n")
        self.output.info("lorcon: saved vendored-libpcap flags: %s"
                         % " | ".join(lines))

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/",
            "--disable-dependency-tracking",
        ])
        # Vendored libpcap headers/libs live in a private prefix known
        # already at generate time (fixed subdir of build_folder). The
        # same CFLAGS/LDFLAGS the toolchain computes for lorcon (OHOS
        # sysroot etc.) are persisted so the private libpcap configure
        # in build() uses byte-identical compilation flags.
        pcap_cflags = list(tc.cflags or [])
        pcap_cflags.append("-I%s" % os.path.join(
            self._pcap_install_folder, "include").replace("\\", "/"))
        pcap_ldflags = list(tc.ldflags or [])
        pcap_ldflags.append("-L%s" % os.path.join(
            self._pcap_install_folder, "lib").replace("\\", "/"))
        self._save_pcap_flags(pcap_cflags, pcap_ldflags)
        # lorcon's own configure needs the same private paths to find
        # pcap.h and -lpcap (AC_CHECK_LIB is a hard error upstream).
        tc.extra_cflags.append("-I%s" % os.path.join(
            self._pcap_install_folder, "include").replace("\\", "/"))
        tc.extra_ldflags.append("-L%s" % os.path.join(
            self._pcap_install_folder, "lib").replace("\\", "/"))
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        if str(self.settings.os) == "OHOS":
            # OHOS preflight profile sets CONFIG_SHELL/SHELL to
            # /data/service/hnp/bin/bash which may be inaccessible in the
            # isolated build container. Mirror the proven archives/m/m4/1.4.19
            # shell-selection logic: prefer an actually-executable shell
            # (HMBS injects SHELL=/bin/sh).
            env = tc.environment()
            shell = self._select_shell()
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._prepare_build_environment()
        self._build_vendored_libpcap()
        # The profile-declared absolute compiler (/data/service/hnp/bin/clang)
        # is not executable inside the preflight container (same failure class
        # as the bad profile SHELL; libnids/1.26 precedent). Probe for a
        # compiler that really runs and pin it via CC/CXX configure args.
        cc = self._probe_working_compiler("c")
        cxx = self._probe_working_compiler("cpp")
        self._fix_autoconf_umask_for_ohos(self.source_folder)
        self._patch_config_sub_for_aarch64(self.source_folder)
        self._relax_wireless_check_for_ohos(self.source_folder)
        self._fix_ifcontrol_includes_for_ohos(self.source_folder)
        self._fix_packasm_uchar_for_ohos(self.source_folder)
        self._fix_drv_tuntap_includes_for_ohos(self.source_folder)
        self._fix_bsd_string_aliases_for_ohos(self.source_folder)
        # OHOS shell scrub (same failure class as the vendored libpcap
        # configure): the profile buildenv CONFIG_SHELL/SHELL
        # (/data/service/hnp/bin/bash) is inaccessible inside the
        # preflight container, and the Autotools helper re-exports it via
        # conanbuild, so plain autotools.configure() dies at
        # configure[157] re-exec. Run configure under env(1) with a
        # probed-good shell (the exact mechanism that let the vendored
        # libpcap configure succeed in this same build) plus an explicit
        # SHELL= on the make command line.
        self._run_lorcon_configure_and_make(cc, cxx)

    def _run_lorcon_configure_and_make(self, cc, cxx):
        shell = self._select_shell()
        make = self._select_make()
        configure = os.path.join(self.source_folder, "configure")
        cmd = [shlex.quote(configure),
               "--prefix=/",
               "--bindir=${prefix}/bin",
               "--sbindir=${prefix}/bin",
               "--libdir=${prefix}/lib",
               "--includedir=${prefix}/include",
               "--oldincludedir=${prefix}/include",
               "--disable-dependency-tracking"]
        if str(self.settings.os) == "OHOS":
            cmd.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if not self.options.shared:
            cmd.append("--disable-shared")
            cmd.append("--enable-static")
        if cc:
            cmd.append("CC=%s" % shlex.quote(cc))
        if cxx:
            cmd.append("CXX=%s" % shlex.quote(cxx))
        env_prefix = "env %s %s" % (
            shlex.quote("CONFIG_SHELL=%s" % shell),
            shlex.quote("SHELL=%s" % shell),
        )
        self.output.info("lorcon: own configure shell=%s make=%s" % (shell, make))
        # lorcon ships a hand-written Makefile.in with no VPATH/ssrcdir
        # indirection: its .depend rule expands bare `*.c` names, so an
        # out-of-source configure (default build-folder cwd) generates a
        # Makefile whose `Generating dependencies...` step cannot find
        # any of the 15 sources (this round: all of ifcontrol_linux.c
        # ... lorcon_multi.c missing + `.depend: No such file`). Build
        # in-source (cwd=source_folder), where the objects belong.
        self.run("%s %s" % (env_prefix, " ".join(cmd)), cwd=self.source_folder,
                 env="conanbuild")
        self.run("%s SHELL=%s -j1" % (make, shlex.quote(shell)),
                 cwd=self.source_folder, env="conanbuild")

    def _build_vendored_libpcap(self):
        """Configure + build + install official libpcap privately.

        Uses only Autotools + the replay shims (no flex/bison, no
        conancenter). Mirrors the configure flags of the conancenter
        non-Windows recipe minus its tool_requires, with features
        auto-detect replaced by explicit off-switches for determinism.
        """
        pcap_src = self._pcap_src_folder
        pcap_build = self._pcap_build_folder
        pcap_prefix = self._pcap_install_folder
        for folder in (pcap_build, pcap_prefix):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                pass
        self._fix_autoconf_umask_for_ohos(pcap_src)
        self._patch_config_sub_for_aarch64(pcap_src)
        self._apply_pcap_linux_fix(pcap_src)
        shell = self._select_shell()
        cc = self._probe_working_compiler("c")
        python3 = self._select_python3()
        vendor = os.path.join(self.export_sources_folder, "vendor")
        lex = "%s %s" % (python3, os.path.join(vendor, "tools", "lex_shim.py"))
        yacc = "%s %s" % (python3, os.path.join(vendor, "tools", "bison_shim.py"))
        # libpcap configure resets BISON_BYACC="" before AC_CHECK_PROGS
        # (configure.ac, verified against the 1.10.6 tag), so no amount
        # of environment export can survive: patch the assignment in the
        # generated configure to our replay shim instead (build-time
        # edit, same class as the umask/wireless patches below).
        self._patch_pcap_bison_check(pcap_src, yacc)
        # Archiver tools for libtool: prefer LLVM ones from the HNP
        # toolchain dir when they really execute, else PATH defaults.
        ar = self._probe_tool(["llvm-ar", "ar"])
        ranlib = self._probe_tool(["llvm-ranlib", "ranlib"])
        self.output.info("lorcon: vendored libpcap shell=%s cc=%s python=%s"
                         % (shell, cc or "<toolchain default>", python3))
        self.output.info("lorcon: vendored libpcap LEX=%s" % lex)
        self.output.info("lorcon: vendored libpcap BISON_BYACC=%s" % yacc)
        # Sanity: the replay shims must answer before configure runs.
        self._check_generator_shim(lex, ["--version"], "flex")
        self._check_generator_shim(yacc, ["-V"], "bison")
        configure_cmd = [shlex.quote(os.path.join(pcap_src, "configure")),
                         "--prefix=%s" % shlex.quote(pcap_prefix),
                         "--disable-shared",
                         "--disable-dependency-tracking",
                         "--disable-dbus",
                         "--disable-rdma",
                         "--disable-bluetooth",
                         "--disable-usb",
                         "--with-snf=no",
                         "--without-dpdk",
                         "--without-libnl",
                         "--disable-universal",
                         "--disable-packet-ring"]
        if str(self.settings.os) == "OHOS":
            configure_cmd.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if cc:
            configure_cmd.append("CC=%s" % shlex.quote(cc))
        # Autoconf lex-library probe bypass (documented cache override,
        # not a skipped test): modern AC_PROG_LEX links its conftest
        # scanner -- which calls plain yywrap() -- against -lfl/-ll and
        # sets LEX=: when neither exists, and libpcap then hard-errors
        # with "Neither flex nor lex was found". The worker ships no
        # flex runtime libraries, but the real build genuinely needs
        # none: the committed flex-2.6.4 scanner is reentrant with
        # `#define yywrap pcap_wrap` (see vendor/pcap_gen/scanner.h),
        # so it never references libfl's yywrap, and make consumes the
        # replayed scanner.c/h directly (also seeded below). Hence
        # `none needed` is the factually correct LEXLIB value here.
        configure_cmd.append("ac_cv_lib_lex=%s" % shlex.quote("none needed"))
        # Same compilation flags the toolchain computed for lorcon
        # itself (OHOS sysroot etc.), persisted at generate() time, so
        # the private libpcap objects are built for the same target.
        # Fall back to the private include/lib paths when generate()
        # did not run (e.g. local `conan build` without generate).
        pcap_cflags, pcap_ldflags = self._load_pcap_flags()
        configure_cmd.append("CFLAGS=%s" % shlex.quote(pcap_cflags))
        configure_cmd.append("LDFLAGS=%s" % shlex.quote(pcap_ldflags))
        # Run under conanbuild (PATH/LD_LIBRARY_PATH for the HNP
        # toolchain) but scrub the profile's bad CONFIG_SHELL/SHELL via
        # env(1): conanbuild would otherwise re-inject the inaccessible
        # /data/service/hnp/bin/bash and configure would die re-execing
        # with it (the conancenter m4 failure mode). LEX goes through
        # the same prefix (AC_PROG_LEX honours an exported LEX, proven
        # by the passing lex-root probe); BISON_BYACC is deliberately
        # NOT exported here because configure overwrites it with
        # BISON_BYACC="" before AC_CHECK_PROGS (see
        # _patch_pcap_bison_check) -- the file patch above is the only
        # channel that survives.
        # NOTE: configure VAR=VAL command-line assignments below would
        # arrive too late for its startup shell re-exec, hence env(1).
        env_prefix = "env %s %s %s" % (
            shlex.quote("CONFIG_SHELL=%s" % shell),
            shlex.quote("SHELL=%s" % shell),
            shlex.quote("LEX=%s" % lex),
        )
        if ar:
            env_prefix += " %s" % shlex.quote("AR=%s" % ar)
        if ranlib:
            env_prefix += " %s" % shlex.quote("RANLIB=%s" % ranlib)
        self.run("%s %s" % (env_prefix, " ".join(configure_cmd)),
                 cwd=pcap_build, env="conanbuild")
        # Seed the build dir with the committed generator outputs so
        # make has nothing to regenerate; any regen replays identical
        # bytes through the shims (belt and suspenders).
        gen_dir = os.path.join(vendor, "pcap_gen")
        for fname in ("scanner.c", "scanner.h", "grammar.c", "grammar.h"):
            dst = os.path.join(pcap_build, fname)
            with open(os.path.join(gen_dir, fname), "rb") as src_handle:
                data = src_handle.read()
            with open(dst, "wb") as dst_handle:
                dst_handle.write(data)
            self.output.info("lorcon: seeded %s (%d bytes)" % (fname, len(data)))
        make = self._select_make()
        # SHELL override: configure substitutes SHELL from its
        # environment (conanbuild carries the profile's bad bash), so
        # pin a working shell on the make command line (wins over the
        # Makefile assignment).
        self.run("%s SHELL=%s -j1" % (make, shlex.quote(shell)),
                 cwd=pcap_build, env="conanbuild")
        self.run("%s SHELL=%s -j1 install" % (make, shlex.quote(shell)),
                 cwd=pcap_build, env="conanbuild")
        lib = os.path.join(pcap_prefix, "lib", "libpcap.a")
        if not os.path.isfile(lib):
            raise ConanInvalidConfiguration(
                "vendored libpcap did not produce %s" % lib)
        self.output.info("lorcon: vendored libpcap.a ready (%d bytes)"
                         % os.path.getsize(lib))

    def _load_pcap_flags(self):
        cflags = "-I%s" % os.path.join(
            self._pcap_install_folder, "include").replace("\\", "/")
        ldflags = "-L%s" % os.path.join(
            self._pcap_install_folder, "lib").replace("\\", "/")
        try:
            with open(self._pcap_flags_file, "r", encoding="utf-8",
                      errors="replace") as handle:
                for line in handle.read().splitlines():
                    if line.startswith("CFLAGS="):
                        cflags = line[len("CFLAGS="):]
                    elif line.startswith("LDFLAGS="):
                        ldflags = line[len("LDFLAGS="):]
        except OSError:
            self.output.warning("lorcon: no persisted libpcap flags, "
                                "using include/lib fallback")
        return cflags, ldflags

    def _check_generator_shim(self, command, args, label):
        try:
            result = subprocess.run(
                shlex.split(command) + args,
                capture_output=True, text=True, timeout=60,
            )
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "lorcon: %s replay shim failed to start: %s" % (label, exc))
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                "lorcon: %s replay shim probe failed (rc=%s): %s"
                % (label, result.returncode, (result.stderr or "")[-500:]))
        self.output.info("lorcon: %s shim probe ok: %s"
                         % (label, (result.stdout or "").splitlines()[0][:80]
                             if result.stdout else "<silent>"))

    def _select_python3(self):
        for candidate in (os.environ.get("HMBS_PYTHON3"),
                          shutil.which("python3"),
                          sys.executable):
            if candidate and os.path.isfile(candidate.split()[0]):
                return candidate.split()[0]
        return "python3"

    def _select_make(self):
        for candidate in (os.environ.get("HMBS_MAKE"),
                          self.conf.get("user.hmbs:make_path"),
                          shutil.which("make")):
            if candidate and isinstance(candidate, str) and os.path.isfile(candidate):
                return candidate
        return "make"

    def _probe_tool(self, candidates):
        for candidate in candidates:
            path = shutil.which(candidate)
            if not path:
                continue
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception:
                continue
            if result.returncode == 0:
                self.output.info("lorcon: tool probe usable: %s" % path)
                return path
        self.output.info("lorcon: tool probe found none of %s" % candidates)
        return ""

    def _probe_working_compiler(self, kind):
        # Mirror the archives/l/libnids/1.26 precedent: really exec
        # `<exe> --version` on the worker and keep the first candidate that
        # exits 0. Returns the executable path, or "" (caller then keeps the
        # toolchain default and the real error surfaces in config.log).
        candidates = []
        try:
            comp = self.conf.get("tools.build:compiler_executables")
            if isinstance(comp, dict) and comp.get(kind):
                candidates.append(comp[kind])
            elif isinstance(comp, str) and comp:
                candidates.append(comp)
        except Exception:
            pass
        env_key = "CC" if kind == "c" else "CXX"
        if os.environ.get(env_key):
            candidates.append(os.environ[env_key])
        candidates.append("/data/service/hnp/bin/%s"
                          % ("clang" if kind == "c" else "clang++"))
        for tool in (("clang", "cc", "gcc")
                     if kind == "c" else ("clang++", "c++", "g++")):
            try:
                found = shutil.which(tool)
            except Exception:
                found = None
            if found:
                candidates.append(found)
        seen = set()
        for cand in candidates:
            if not cand or not isinstance(cand, str):
                continue
            exe = cand.split()[0]
            if not exe or exe in seen:
                continue
            seen.add(exe)
            if "/" not in exe:
                resolved = shutil.which(exe)
                if not resolved:
                    self.output.info("CC probe: not found, skip: %s" % cand)
                    continue
                exe = resolved
            if not os.path.isfile(exe):
                self.output.info("CC probe: not a file, skip: %s" % cand)
                continue
            try:
                result = subprocess.run(
                    [exe, "--version"],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception as exc:
                self.output.info("CC probe: exec failed %s (%s)"
                                 % (cand, exc))
                continue
            if result.returncode == 0:
                self.output.info("CC probe: usable %s -> %s" % (kind, exe))
                return exe
            self.output.info("CC probe: %s --version rc=%s"
                             % (cand, result.returncode))
        self.output.warning("CC probe: no working %s compiler, "
                            "keeping toolchain default" % kind)
        return ""

    def _select_shell(self):
        # Hardened shell selection: the preflight container exposes
        # /data/service/hnp/bin/bash as a file with +x in the shared fs
        # view, but exec fails inside the isolated build namespace
        # (configure[157]: inaccessible or not found). isfile+X_OK alone
        # therefore falsely accepts it (this round: vendored libpcap
        # succeeded via env(1) scrub while lorcon's own configure baked
        # the bad profile shell). Really exec `shell -c true` and keep
        # the first that exits 0; HMBS SHELL=/bin/sh and /bin/sh stay
        # first, the profile absolute bash stays last.
        import subprocess as _sp
        for shell in (
            os.environ.get("SHELL"),
            os.environ.get("CONFIG_SHELL"),
            "/bin/sh",
            "/system/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if not shell:
                continue
            exe = shell.split()[0] if isinstance(shell, str) else ""
            if not exe:
                continue
            if "/" not in exe:
                resolved = shutil.which(exe)
                if not resolved:
                    continue
                exe = resolved
            if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
                continue
            try:
                probe = _sp.run([exe, "-c", "true"],
                                capture_output=True, timeout=15)
            except Exception:
                continue
            if probe.returncode == 0:
                if exe != shell:
                    self.output.info("lorcon: shell probe %s -> %s ok"
                                     % (shell, exe))
                    return exe
                return shell
            self.output.info("lorcon: shell probe %s rc=%s, skip"
                             % (shell, probe.returncode))
        return "sh"

    def _prepare_build_environment(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ.setdefault("TMP", tmpdir)
        os.environ.setdefault("TEMP", tmpdir)
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        self.output.info("lorcon: using shell %s tmpdir %s" % (shell, tmpdir))

    def package(self):
        # Manual staging instead of `make install` (zero `make install`
        # invocation): with compilation now green through all 15 objects,
        # the build dies in package() at `Makefile:67: install, Error 64`.
        # Upstream's install target is unusable on the OHOS worker for
        # three independent reasons, so flag tweaks (SHELL=, LDCONFIG=)
        # cannot converge -- a different strategy is required:
        # (1) it ends with `install -o root -m 644 lorcon.3`, which fails
        # as non-root and needs chown (in-repo precedent: libpri/1.6.0
        # passes LDCONFIG=true because OHOS has no ldconfig; same class
        # as the trailing `$(LDCONFIG)` here); (2) libtool
        # `--mode=install` re-chmods/relinks, hostile to the worker fs
        # (HMBS reports chmod:0/hardlink:0); (3) only `make install`
        # still shells out to the profile `${SHELL}`, re-exposing the
        # scrubbed bad bash. Manual staging with conan `copy()` (pure
        # python, no shell/install/libtool) replicates exactly what
        # `make install` would lay out: the libtool archive from .libs,
        # the five public headers + ieee80211.h renamed to
        # lorcon_ieee80211.h under include/lorcon2, and the man page.
        import glob as _glob
        libs_dir = os.path.join(self.source_folder, ".libs")
        pkg_lib = os.path.join(self.package_folder, "lib")
        try:
            os.makedirs(pkg_lib, exist_ok=True)
        except OSError:
            pass
        if self.options.shared:
            copy(self, "liborcon2.so*", libs_dir, pkg_lib)
            copy(self, "liborcon2.a", libs_dir, pkg_lib)
        else:
            lib = os.path.join(libs_dir, "liborcon2.a")
            if not os.path.isfile(lib):
                raise ConanInvalidConfiguration(
                    "lorcon: in-source build did not produce %s" % lib)
            copy(self, "liborcon2.a", libs_dir, pkg_lib)
        self.output.info("lorcon: staged liborcon2 from %s" % libs_dir)
        pkg_inc = os.path.join(self.package_folder, "include", "lorcon2")
        for header in ("lorcon.h", "lorcon_packet.h", "lorcon_packasm.h",
                       "lorcon_forge.h", "lorcon_multi.h"):
            copy(self, header, self.source_folder, pkg_inc)
        # Upstream renames ieee80211.h on install; replicate the rename.
        try:
            with open(os.path.join(self.source_folder, "ieee80211.h"),
                      "rb") as _src:
                _data = _src.read()
            try:
                os.makedirs(pkg_inc, exist_ok=True)
            except OSError:
                pass
            with open(os.path.join(pkg_inc, "lorcon_ieee80211.h"),
                      "wb") as _dst:
                _dst.write(_data)
        except OSError:
            self.output.warning("lorcon: ieee80211.h not staged")
        copy(self, "lorcon.3", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man3"))
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            try:
                os.remove(_la)
            except OSError:
                pass
        # Bundle the privately built libpcap (static archive + headers)
        # so consumers link without any Conan-level libpcap requirement.
        pcap_prefix = self._pcap_install_folder
        copy(self, "libpcap.a", os.path.join(pcap_prefix, "lib"),
             os.path.join(self.package_folder, "lib"))
        for header in ("pcap.h", "pcap-bpf.h", "pcap-namedb.h"):
            copy(self, header, os.path.join(pcap_prefix, "include"),
                 os.path.join(self.package_folder, "include"))
        copy(self, "*.h", os.path.join(pcap_prefix, "include", "pcap"),
             os.path.join(self.package_folder, "include", "pcap"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        if not self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            if os.path.isdir(libdir):
                for root, _dirs, files in os.walk(libdir):
                    for fname in files:
                        if fname.endswith(".so") or ".so." in fname:
                            try:
                                os.remove(os.path.join(root, fname))
                            except OSError:
                                pass

    def package_info(self):
        # libpcap.a is bundled in this package (see package()); consumers
        # link it directly, no transitive libpcap requirement exists.
        self.cpp_info.libs = ["orcon2", "pcap"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include", "include/lorcon2"]
        self.cpp_info.set_property("cmake_file_name", "lorcon")
        self.cpp_info.set_property("cmake_target_name", "lorcon::lorcon")
        self.cpp_info.set_property("pkg_config_name", "lorcon")

    def _fix_autoconf_umask_for_ohos(self, source_folder):
        configure = os.path.join(source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        content = content.replace("umask 077", "umask 022")
        with open(configure, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info("lorcon: rewrote umask 077 -> 022 for HMDFS")

    def _apply_pcap_linux_fix(self, pcap_src):
        # Mirror published archives/l/libpcap/1.10.6 patch
        # 0003-pcap-linux.c.patch at build time (zero committed patches):
        # prevent sockaddr_storage redefinition against the OHOS sysroot
        # linux/socket.h by including linux/if.h first under a guard.
        target = os.path.join(pcap_src, "pcap-linux.c")
        try:
            with open(target, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        old = ("#include <sys/socket.h>\n"
               "#include <sys/ioctl.h>\n"
               "#include <sys/utsname.h>\n"
               "#include <sys/mman.h>\n"
               "#include <linux/if.h>\n")
        new = ("#include <sys/socket.h>\n"
               "/* HarmonyOS fix: prevent sockaddr_storage redefinition in linux/socket.h */\n"
               "#define sockaddr_storage sockaddr_storage_linux\n"
               "#include <linux/if.h>\n"
               "#undef sockaddr_storage\n"
               "#include <sys/ioctl.h>\n"
               "#include <sys/utsname.h>\n"
               "#include <sys/mman.h>\n")
        if old not in content:
            self.output.warning("lorcon: pcap-linux.c include block not found, "
                                "skipping HarmonyOS sockaddr fix")
            return
        content = content.replace(old, new, 1)
        with open(target, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info("lorcon: applied pcap-linux.c sockaddr_storage guard")

    def _patch_pcap_bison_check(self, pcap_src, yacc_cmd):
        # libpcap 1.10.6 configure.ac hard-codes `BISON_BYACC=""` right
        # before `AC_CHECK_PROGS(BISON_BYACC, bison)` / `byacc yacc`,
        # so any BISON_BYACC/YACC environment export is discarded and
        # configure always searches PATH (worker has no bison/byacc/
        # yacc -> "Neither bison, byacc, nor yacc was found"). Preset
        # the variable to our replay shim in the generated configure
        # instead; the following `if test x"$BISON_BYACC" != x` then
        # takes the bison branch and parses `$BISON_BYACC -V` (our shim
        # reports GNU Bison 3.8.2, selecting %define api.pure -- the
        # same value the committed grammar.c was generated with).
        configure = os.path.join(pcap_src, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            raise ConanInvalidConfiguration(
                "lorcon: vendored libpcap configure not found for "
                "BISON_BYACC patch")
        marker = 'BISON_BYACC=""'
        if marker not in content:
            raise ConanInvalidConfiguration(
                "lorcon: BISON_BYACC reset line not found in vendored "
                "configure; cannot bypass bison PATH search")
        quoted = "'" + yacc_cmd.replace("'", "'\\''") + "'"
        content = content.replace(marker, "BISON_BYACC=%s" % quoted, 1)
        with open(configure, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info("lorcon: preset BISON_BYACC to replay shim")

    def _patch_config_sub_for_aarch64(self, source_folder):
        config_sub = os.path.join(source_folder, "config.sub")
        try:
            with open(config_sub, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "aarch64" in content:
            return
        patched = False
        bare = "| thumb | d10v | d30v | fr30 | avr)"
        if bare in content:
            content = content.replace(
                bare,
                "| thumb | d10v | d30v | fr30 | avr | aarch64 | aarch64be)",
                1,
            )
            patched = True
        company = "| bs2000-* | tic54x-* | c54x-* | x86_64-*)"
        if company in content:
            content = content.replace(
                company,
                "| bs2000-* | tic54x-* | c54x-* | x86_64-* | aarch64-* | aarch64be-*)",
                1,
            )
            patched = True
        if patched:
            with open(config_sub, "w", encoding="utf-8",
                       errors="surrogateescape") as handle:
                handle.write(content)
            self.output.info("lorcon: patched config.sub for aarch64")

    def _relax_wireless_check_for_ohos(self, source_folder):
        configure = os.path.join(source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        marker = "*** Missing working Linux wireless kernel extensions ***"
        if marker not in content:
            return
        old = (
            'as_fn_error $? "*** Missing working Linux wireless kernel extensions ***" '
            '"$LINENO" 5'
        )
        if old in content:
            content = content.replace(
                old,
                '{ $as_echo "$as_me:${as_lineno-$LINENO}: WARNING: '
                'linux/wireless.h not usable, building without wireless extensions" '
                '>&5; $as_echo "WARNING: linux/wireless.h not usable" >&2; }',
            )
            with open(configure, "w", encoding="utf-8",
                       errors="surrogateescape") as handle:
                handle.write(content)
            self.output.info("lorcon: relaxed linux/wireless.h check to warning")

    def _fix_ifcontrol_includes_for_ohos(self, source_folder):
        # Build-time include repair (zero committed patches): both
        # ifcontrol_linux.c and madwifing_control.c use struct ifreq /
        # IFNAMSIZ while relying on glibc transitive includes. Their
        # headers only provide struct ifreq via <linux/if.h> under
        # HAVE_LINUX_WIRELESS, which is undefined on OHOS (wireless
        # check relaxed above), so the OHOS sysroot leaves struct ifreq
        # incomplete (last round: 12 errors in ifcontrol_linux.c, fixed;
        # this round: 9 errors in madwifing_control.c at the next
        # object). Insert the direct POSIX/Linux headers; <net/if.h> is
        # guarded so a wireless-enabled (glibc) build keeps using
        # <linux/if.h> without a redefinition clash.
        target = os.path.join(source_folder, "ifcontrol_linux.c")
        try:
            with open(target, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            pass
        else:
            old = ("#include <sys/types.h>\n"
                   "#include <sys/stat.h>\n"
                   "#include <unistd.h>\n")
            new = ("#include <sys/types.h>\n"
                   "#include <sys/stat.h>\n"
                   "#include <unistd.h>\n"
                   "#include <stdio.h>\n"
                   "#include <string.h>\n"
                   "#include <strings.h>\n"
                   "#include <errno.h>\n"
                   "#include <sys/socket.h>\n"
                   "#include <sys/ioctl.h>\n"
                   "#include <netinet/in.h>\n"
                   "#ifndef HAVE_LINUX_WIRELESS\n"
                   "#include <net/if.h>\n"
                   "#endif\n")
            if old in content and "<net/if.h>" not in content:
                content = content.replace(old, new, 1)
                with open(target, "w", encoding="utf-8",
                           errors="surrogateescape") as handle:
                    handle.write(content)
                self.output.info("lorcon: added OHOS system headers to "
                                 "ifcontrol_linux.c")
            elif "<net/if.h>" not in content and old not in content:
                self.output.warning("lorcon: ifcontrol_linux.c include block not "
                                    "found, skipping OHOS include fix")
        # Second translation unit with the identical OHOS failure class:
        # madwifing_control.c already includes sys/socket + sys/ioctl +
        # string/errno, but on the OHOS sysroot struct ifreq/IFNAMSIZ
        # live only in <net/if.h> (glibc provides them transitively).
        mtarget = os.path.join(source_folder, "madwifing_control.c")
        try:
            with open(mtarget, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                mcontent = handle.read()
        except OSError:
            return
        if "<net/if.h>" in mcontent:
            return
        manchor = '#include "ifcontrol_linux.h"'
        minsert = (manchor + "\n"
                   "#ifndef HAVE_LINUX_WIRELESS\n"
                   "#include <net/if.h>\n"
                   "#endif\n"
                   "#include <netinet/in.h>\n")
        if manchor in mcontent:
            mcontent = mcontent.replace(manchor, minsert, 1)
        else:
            fanchor = "#include <errno.h>"
            if fanchor in mcontent:
                mcontent = mcontent.replace(
                    fanchor,
                    fanchor + "\n"
                    "#ifndef HAVE_LINUX_WIRELESS\n"
                    "#include <net/if.h>\n"
                    "#endif\n"
                    "#include <netinet/in.h>\n", 1)
            else:
                self.output.warning("lorcon: madwifing_control.c anchor not "
                                    "found, skipping OHOS include fix")
                return
        with open(mtarget, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(mcontent)
        self.output.info("lorcon: added OHOS net/if.h to "
                         "madwifing_control.c")

    def _fix_packasm_uchar_for_ohos(self, source_folder):
        # Build-time BSD-alias repair for lorcon_packasm.h (zero committed
        # patches): upstream declares lcpa_freeze() with `u_char *` while
        # including only <stdint.h>, relying on glibc/pcap transitive
        # <sys/types.h> to provide the BSD alias. The OHOS (musl-like)
        # sysroot does not provide u_char, so lorcon_packasm.h:168 and
        # lorcon_packasm.c:220 fail with `unknown type name 'u_char'`
        # (this round, after the ifreq fixes let the build progress to
        # lorcon_packasm.lo). Insert <sys/types.h> plus a non-glibc
        # fallback typedef; the __GLIBC__ guard keeps glibc builds using
        # the system alias with no redefinition.
        target = os.path.join(source_folder, "lorcon_packasm.h")
        try:
            with open(target, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "LORCON_U_CHAR_FALLBACK" in content:
            return
        old = "#include <stdint.h>"
        new = ("#include <stdint.h>\n"
               "#include <sys/types.h>\n"
               "/* HarmonyOS fix: musl-like sysroot lacks BSD u_char alias */\n"
               "#ifndef __GLIBC__\n"
               "#ifndef LORCON_U_CHAR_FALLBACK\n"
               "#define LORCON_U_CHAR_FALLBACK 1\n"
               "typedef unsigned char u_char;\n"
               "#endif\n"
               "#endif\n")
        if old not in content:
            self.output.warning("lorcon: lorcon_packasm.h stdint anchor not "
                                "found, skipping u_char fix")
            return
        content = content.replace(old, new, 1)
        with open(target, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info("lorcon: added u_char fallback to lorcon_packasm.h")

    def _fix_drv_tuntap_includes_for_ohos(self, source_folder):
        # Build-time include isolation for SYS_LINUX-only driver TUs (zero
        # committed patches): drv_tuntap.c and drv_madwifing.c both
        # unconditionally include <linux/types.h>, <linux/if.h>,
        # <linux/wireless.h> after <sys/socket.h> under bare
        # `#if defined(SYS_LINUX)` (unlike drv_mac80211.c, which is also
        # gated on HAVE_LINUX_WIRELESS+HAVE_LIBNL and compiles out on
        # OHOS). On glibc the two sockaddr_storage definitions coincide,
        # but the OHOS sysroot defines struct sockaddr_storage in both
        # sys/socket.h:377 and linux/socket.h:23 (pulled via linux/if.h),
        # so each TU dies with `redefinition of 'sockaddr_storage'`.
        # Prior round fixed drv_tuntap.c alone (single-file exclusion);
        # this round generalizes to a systematic sweep because the very
        # next object (drv_madwifing.lo) fails with the identical
        # fingerprint -- whack-a-mole one file per round is falsified.
        # Unlike the additive <net/if.h> insertion for
        # ifcontrol/madwifing_control or the rename guard for pcap's
        # pcap-linux.c, insertion alone cannot help here because the
        # offending <linux/if.h> itself is the clash source: it must be
        # conditionally excluded, not supplemented. HAVE_LINUX_WIRELESS
        # is undefined on OHOS (wireless check relaxed above) and these
        # TUs use no wireless structs (only ifreq/sockaddr_ll/PF_PACKET),
        # so on OHOS use <net/if.h> (already ordered after sys/socket.h)
        # and skip the linux/wireless triplet; glibc builds with
        # HAVE_LINUX_WIRELESS keep the original includes byte-identical.
        old = ("#include <linux/types.h>\n"
               "#include <linux/if.h>\n"
               "#include <linux/wireless.h>\n")
        new = ("/* HarmonyOS fix: linux/if.h pulls linux/socket.h whose\n"
               "   sockaddr_storage clashes with sys/socket.h on OHOS */\n"
               "#ifdef HAVE_LINUX_WIRELESS\n"
               "#include <linux/types.h>\n"
               "#include <linux/if.h>\n"
               "#include <linux/wireless.h>\n"
               "#else\n"
               "#include <net/if.h>\n"
               "#endif\n")
        fixed = []
        try:
            names = sorted(os.listdir(source_folder))
        except OSError:
            return
        for fname in names:
            if not fname.endswith(".c"):
                continue
            # Skip the vendored libpcap subtree (own fix) and only touch
            # TUs carrying the exact offending triplet.
            target = os.path.join(source_folder, fname)
            try:
                with open(target, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError:
                continue
            if old not in content or "LORCON_DRV_TUNTAP_OHOS" in content:
                continue
            # Safety: never strip wireless headers from TUs that really
            # consume wireless-extension structs (iwreq/iw_statistics);
            # those need the rename-guard route instead. Driver TUs
            # below only use ifreq/sockaddr_ll.
            if "struct iwreq" in content or "iw_statistics" in content:
                self.output.info("lorcon: skip wireless-struct TU %s" % fname)
                continue
            content = content.replace(old, new, 1)
            # Tag idempotence without leaving a bare macro that could
            # collide: the comment marker is enough since `old` no
            # longer matches after replacement.
            with open(target, "w", encoding="utf-8",
                       errors="surrogateescape") as handle:
                handle.write(content)
            fixed.append(fname)
        if fixed:
            self.output.info("lorcon: isolated linux/if.h in %s"
                             % ", ".join(fixed))
        else:
            self.output.warning("lorcon: drv linux include triplet not found "
                                "in any TU, skipping OHOS include isolation")

    def _fix_bsd_string_aliases_for_ohos(self, source_folder):
        # Build-time BSD-alias repair (zero committed patches): lorcon's
        # ifcontrol_linux.c calls rindex() (BSD deprecated alias for
        # strrchr) in ifconfig_get_sysdriver. glibc declares it in
        # strings.h, but the OHOS (musl-like) sysroot provides no rindex,
        # so the static archive builds fine yet every consumer link dies
        # with `ld.lld: error: undefined symbol: rindex` (this round, at
        # test_package lorcon_test link). rindex(s, c) is exactly
        # strrchr(s, c), so map it at compile time. The __GLIBC__ guard
        # keeps glibc builds using the system symbol byte-identical.
        import re as _re
        try:
            names = sorted(os.listdir(source_folder))
        except OSError:
            return
        fixed = []
        for fname in names:
            if not (fname.endswith(".c") or fname.endswith(".h")):
                continue
            target = os.path.join(source_folder, fname)
            try:
                with open(target, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "LORCON_RINDEX_FALLBACK" in content:
                continue
            if not _re.search(r"\brindex\s*\(", content):
                continue
            anchor = None
            for line in content.splitlines(True):
                stripped = line.strip()
                if stripped.startswith("#include"):
                    anchor = line
                    break
            compat = (
                "/* HarmonyOS fix: OHOS sysroot lacks BSD rindex alias */\n"
                "#ifndef __GLIBC__\n"
                "#ifndef LORCON_RINDEX_FALLBACK\n"
                "#define LORCON_RINDEX_FALLBACK 1\n"
                "#include <string.h>\n"
                "#ifndef rindex\n"
                "#define rindex strrchr\n"
                "#endif\n"
                "#endif\n"
                "#endif\n"
            )
            if anchor is not None:
                content = content.replace(anchor, anchor + compat, 1)
            else:
                content = compat + content
            with open(target, "w", encoding="utf-8",
                       errors="surrogateescape") as handle:
                handle.write(content)
            fixed.append(fname)
        if fixed:
            self.output.info("lorcon: mapped rindex->strrchr in %s"
                             % ", ".join(fixed))
        else:
            self.output.warning("lorcon: rindex call site not found, "
                                "skipping BSD alias fix")

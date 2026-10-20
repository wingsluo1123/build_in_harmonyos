#!/usr/bin/env python3
"""Conan recipe for sniffit 0.7 -- historical packet sniffer and monitoring tool.

sniffit sniffs TCP/UDP/ICMP over IPv4 via libpcap and shows detailed packet
info (SEQ, ACK, TTL, Window) plus payload in hex/text. Optional ncurses
interactive mode (-i/-I) is enabled when ncurses is present.

Upstream build system: GNU Autotools (configure.ac + Makefile.am, automake
foreign). The GitHub tag archive ships configure.ac/autogen.sh but no
generated configure/Makefile.in. Upstream configure.ac hard-requires libpcap
and optionally uses ncurses; both are Conan requires so the feature set is
deterministic. Upstream ships no test suite (no TESTS/check target, no
tests/ dir -- see test_package/MANIFEST.yml audit), so build() runs no make
check; the consumer test in test_package/ drives the packaged binary.

OHOS build strategy (no patches/ dir, no autoreconf on device):
  - Strategy-cycle-2 change: build() compiles the 7 translation units listed
    in src/Makefile.am SOURCES directly with the Conan toolchain compiler
    instead of running autoreconf/configure/make on the device. Rationale:
    the preflight failure is in the *dependency* m4/1.4.19
    (configure[139]: /data/service/hnp/bin/bash inaccessible, Error 127),
    which Conan builds before this recipe's generate() env script can apply;
    hardening SHELL/CONFIG_SHELL inside this recipe (cycle-1 fix) therefore
    never reaches m4. Removing the automake/autoconf/libtool tool_requires
    removes the m4 build edge entirely, so the missing-HNP-bash runner
    failure mode disappears regardless of remote priority (aldo/0.7.8
    vendoring precedent for avoiding the m4 rebuild).
  - config.h (included by src/sn_config.h as <config.h>) is generated in
    build() with values matching configure.ac probes on OHOS aarch64
    (LP64 + musl + libpcap/ncurses required): HAVE_LIBNCURSES,
    HAVE_NCURSES_H, HAVE_SHMGET, HAVE_ATEXIT, HAVE_SETSERVENT,
    SIZEOF_UNSIGNED_SHORT_INT=2, SIZEOF_UNSIGNED_LONG_INT=8,
    SIZEOF_UNSIGNED_INT=4, USE_32_INT. See _write_config_h().
  - Compiler/TMPDIR handling: the repo profile pins
    tools.build:compiler_executables to /data/service/hnp/bin/clang(++),
    absent on some HMBS hosts; generate() saves a build-scope env script
    with a writable TMPDIR plus a PATH/SDK compiler fallback, and build()
    re-exports CC/CXX inline AFTER conanbuild.sh is sourced. No configure
    re-exec exists anymore, so no SHELL/CONFIG_SHELL re-export hazard.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SniffitConan(ConanFile):
    name = "sniffit"
    version = "0.7"
    description = "Historical packet sniffer and monitoring tool for TCP/UDP/ICMP over IPv4"
    license = "BSD-3-Clause"
    homepage = "https://github.com/resurrecting-open-source-projects/sniffit"
    url = ""  # CI fills this repository URL

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Exact translation units from src/Makefile.am (sbin_PROGRAMS = sniffit).
    # NOTE: src/ also contains sn_conn_desc.c, which upstream does NOT list
    # in sniffit_SOURCES -- it must be excluded (globbing src/*.c would add
    # an unwanted TU).
    _SOURCES = [
        "sn_packets.c",
        "sn_generation.c",
        "sn_interface.c",
        "sn_cfgfile.c",
        "sn_logfile.c",
        "sn_resolv.c",
        "sniffit.c",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sniffit is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def requirements(self):
        # configure.ac: AC_CHECK_LIB(pcap, ...) is fatal when missing;
        # ncurses is optional upstream but required here so the interactive
        # mode (-i/-I, INCLUDE_INTERFACE) builds deterministically.
        # libpcap/1.10.6 is RREV-pinned to the ohpcd recipe: a bare ref
        # resolves conancenter-first on HMBS preflight (official CI disables
        # conancenter; alberta/abuild-sudo precedent) to the CCI autotools
        # recipe, whose bison/flex tool_requires drag in a CCI m4 source
        # build that dies on the missing HNP bash (mgen/5.02.c5.1.1 hit the
        # identical `libpcap -> bison/flex -> m4` signature). The ohpcd
        # recipe (cmake, no tool_requires) cannot pull m4. RREV e4d43bf9 was
        # read from the registry with `conan download --only-recipe`
        # (lltdscan/0-20180223 notes, 2026-10-10). ncurses/6.6 stays bare:
        # absent from CCI (latest there is 6.5), so it always resolves ohpcd.
        self.requires("libpcap/1.10.6#e4d43bf9a29fdaabd60dee919243c781")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # Intentionally no automake/autoconf/libtool tool_requires: the tag
        # archive has no generated configure, and bootstrapping it on the
        # device pulls m4/1.4.19 from conancenter, whose configure re-execs
        # the profile-pinned /data/service/hnp/bin/bash (inaccessible on
        # some HMBS runners -> Error 127 before this package ever builds).
        # Direct compilation below needs only the Conan toolchain compiler
        # plus the libpcap/ncurses requires, so no m4 edge originates from
        # this recipe. The remaining transitive edge (bare libpcap resolving
        # to the CCI recipe conancenter-first) is cut by the libpcap RREV pin
        # in requirements().
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps injects -I/-L/-l for libpcap/ncurses into
        # conanbuild (CPPFLAGS/LIBS); AutotoolsToolchain provides the OHOS
        # target/sysroot CFLAGS/LDFLAGS consumed via env="conanbuild".
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Compiler/TMPDIR hardening: the repo profile pins the clang paths,
        # which are absent on some HMBS hosts. A generated build-scope
        # script wins over the profile [buildenv]; inline os.environ tweaks
        # alone do not.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        cc, cxx, lbl = self._resolve_compiler()
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        env.vars(self, scope="build").save_script("sniffit_hmos_fix")
        self.output.info(
            "sniffit_hmos_fix: SHELL/CONFIG_SHELL=%s TMPDIR=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, lbl, cc, cxx)
        )

    def _usable_shell(self):
        # Hard-prefer /bin/sh (HMBS capability shell=/bin/sh); never return
        # the HNP bash path even if isfile() is true for it (it may exist
        # but be non-executable: "inaccessible or not found").
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Keep the profile tools.build:compiler_executables value when the
        file exists (CI worker unchanged); otherwise fall back to a
        PATH/SDK-resolved clang so the direct-cc build can run. Pure
        isfile probing, no X_OK probing per R49.
        """

        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        if _ok(conf_cc) and not conf_cxx:
            sib = conf_cc + "++" if conf_cc.endswith("clang") else ""
            if _ok(sib):
                return conf_cc, sib, "profile-cxx-sibling"
        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = []
        for d in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if d and d not in cand_dirs:
                cand_dirs.append(d)
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
                    if sib not in cand_dirs:
                        cand_dirs.append(sib)
        except Exception:
            pass
        found_cc, found_cxx = "", ""
        for name in cc_names:
            w = shutil.which(name)
            if _ok(w):
                found_cc = w
                break
        for name in cxx_names:
            w = shutil.which(name)
            if _ok(w):
                found_cxx = w
                break
        if not found_cc or not found_cxx:
            for d in cand_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for n in cc_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cc = p
                            break
                if not found_cxx:
                    for n in cxx_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cxx = p
                            break
                if found_cc and found_cxx:
                    break
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            sib = cc + "++"
            if _ok(sib):
                cxx = sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _write_config_h(self, cfg_dir):
        """Write the config.h consumed as <config.h> by src/sn_config.h.

        Values mirror configure.ac probes for OHOS aarch64 (LP64 musl with
        the libpcap + ncurses requires present):
          HAVE_LIBNCURSES/HAVE_NCURSES_H/HAVE_SHMGET -> keep
          INCLUDE_INTERFACE (== upstream --with-ncurses default);
          HAVE_ATEXIT -> sn_config.h exit_func() selects atexit();
          HAVE_SETSERVENT -> AC_CHECK_FUNC(setservent) passes on musl;
          short==2 / long==8 / int==4 (aarch64 LP64) -> USE_32_INT.
        """
        os.makedirs(cfg_dir, exist_ok=True)
        path = os.path.join(cfg_dir, "config.h")
        content = """/* config.h -- generated by sniffit/0.7 recipe (direct-cc build).

   Mirrors the configure.ac probe results for OHOS aarch64 (LP64 musl,
   libpcap + ncurses requires present). sn_config.h includes this file
   as <config.h>; keep the HAVE_* set in sync with configure.ac. */
#ifndef SNIFFIT_CONFIG_H
#define SNIFFIT_CONFIG_H

/* Package identity (AC_INIT). */
#define PACKAGE_NAME "sniffit"
#define PACKAGE_TARNAME "sniffit"
#define PACKAGE_VERSION "0.7"
#define PACKAGE_STRING "sniffit 0.7"
#define PACKAGE_BUGREPORT "https://github.com/resurrecting-open-source-projects/sniffit/issues"
#define PACKAGE_URL "https://github.com/resurrecting-open-source-projects/sniffit"
#define VERSION "0.7"

/* AC_CHECK_LIB(ncurses, initscr) + AC_CHECK_HEADERS([ncurses.h]). */
#define HAVE_LIBNCURSES 1
#define HAVE_NCURSES_H 1

/* AC_CHECK_HEADERS([pcap.h]). */
#define HAVE_PCAP_H 1

/* AC_CHECK_FUNCS(shmget): musl provides sys/shm.h shmget; gates
   INCLUDE_INTERFACE in sn_config.h together with the ncurses pair. */
#define HAVE_SHMGET 1

/* AC_CHECK_FUNCS(atexit): selects atexit() in sn_config.h exit_func(). */
#define HAVE_ATEXIT 1

/* AC_CHECK_FUNC(setservent): provided by musl netdb. */
#define HAVE_SETSERVENT 1

/* AC_CHECK_SIZEOF on aarch64 LP64: short==2, long==8, int==4. */
#define SIZEOF_UNSIGNED_SHORT_INT 2
#define SIZEOF_UNSIGNED_LONG_INT 8
#define SIZEOF_UNSIGNED_INT 4
#define USE_32_INT 1

/* Standard headers available on OHOS musl. */
#define STDC_HEADERS 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_UNISTD_H 1

#endif /* SNIFFIT_CONFIG_H */
"""
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("wrote generated config.h to %s" % path)
        return path

    def build(self):
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        cc, cxx, lbl = self._resolve_compiler()
        self.output.info(
            "sniffit direct-cc build shell=%s tmpdir=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, lbl, cc, cxx)
        )
        prefix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
            % (shell, shell, tmpdir, tmpdir, tmpdir)
        )
        if cc:
            prefix += 'export CC="%s" && ' % cc
            os.environ["CC"] = cc
        if cxx:
            prefix += 'export CXX="%s" && ' % cxx
            os.environ["CXX"] = cxx
        # config.h goes to an isolated generated dir (never into the
        # upstream source tree); -I picks it up as <config.h>.
        gen_dir = os.path.join(self.build_folder, "sniffit-gen")
        self._write_config_h(gen_dir)
        src_dir = os.path.join(self.source_folder, "src")
        missing = [s for s in self._SOURCES
                   if not os.path.isfile(os.path.join(src_dir, s))]
        if missing:
            raise ConanInvalidConfiguration(
                "sniffit sources missing from upstream tree: %s" % ", ".join(missing)
            )
        # $CC comes from the inline export above (profile value when it
        # exists, PATH/SDK fallback otherwise); $CPPFLAGS/$CFLAGS/$LDFLAGS/
        # $LIBS come from conanbuild (AutotoolsDeps + AutotoolsToolchain for
        # the libpcap/ncurses -I/-L/-l and the OHOS target/sysroot flags).
        # $LIBS already carries the exact static link set declared by the
        # requires (libpcap -> -lpcap; ncurses/6.6 static widec-only ->
        # -lformw -lmenuw -lpanelw -lncursesw, there is NO libncurses.a, so
        # a hardcoded -lncurses always fails with "unable to find library
        # -lncurses"). Keep $LIBS as the single -l source; the explicit
        # tail below repeats the same widec set in recipe order as a
        # fallback in case LIBS is ever empty, never -lncurses.
        srcs = " ".join('"%s"' % os.path.join(src_dir, s) for s in self._SOURCES)
        out = os.path.join(self.build_folder, "sniffit")
        cmd = (
            prefix
            + '"$CC" $CPPFLAGS $CFLAGS -I"%s" -I"%s" %s $LDFLAGS $LIBS '
              '-lpcap -lformw -lmenuw -lpanelw -lncursesw -o "%s"'
            % (gen_dir, src_dir, srcs, out)
        )
        self.run(cmd, env="conanbuild")
        if not os.path.isfile(out) or os.path.getsize(out) == 0:
            raise ConanInvalidConfiguration(
                "direct-cc build produced no sniffit binary at %s" % out
            )
        self.output.info("sniffit direct-cc build OK: %s" % out)
        # Upstream ships no test suite (no TESTS/check target, no tests/
        # dir -- audit in test_package/MANIFEST.yml), so there is no
        # `make check` to run here. The packaged binary is validated by
        # test_package/test_sniffit.sh (R34 consumer test).

    def package(self):
        # Direct-cc build: install the linked binary + docs explicitly
        # (no `make install`; there is no generated Makefile anymore).
        bin_src = os.path.join(self.build_folder, "sniffit")
        if not os.path.isfile(bin_src):
            # Keep the build_folder layout assumption explicit: basic_layout
            # may place the binary next to the recipe build root.
            raise ConanInvalidConfiguration(
                "sniffit binary missing at package() time: %s" % bin_src
            )
        bin_dst_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst_dir, exist_ok=True)
        shutil.copy2(bin_src, os.path.join(bin_dst_dir, "sniffit"))
        try:
            os.chmod(os.path.join(bin_dst_dir, "sniffit"), 0o755)
        except OSError:
            pass
        # Upstream man pages (Makefile.am man_MANS).
        man_src_dir = os.path.join(self.source_folder, "man")
        for page, section in (("sniffit.5", "man5"), ("sniffit.8", "man8")):
            src = os.path.join(man_src_dir, page)
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "share", "man", section)
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dst_dir, page))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # CLI tool, not a library (R38: commands.json at software level).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

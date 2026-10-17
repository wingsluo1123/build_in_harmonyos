#!/usr/bin/env python3
"""Conan recipe for ircd-ircu (Undernet IRC daemon, ircu2) 2.10.12.19.

ircu2 is the IRC server maintained by Undernet IRC; it is a pure C daemon with
**no external library dependencies** (only libc plus the optional in-tree
libcrypt shims), so this recipe has zero `requires`.

Build system: autoconf (`./configure`) driving hand-written recursive Makefiles.
The release tarball deliberately ships *without* the generated lexer/parser, so
`flex` (ircd_lexer.l -> lex.yy.c) and `bison` (ircd_parser.y -> y.tab.c/y.tab.h)
plus the in-tree `table_gen` host tool are required at build time.

OHOS adaptation notes (see notes.md):
  - patches/0001 + 0002 add HarmonyOS/aarch64 recognition to the 2005-era
    config.guess / config.sub shipped in the release tarball (E007). The CI and
    local gate both build with identical host/build profiles, so Conan does not
    emit `--host`; config.guess still runs, and config.sub is what a genuine
    cross build (`-pr:b != -pr:h`) would need.
  - patches/0003 replaces ircd/umkpasswd.c's getpass(3) call: musl, the libc
    HarmonyOS is built on, does not implement getpass at all, so the file does
    not even compile there.
  - patches/0004 lowers autoconf 2.64's `umask 077` to `022` for the scratch
    directory it makes for config.status: on the worker's HMDFS-backed build
    folder the 077 directory cannot be written into, so config.status dies with
    `./confXXXXXX/subs1.awk: Permission denied` right after being created and no
    config file is ever generated (worker-only; ext4 reproduces nothing).
  - m4/1.4.19 is an explicit tool_requires so bison always drives a known GNU m4.
    bison/3.8.2 was published with `/data/service/hnp/bin/m4` baked in, which
    exists on the worker image, so the previous recipe only ever overrode M4 on
    local WSL; on the worker that left bison producing an empty y.tab.c (build
    #79156) and the link of `ircd` failed with `undefined symbol: yyparse`.
  - The tarball also ships stale build products (Makefile / config.status /
    config.h) generated on the packager's machine. `source()` removes them so
    `./configure` is forced to regenerate every one from its `.in` template.
  - layout() points the build folder back at the source folder: the top-level
    Makefile.in has no VPATH, so a VPATH build cannot find `configure`.
  - `--bindir` is pinned to the package's bin/ so config.h's SPATH (the restart
    path, which ircd `access(X_OK)`-checks at startup) points at the artifact
    this recipe actually installs.
  - `--with-dpath` pins DPATH inside the package folder instead of leaving it at
    the upstream default (which is $libdir == `/lib` because Conan passes
    --prefix=/); test and runtime always override it with -d.
  - `--with-symlink=no` selects the `install-no-symlink` rule, avoiding the
    `bin/ircd.<timestamp>` + symlink scheme (which also writes /tmp/ircd.tag).
  - package() copies the artifacts instead of running `make install`: upstream's
    install rules ignore ${DESTDIR} (they would write into the build host's
    /bin) and end in the host `strip`, which cannot read an aarch64 ELF.
  - Upstream unit tests (`ircd/test/*_t.c`, 4 programs) are executed in
    `build()`; `test_package/` drives the installed daemon through a real IRC
    handshake.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Build products that ship inside the upstream release tarball, generated on the
# packager's machine with their own prefix/paths. They must go before configure
# runs, otherwise `make` may consider them up to date (identical 2019 mtimes).
STALE_BUILD_PRODUCTS = (
    "Makefile",
    "config.status",
    "config.log",
    "config.h",
    "stamp-h",
    os.path.join("ircd", "Makefile"),
    os.path.join("ircd", "test", "Makefile"),
)

# Upstream unit-test programs built by `make` (SUBDIRS = ircd ircd/test).
UPSTREAM_TEST_PROGRAMS = (
    "ircd_chattr_t",
    "ircd_in_addr_t",
    "ircd_match_t",
    "ircd_string_t",
)

# Binaries upstream's `install-no-symlink` rule would place in BINDIR.
INSTALLED_BINARIES = ("ircd", "umkpasswd", "convert-conf")

# Upstream's `ircd/Makefile.in` generates the parser with bison and only checks
# bison's exit status.  bison exits 0 even when its m4 subprocess dies part way
# through, leaving an empty y.tab.c; the only visible symptom is
# `undefined symbol: yyparse` hundreds of lines later at the link step.  So the
# generation is also done up front and the artefact is asserted here.
PARSER_FILE = "y.tab.c"
PARSER_REL = os.path.join("ircd", PARSER_FILE)
PARSER_SYMBOL_CHECK = "yyparse"

# MAXCONNECTIONS, i.e. what `ircd -v` calls the compiled connection maximum.
# Must stay below numnicks.c's NN_MAX_CLIENT (64^3 = 262144) and, practically,
# below the RLIMIT_NOFILE a consumer is likely to have.
MAX_CONNECTIONS = 1024


class IrcdIrcuConan(ConanFile):
    name = "ircd-ircu"
    version = "2.10.12.19"
    description = "Undernet IRC daemon (ircu2) - IRC server, autotools, pure C"
    license = "GPL-2.0-only"
    homepage = "https://github.com/UndernetIRC/ircu2"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    topics = ("irc", "ircd", "ircu", "ircu2", "undernet", "server", "daemon")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ircd-ircu supports Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "ircd-ircu is verified on OHOS armv8 (aarch64) only"
            )

    def requirements(self):
        # ircu2 has no external library dependencies: configure.in only does
        # AC_SEARCH_LIBS(crypt, descrypt crypt) against libc and the crypto
        # back-ends are compiled from libircd sources shipped in the tarball.
        pass

    def build_requirements(self):
        # The release tarball ships ircd_lexer.l / ircd_parser.y but NOT the
        # generated lex.yy.c / y.tab.c / y.tab.h, so flex + bison are hard
        # build requirements. CI has no system-wide flex/bison (same situation
        # as archives/c/canlock/3.3.1 and archives/c/captagent/6.4.4).
        #
        # flex/2.6.4.2, not flex/2.6.4: the older package only ships
        # libfl.a + FlexLexer.h and no bin/flex at all.
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")
        # m4/1.4.19: bison shells out to m4 to turn ircd_parser.y into y.tab.c.
        # bison/3.8.2 was published with an absolute m4 program baked in
        # (/data/service/hnp/bin/m4), which exists on the OHOS CI worker image;
        # because of that, the old _bison_env() left M4 alone there and only
        # ever exercised the override on local WSL. With that host-provided m4
        # the CI build produced an EMPTY y.tab.c (build #79156) while bison
        # itself exited 0 - lld then reported `undefined symbol: yyparse` /
        # `yylval` from the link step, which points nowhere near the cause.
        # Depending on m4/1.4.19 explicitly makes the m4 used by bison the same
        # GNU build on every host, and its binary for ohos-aarch64 is a real
        # aarch64/musl ELF. m4 is *not* a `requires`: bison already declares it
        # as a build requirement and Conan skips its binary; asking for it here
        # is purely to put a known-good m4 first on the build PATH.
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self, src_folder="src")
        # ircu's hand-written Makefiles are not VPATH-clean at the top level
        # (`config.status: configure` with no VPATH for `configure`), so the
        # build must happen inside the source tree.
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for stale in STALE_BUILD_PRODUCTS:
            stale_path = os.path.join(self.source_folder, stale)
            if os.path.isfile(stale_path):
                os.remove(stale_path)

    # A tiny m4 program: define a macro and expand it. Exercises startup *and*
    # macro expansion, so a binary that runs but quietly produces nothing (the
    # exact failure that silently empties y.tab.c) is rejected.
    M4_PROBE_INPUT = b"define(`ircd_probe',`m4-ok')ircd_probe\n"
    M4_PROBE_EXPECT = b"m4-ok"

    def _m4_works(self, candidate):
        """True only if `candidate` starts up and really expands a macro."""
        try:
            probe = subprocess.run(
                [candidate],
                input=self.M4_PROBE_INPUT,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return probe.returncode == 0 and self.M4_PROBE_EXPECT in (probe.stdout or b"")

    def _usable_m4(self):
        """First m4 on PATH that really works here, or None.

        `shutil.which()`/`--version` are not enough. bison drives m4 as a
        subprocess and trusts its exit status; an m4 that cannot start, or that
        starts but outputs nothing, leaves bison with no parser at all while
        bison itself still exits 0. Concretely, m4/1.4.19's ohos-aarch64 binary
        prints `Error relocating ...: __strchr_chk: symbol not found` on a WSL
        host (the local guest libc is missing the shims - T167) but runs
        natively on the device, so the only portable test is to execute it on a
        real m4 program.
        """
        candidates = []
        found = shutil.which("m4")
        if found:
            candidates.append(found)
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(directory, "m4")
            if candidate not in candidates and os.path.isfile(candidate) \
                    and os.access(candidate, os.X_OK):
                candidates.append(candidate)
        for candidate in candidates:
            if self._m4_works(candidate):
                return candidate
        return None

    def _bison_env(self):
        """Build the environment overrides bison/3.8.2 from this registry needs.

        Two relocation bugs have to be worked around, both verified locally:

        1. PKGDATADIR is baked in as `/share/bison` while the m4 skeletons ship
           inside the package, so bison aborts with
           ``bison: /share/bison/m4sugar/m4sugar.m4: cannot open``.
        2. The m4 program is baked in as the absolute path
           ``/data/service/hnp/bin/m4``.  Where that path happens to exist (the
           OHOS worker image) it is still not an m4 this recipe can vouch for:
           when m4 cannot run properly bison writes a truncated y.tab.c and
           still exits 0, and the failure surfaces much later as
           `undefined symbol: yyparse` at link time (build #79156).

        Both are derived from what is actually on PATH - never hardcoded.
        `tool_requires("m4/1.4.19")` puts a GNU m4 on PATH on every host, and
        `_usable_m4()` picks the first candidate that really executes, so a
        binary that cannot start here is skipped instead of silently poisoning
        the parser generation.
        """
        bison_bin = shutil.which("bison")
        if not bison_bin:
            raise ConanInvalidConfiguration(
                "bison is not on PATH; the tool_requires(flex, bison) "
                "environment did not reach build()"
            )
        bison_prefix = os.path.dirname(os.path.dirname(bison_bin))
        overrides = {}
        pkgdatadir = os.path.join(bison_prefix, "share", "bison")
        if os.path.isdir(pkgdatadir):
            overrides["BISON_PKGDATADIR"] = pkgdatadir
        m4 = self._usable_m4()
        if m4:
            overrides["M4"] = m4
            self.output.info("[bison] using m4: {}".format(m4))
        else:
            raise ConanInvalidConfiguration(
                "no runnable m4 found on PATH; bison cannot generate "
                "ircd_parser.y without one (tool_requires(flex, bison, m4) "
                "did not reach build())"
            )
        return overrides

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Conan passes --prefix=/ and installs with DESTDIR=<package_folder>.
        #
        # --bindir        -> config.h's SPATH ("path to executable for restarts",
        #   see configure.in) is derived from it. The default would be
        #   `//bin/ircd`, i.e. the *build host's* /bin, which does not exist, and
        #   ircd aborts at startup with `Check on SPATH failed`. Autoconf takes
        #   the last --bindir, so pin it to where this recipe really installs.
        # --with-symlink=no  -> `install-no-symlink` rule: installs bin/ircd
        #   directly instead of bin/ircd.<date> + a relative symlink, and skips
        #   the `echo date > /tmp/ircd.tag` scratch file.
        # --with-mode=755   -> readable/executable by every consumer of the
        #   package (upstream default is owner-only for read).
        # --with-dpath      -> DPATH, ircd's default data directory. Pinned
        #   inside the package folder rather than left at the upstream default
        #   ($libdir == `/lib` because of --prefix=/); test and runtime always
        #   override it with -d anyway.
        # --with-maxcon     -> MAXCONNECTIONS. Upstream leaves this at
        #   `ulimit -Hn - 4` **of the machine running configure**, so the number
        #   is baked in from an unrelated host: here it came out as 1048572,
        #   above numnicks.c's hard limit NN_MAX_CLIENT (= 64^3 = 262144), and
        #   every ircd invocation died at startup with
        #   "MAXCLIENTS (or MAXCONNECTIONS) is (at least) 786432 too large".
        #   Pin it so the build is reproducible and the daemon can start.
        tc.configure_args.extend([
            "--bindir={}".format(os.path.join(self.package_folder, "bin")),
            "--with-symlink=no",
            "--with-mode=755",
            "--with-maxcon={}".format(MAX_CONNECTIONS),
            "--with-dpath={}".format(os.path.join(self.package_folder, "ircd")),
        ])
        # /dev/poll (Solaris) and kqueue (BSD/macOS) do not exist on OHOS; being
        # explicit keeps the selected event engine deterministic across hosts.
        tc.configure_args.extend([
            "--disable-devpoll",
            "--disable-kqueue",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        bison_env = self._bison_env()
        m4 = bison_env["M4"]
        # BISON_PKGDATADIR also has to survive into configure's compiler probes;
        # exporting it through os.environ covers configure and any self.run()
        # that does not go through Autotools.
        os.environ.update(bison_env)
        autotools = Autotools(self)
        autotools.configure()
        self._check_parser_generator(m4)
        # flex 2.6.4 expands its own skeleton with m4 too (ircd_lexer.l ->
        # lex.yy.c). When the m4 it finds cannot run, flex leaves a ZERO-BYTE
        # lex.yy.c and dies with `Error 141`, which `make` reports as a plain
        # rule failure. Both generators therefore have to be handed the same
        # working m4.
        #
        # os.environ["M4"] is NOT enough here: Conan applies (and restores) the
        # conanbuild environment around each self.run(), so a variable put into
        # os.environ does not reliably reach the make subprocess. Passing it as
        # a make variable does: GNU make exports command-line variables into the
        # environment of every recipe line, which is exactly where flex and
        # bison read M4 from.
        autotools.make(args=["M4={}".format(m4)])
        self._run_upstream_tests()

    def _check_parser_generator(self, m4):
        """Generate ircd_parser.y with the configured bison+m4 and assert it.

        `ircd/Makefile.in` does this itself, but only checks bison's exit
        status. bison exits 0 even when its m4 subprocess dies part way
        through, in which case `y.tab.c` comes out empty and the failure is
        reported by lld as `undefined symbol: yyparse` from the final link of
        `ircd` - hundreds of lines later and pointing at the wrong thing.
        Doing it here means the error names bison and m4.

        M4 is passed on the command line rather than relying on the inherited
        environment: it is the one variable that decides whether the parser
        exists at all, and an inherited one can be lost silently.

        The assertion reads the finished file rather than piping bison into a
        grep: `bison ... | grep -q yyparse` makes grep close the pipe on the
        first match and kills bison with SIGPIPE (ConanException: Error 141).
        """
        parser_dir = os.path.join(self.source_folder, "ircd")
        self.run('M4="{}" bison -y -d ircd_parser.y'.format(m4), cwd=parser_dir)
        parser = os.path.join(parser_dir, PARSER_FILE)
        if not os.path.isfile(parser):
            raise ConanException(f"bison produced no {PARSER_REL}")
        size = os.path.getsize(parser)
        with open(parser, "r", errors="replace") as parser_file:
            body = parser_file.read()
        if size == 0 or PARSER_SYMBOL_CHECK not in body:
            raise ConanException(
                f"bison+m4 produced an unusable {PARSER_REL} "
                f"({size} bytes, defines {PARSER_SYMBOL_CHECK}: "
                f"{PARSER_SYMBOL_CHECK in body}); the m4 bison drives is not "
                "producing the parser tables"
            )
        self.output.info(
            "[parser-gen] {} generated by bison+m4 ({} bytes)".format(
                PARSER_REL, size
            )
        )

    def _run_upstream_tests(self):
        """Execute the four upstream unit-test programs built by `make`.

        ircu ships no `make check` target; `ircd/test/Makefile.in` builds four
        standalone C test programs that the top-level `all` target already
        compiles (SUBDIRS = ircd ircd/test). Running them here is the only way
        to execute upstream's own test code in an automated build.
        """
        test_bin_dir = os.path.join(self.source_folder, "ircd", "test")
        for program in UPSTREAM_TEST_PROGRAMS:
            program_path = os.path.join(test_bin_dir, program)
            if not os.path.isfile(program_path):
                raise ConanException(
                    f"upstream test program was not built: {program_path}"
                )
            out_file = os.path.join(self.build_folder, program + ".out")
            # A test program that produced no output at all would still exit 0,
            # so assert non-empty output as well as a zero exit status.
            self.run('"{}" > "{}" && test -s "{}"'.format(
                program_path, out_file, out_file))
            self.output.info("[upstream-test] {}: executed, output captured".format(program))

    def package(self):
        """Copy the four artifacts upstream would install, by hand.

        `make install` is unusable here, for two independent reasons:

        1. ircd's install rules never prefix ${DESTDIR}: they run
           `${INSTALL} ... ircd ${BINDIR}/ircd` with BINDIR=//bin (Conan passes
           --prefix=/), so a build writes straight into the *build host's* /bin.
           Verified: an earlier local run left /usr/bin/ircd (954 KB) behind on
           the WSL host and still produced an empty package.
        2. `${INSTALL} -s` ends in the host `strip`, which cannot recognise an
           aarch64 ELF when the build host is x86, so the rule dies with
           `strip: Unable to recognise the format of the input file` and takes
           the rest of the install with it.

        Copying explicitly also re-stamps the executable bit, which the
        hmdfs-backed package folder on the real worker otherwise leaves
        non-executable (build tree runs, packaged binary gets EPERM).
        """
        pkg_bin = os.path.join(self.package_folder, "bin")
        for binary in INSTALLED_BINARIES:
            built = os.path.join(self.source_folder, "ircd", binary)
            if not os.path.isfile(built):
                raise ConanException(f"expected build product is missing: {built}")
            copy(self, binary, src=os.path.join(self.source_folder, "ircd"), dst=pkg_bin)
            os.chmod(os.path.join(pkg_bin, binary), 0o755)

        example_conf = os.path.join(self.source_folder, "doc", "example.conf")
        if not os.path.isfile(example_conf):
            raise ConanException(f"upstream example configuration is missing: {example_conf}")
        copy(self, "example.conf", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "ircd"))
        os.chmod(os.path.join(self.package_folder, "ircd", "example.conf"), 0o644)

    def package_info(self):
        # ircu is a server binary set (ircd / umkpasswd / convert-conf), not a
        # library: no libs, no headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.defines = []
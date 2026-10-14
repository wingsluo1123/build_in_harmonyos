#!/usr/bin/env python3
"""Conan recipe for xmlto 0.0.29 — XSL toolchain front-end (CLI tool).

Autotools bootstrap on OHOS
---------------------------
The upstream release ships `configure.ac`/`Makefile.am`/`config.h.in` but no
generated `configure`/`Makefile.in`/`aclocal.m4`, so the build must bootstrap
the autotools machinery itself.

`autoreconf` cannot be used here: it execve()'s `$ACLOCAL`, and OHOS refuses
execve of scripts that live on HMDFS (a conan build tree lives under
`~/.conan2/p/...`), which manifests as EACCES/exit 13 on a healthy worker and
as an unkillable hang on a wedged one (CI build #81400: `aclocal` stuck for
14400 s with no output, SIGKILL ineffective, cleanup step wedged as well).
The automake Perl scripts are therefore invoked through the `perl`
interpreter (execve of an interpreter binary is unrestricted), the generated
`configure` is driven through `sh`, and the tool_requires package is used
directly instead of via its `sh` wrapper.  Reference implementation:
archives/w/wmtop/0.85.

CI build #85406 surfaced two further failure modes on a fork-starved worker:
`autom4te` could not run its `m4` child (`sh: can't fork - try again`,
misreported as "need GNU m4 1.4 or later"), and the failed `perl` left
conan's stdout pipe open, so `conan create` burned the whole 3600 s timeout
instead of failing fast.  Counter-measures:
  * m4 comes from the published `m4/1.4.19` tool package — `autom4te`
    honours `$M4` (autom4te.in: `my $m4 = $ENV{"M4"} || 'm4'`), and the m4
    package exports `M4=<pkg>/bin/m4` through its buildenv, so the bootstrap
    no longer depends on the worker's system m4 at all.
  * every bootstrap/configure/compile step runs with its output redirected
    into a log file (conan's own pipe reaches EOF as soon as the direct
    child exits — a lingering grandchild can no longer hang the run) and is
    retried on transient failures.

E540 note (agent sandbox only): the safe-bin `rm` shim has a `#!/bin/bash`
shebang while `/bin/bash` does not exist on OHOS; the local sandbox therefore
cannot run `make install` reliably, so xmlif is compiled with clang directly
and the package tree is assembled with Python file copies.  CI has no
safe-bin and would accept the plain autotools flow just as well.

CI build #88833 (PR #15135) surfaced a third failure mode: configure ran to
completion but `config.status` aborted with

    ./config.status[765]: can't create ./confbNNjmm/subs1.awk: Permission denied
    config.status: error: could not setup config files machinery

`config.status` creates its scratch dir with `(umask 077 && mktemp -d
"./confXXXXXX")`.  On the CI worker (HMFS uid-domain mapping) that directory
comes back unwritable for the creating process, and since this recipe
bootstraps its own configure (the tarball ships none), the block has to be
patched after `autoconf` generates it - a static source patch would not
survive the bootstrap.  `_harden_scratch_machinery()` rewrites the two
`umask 077` occurrences (mktemp + conf$$-fallback, both in configure and in
a pre-existing config.status) and inserts a probe + chmod + fallback block
right after `ac_tmp=$tmp`: probe with the very operation that failed
(`: >"$ac_tmp/.wr-probe"`), `chmod 0777` retry, then fall back to a
dedicated dir under the conan build folder (never the cwd - the exit trap
`rm -fr "$ac_tmp"` would then delete the build tree).  Reference
implementation: archives/u/uim/1.9.6 (knowledge E011, CI #87163).
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os
import shlex
import shutil
import time


# E011 (HMDFS) hardening injected into autoconf's scratch-dir block.
# `@BUILD_FOLDER@` is replaced with the conan build folder at patch time.
_SCRATCH_HARDEN_TMPL = r'''ac_tmp=$tmp
# --- build_in_harmonyos E011: make the scratch dir provably writable ------
# HMDFS can hand back a scratch directory the creating process cannot write
# into; config.status then aborts with
#   can't create ./confXXXXXX/subs1.awk: Permission denied
#   config.status: error: could not setup config files machinery
# (CI #88833, PR #15135).  mktemp -d forces mode 0700 regardless of umask,
# so the umask rewrite alone is not trusted; probe with the exact operation
# that fails, rescue with chmod, and fall back to a dedicated dir in the
# conan build folder.  The exit trap removes $ac_tmp, so every candidate is
# a dedicated directory (never the cwd: `.` would make the trap `rm -fr .`).
_bihe011_err=
if ! _bihe011_err=$( { umask 002; : >"$ac_tmp/.wr-probe"; } 2>&1 ); then
  chmod 0777 "$ac_tmp" 2>/dev/null
  if ! _bihe011_err=$( { umask 002; : >"$ac_tmp/.wr-probe"; } 2>&1 ); then
    echo "config.status: scratch dir '$ac_tmp' unwritable: $_bihe011_err" >&2
    ac_tmp="@BUILD_FOLDER@/xmlto-cs-$$"
    mkdir -p "$ac_tmp" 2>/dev/null
    chmod 0777 "$ac_tmp" 2>/dev/null
    if _bihe011_err=$( { umask 002; : >"$ac_tmp/.wr-probe"; } 2>&1 ); then
      echo "config.status: using fallback scratch dir $ac_tmp" >&2
    else
      echo "config.status: fallback scratch dir unwritable: $_bihe011_err" >&2
    fi
  fi
fi
rm -f "$ac_tmp/.wr-probe" 2>/dev/null
# --- end build_in_harmonyos E011 -----------------------------------------
'''


def _prepare_autotools_env():
    """The installed automake scripts read AUTOM4TE (and friends) from the
    environment and otherwise fall back to a bare name; the automake package
    may also carry bake-in absolute paths that do not exist here.  Point the
    var at whatever is actually on PATH (same approach as
    abiword-plugin-clarisworks)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class XmltoConan(ConanFile):
    name = "xmlto"
    version = "0.0.29"
    description = "xmlto - front-end to a XSL toolchain (applies XSL stylesheets to XML documents)"
    license = "GPL-2.0-or-later"
    homepage = "https://pagure.io/xmlto"
    url = "https://pagure.io/xmlto"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Bootstrap needs aclocal/automake.  The CI sandbox (USER=100) only has
        # the autoconf suite under /data/service/hnp/bin — no automake/aclocal —
        # and the hand-installed automake under $HOME/.local is invisible to the
        # CI user (ENOENT, CI build #80205).  Pull automake in as tool_requires
        # (published as automake/1.18; same approach as abiword-plugin-clarisworks).
        # configure.ac has no LT_INIT, so libtool/libtoolize is not needed.
        # tool_requires resolve with the *build* profile, so conan create must
        # pass both -pr:h and -pr:b (CI build_and_test.sh does).
        self.tool_requires("automake/1.18")
        # autom4te (from the image's autoconf suite) shells out to `m4`; on a
        # worker without a usable system m4 the bootstrap aborts with
        # "need GNU m4 1.4 or later" (CI build #85406).  The published m4
        # package exports M4=<pkg>/bin/m4 via its buildenv, which autom4te
        # honours ($ENV{M4} in autom4te), so the bootstrap no longer depends
        # on the worker's system m4.
        self.tool_requires("m4/1.4.19")

    def generate(self):
        _prepare_autotools_env()
        # VirtualBuildEnv: put the automake bin dir on the conanbuild PATH and
        # export ACLOCAL/AUTOMAKE/ACLOCAL_PATH/PERL5LIB defined by the automake
        # package — without them `perl .aclocal-real` cannot find its modules.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # 1. autotools bootstrap (aclocal.m4 -> configure -> Makefile.in)
        self._bootstrap_configure()

        # 1b. E011 (HMDFS): harden the freshly generated configure (and any
        #     pre-existing config.status) BEFORE configure runs — configure
        #     embeds the scratch-dir block verbatim into the config.status it
        #     generates, so patching only the generated file would be too
        #     late on a fresh tree (CI #88833).
        self._harden_scratch_machinery(
            os.path.join(src, "configure"),
            os.path.join(src, "config.status"))

        # 2. configure, driven through the shell (no execve of the script)
        prefix = self.package_folder
        self._run_logged(
            f'sh "{os.path.join(src, "configure")}" '
            f'--prefix={prefix} --bindir={prefix}/bin --sbindir={prefix}/bin '
            f'--libdir={prefix}/lib --includedir={prefix}/include --datarootdir={prefix}/share',
            os.path.join(self.build_folder, "configure.log"),
            cwd=src, attempts=2)

        # 3. Build xmlif (the only C program) directly with clang.  The tarball
        #    ships the flex-generated xmlif/xmlif.c, so no lexer is needed.
        #    The compiler output is redirected into a log file and echoed back
        #    on failure: in the agent sandbox a compiler process that inherits
        #    conan's stdout works only when that stdout is a terminal — with
        #    the piped stdout CI uses (`conan create ... | tee`) it is killed
        #    silently (exit 1, no output).  configure's own compiler probes are
        #    unaffected for the same reason (they write to config.log files).
        c_src = os.path.join(src, "xmlif", "xmlif.c")
        obj = os.path.join(self.build_folder, "xmlif", "xmlif.o")
        bin_out = os.path.join(self.build_folder, "xmlif", "xmlif")
        os.makedirs(os.path.join(self.build_folder, "xmlif"), exist_ok=True)
        for cmd, log_name in ((f"clang -DHAVE_CONFIG_H -I{src} -DNDEBUG -O3 -c -o {obj} {c_src}",
                               "clang-compile.log"),
                              (f"clang -o {bin_out} {obj}", "clang-link.log")):
            self._run_logged(cmd, os.path.join(self.build_folder, "xmlif", log_name),
                             attempts=2)

        # 4. Install xmlto script + xmlif binary + format data to package folder
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        gen_xmlto = os.path.join(src, "xmlto")
        # Fix shebang for OHOS: replace /data/service/hnp/bin/bash with /usr/bin/env bash
        # Also ensure executable permission
        with open(gen_xmlto, 'r') as f:
            content = f.read()
        content = content.replace('#!/data/service/hnp/bin/bash', '#!/usr/bin/env bash')
        pkg_xmlto = os.path.join(self.package_folder, "bin", "xmlto")
        with open(pkg_xmlto, 'w') as f:
            f.write(content)
        # Copy mode and ensure executable
        shutil.copymode(gen_xmlto, pkg_xmlto)
        os.chmod(pkg_xmlto, 0o755)
        shutil.copy2(bin_out, os.path.join(self.package_folder, "bin", "xmlif"))
        xmlto_share = os.path.join(self.package_folder, "share", "xmlto")
        os.makedirs(xmlto_share, exist_ok=True)
        shutil.copy2(os.path.join(src, "xmlto.mak"), xmlto_share)
        for d in os.listdir(os.path.join(src, "format")):
            src_d = os.path.join(src, "format", d)
            dst_d = os.path.join(xmlto_share, "format", d)
            if os.path.isdir(src_d):
                shutil.copytree(src_d, dst_d)

    def _ohos_env_prefix(self, path_prepend="", extra=""):
        """Env prefix for the bootstrap / configure / compile runs.

        * PATH: real hnp/toybox tools ahead of the agent sandbox shims
          (safe-bin/rm has a `#!/bin/bash` shebang that does not exist here).
        * SHELL/CONFIG_SHELL: conan's build env exports the sandbox bash, which
          configure would record; force /bin/sh instead.
        """
        path = "/data/service/hnp/bin:/system/bin:/bin:$PATH"
        if path_prepend:
            path = f"{path_prepend}:{path}"
        out = f'PATH="{path}" SHELL="/bin/sh" CONFIG_SHELL="/bin/sh"'
        if extra:
            out += f" {extra}"
        return out

    def _run_logged(self, cmd, log, cwd=None, prefix=None, attempts=3, delay=5.0):
        """Run cmd with its output redirected into `log`, retrying transient
        failures.

        * The redirection matters: a step whose *grandchild* keeps conan's
          stdout pipe open hangs `conan create` until the CI timeout (3600 s
          burned on CI build #85406 after a bootstrap failure).  With the
          redirect, conan's pipe reaches EOF as soon as the direct child
          exits, so failures are fast and the captured log is echoed back.
        * Retries absorb transient worker conditions such as fork exhaustion
          (`sh: can't fork - try again`, which autom4te then misreports as
          "need GNU m4 1.4 or later").
        """
        if prefix is None:
            prefix = self._ohos_env_prefix()
        for attempt in range(1, attempts + 1):
            try:
                self.run(f'{prefix} sh -c {shlex.quote(f"{cmd} > {log} 2>&1")}', cwd=cwd)
                return
            except ConanException:
                if attempt == attempts:
                    try:
                        with open(log, "r", errors="replace") as fh:
                            self.output.error(fh.read())
                    except OSError:
                        pass
                    raise
                self.output.warning(
                    f"step failed (attempt {attempt}/{attempts}), retrying in {delay}s: {cmd.split()[0]}")
                time.sleep(delay)

    def _build_tool_pkg(self, name):
        """Locate a tool_requires dependency in the build graph."""
        for require, dep in self.dependencies.build.items():
            if require.ref and require.ref.name == name:
                return dep
        raise ConanException(f"tool_requires {name} not found in the build graph")

    def _bootstrap_configure(self):
        """Generate aclocal.m4 / configure / Makefile.in from the pristine tree.

        OHOS forbids execve of scripts living on HMDFS inside conan's build
        tree (EACCES/exit 13, or an unfinishable hang on a wedged worker), so
        neither `autoreconf` (which execve()'s $ACLOCAL) nor the packaged `sh`
        wrapper (which execve()'s the embedded .aclocal-real) can be used.  The
        automake Perl scripts are invoked through the `perl` binary instead;
        the acdir/libdir arguments replicate what the packaged wrappers would
        have passed.
        """
        source = self.source_folder
        if os.path.isfile(os.path.join(source, "configure")):
            return
        pkg = self._build_tool_pkg("automake").package_folder
        bin_dir = os.path.join(pkg, "bin")
        share_dir = os.path.join(pkg, "share")
        # m4 from the tool package: autom4te honours $M4 (autom4te.in:
        # `my $m4 = $ENV{"M4"} || 'm4'`), so the bootstrap does not depend on
        # the worker's system m4 (CI build #85406).
        m4_bin = os.path.join(self._build_tool_pkg("m4").package_folder, "bin")
        prefix = self._ohos_env_prefix(path_prepend=m4_bin, extra=f'M4="{m4_bin}/m4"')
        self.output.info(f"Bootstrapping autotools: automake pkg={pkg} m4 bin={m4_bin}")
        # 1. aclocal.m4 (automake's own macros)
        self._run_logged(
            f'perl "{bin_dir}/.aclocal-real" '
            f'--automake-acdir="{share_dir}/aclocal-1.18" '
            f'--system-acdir="{share_dir}/aclocal" --force',
            os.path.join(self.build_folder, "bootstrap-aclocal.log"),
            cwd=source, prefix=prefix)
        # 2. configure (autoconf from the image's autoconf suite; its autom4te
        #    child inherits M4 -> the packaged m4)
        self._run_logged("autoconf -o configure configure.ac",
                         os.path.join(self.build_folder, "bootstrap-autoconf.log"),
                         cwd=source, prefix=prefix)
        # 3. Makefile.in + aux scripts (install-sh/missing/compile/depcomp)
        self._run_logged(
            f'perl "{bin_dir}/.automake-real" '
            f'--libdir="{share_dir}/automake-1.18" '
            f"--add-missing --copy --foreign",
            os.path.join(self.build_folder, "bootstrap-automake.log"),
            cwd=source, prefix=prefix)
        if not os.path.isfile(os.path.join(source, "configure")):
            raise ConanException("autotools bootstrap did not produce configure")

    def _harden_scratch_machinery(self, *paths):
        """E011 (HMDFS): make autoconf's scratch dir provably writable.

        `config.status` creates its scratch directory with
        `(umask 077 && mktemp -d "./confXXXXXX")` and then writes
        `subs1.awk` into it.  On the CI worker (HMDFS uid-domain mapping,
        mktemp forces mode 0700 independent of umask) the creating process
        cannot write into that directory, so config.status aborts with

            ./config.status[765]: can't create ./confXXXXXX/subs1.awk:
            Permission denied
            config.status: error: could not setup config files machinery

        and configure exits 1 (CI #88833, PR #15135).  Since this recipe
        bootstraps its own configure, the fix is applied to the generated
        file right after `autoconf` produced it (and to any pre-existing
        config.status): rewrite `umask 077` -> `umask 002` (covers both the
        mktemp block and the `./conf$$-$RANDOM` fallback) and insert a
        probe + chmod + fallback block after `ac_tmp=$tmp` — probe with the
        exact operation that fails, `chmod 0777` retry, then fall back to a
        dedicated directory under the conan build folder (never the cwd:
        the exit trap `rm -fr "$ac_tmp"` would then delete the tree).  The
        probe error is echoed to stderr so the CI log carries the errno
        either way.  Idempotent: a second run finds `_bihe011_err=` already
        present and only rewrites the umask.
        """
        build_folder = self.build_folder or ""
        block = _SCRATCH_HARDEN_TMPL.replace("@BUILD_FOLDER@", build_folder)
        for path in paths:
            try:
                if not os.path.isfile(path):
                    continue
                with open(path, "r", errors="replace") as fh:
                    text = fh.read()
                if "ac_tmp=$tmp" not in text:
                    continue
                mode = os.stat(path).st_mode & 0o7777
                new_text = text.replace("umask 077", "umask 002")
                if "_bihe011_err=" not in new_text:
                    new_text = new_text.replace("ac_tmp=$tmp", block, 1)
                with open(path, "w") as fh:
                    fh.write(new_text)
                os.chmod(path, mode)
                self.output.info("E011: hardened scratch-dir block in %s" % path)
            except OSError as exc:
                self.output.warning(
                    "E011: cannot patch scratch-dir block in %s: %s" % (path, exc))

    def package(self):
        # Package is already assembled in build() to avoid safe-bin rm trap during make install
        pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

#!/usr/bin/env python3
"""Conan recipe for nfdump 1.7.6 on HarmonyOS PC (OHOS / musl, clang 15).

nfdump bundles everything it needs: the two internal libraries
(libnffile, libnfdump) and minilzo. There are no external requirements.

OHOS adaptations (all of them live in patches/, no platform define is used):
  * configure.ac gains a feature probe for the `_res` global resolver state.
    glibc exports it, musl libc (used by OpenHarmony) does not; the probe
    turns the difference into HAVE_RES_GLOBAL instead of a platform macro.
  * src/libnfdump/filter/ipconv.c and src/libnffile/conf/nfconf.c are
    guarded by that macro, so the sources build against musl while keeping
    the original behaviour on glibc.
"""
import glob
import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Upstream ships these four entries as symlinks inside the release tarball.
# Conan copies the source tree into the build folder with symlinks preserved
# (os.symlink), which fails with EACCES on FUSE backed caches; materialising
# them keeps the recipe independent of the underlying filesystem.
_UPSTREAM_SYMLINKS = ("COPYING", "NEWS", "README", "bootstrap")

# The OHOS CI builders run several package builds concurrently on one device
# whose conan cache lives on a distributed (HMDFS) filesystem. Two unrelated
# host-side problems have been observed in the CI logs:
#   * fork() returning EAGAIN inside the first perl subprocess aclocal
#     spawns ("aclocal[N]: can't fork - try again") when the device process
#     budget is exhausted by concurrent jobs. This is transient, so the
#     fragile host-tool invocations are retried with a pause.
#   * config.status dying with "subs1.awk: Permission denied": autoconf >= 2.71
#     hands its scratch directory out via `mktemp -d` (mode 0700) and the
#     HMDFS permission check refuses writes into freshly created owner-only
#     directories for the worker uid - the failure is deterministic there
#     (automake writes into a fresh 0755 m4/ directory without problems at
#     the same time). Handled by the mktemp wrapper installed in generate().
#
# The EAGAIN episodes can outlast a short retry loop: CI build #93623 failed
# all 5 attempts spaced 15s apart (~75s window) and even the CI knowledge
# check script, which runs before the recipe, hit "fork: retry" in the same
# run. Space the retries 30s apart over 10 attempts (~5 minutes) so a
# multi-minute fork storm no longer consumes the whole budget.
_TRANSIENT_ATTEMPTS = 10
_TRANSIENT_RETRY_WAIT = 30

# autoconf >= 2.71 builds config.status with a scratch directory created by
#   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
# The literal is embedded twice in the generated configure script: once for
# configure itself and once inside the heredoc that configure later writes
# out as config.status. On the OHOS builders (HMDFS-backed conan cache)
# writing into such a freshly created owner-only directory fails with
# "Permission denied" even for the owning user, which killed every CI
# configure attempt with
#   ./config.status: line 815: ./confXXXXXX/subs1.awk: Permission denied
# while automake could write into a fresh 0755 m4/ directory just fine.
# CI build #95593 additionally showed the PATH-based mktemp wrapper (see
# _install_mktemp_shim) does not defuse the failure there, so the recipe
# rewrites the snippet at its source after autoreconf: the scratch directory
# is created world-writable from birth with a plain `mkdir` under umask 000,
# which matches the evidence (fresh 0755 dirs are writable) and depends
# neither on PATH resolution nor on chmod being honoured by HMDFS.
_TMPDIR_SNIPPET_OLD = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
_TMPDIR_SNIPPET_NEW = ('tmp=`(umask 000 && d="./conf$$-$RANDOM" '
                       '&& mkdir "$d" && echo "$d") 2>/dev/null`')


def _prepare_autotools_env():
    """Point autotools at the tools that actually exist in this environment.

    The automake/aclocal wrappers installed on the build host hardcode
    absolute paths for autoconf/autom4te/sed that are not present here;
    exporting the real locations keeps autoreconf working without patching
    the host installation (same helper as the abiword-plugin-* recipes).
    """
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _materialize_symlinks(root):
    """Replace the symlinks listed in _UPSTREAM_SYMLINKS by regular files."""
    for name in _UPSTREAM_SYMLINKS:
        path = os.path.join(root, name)
        if not os.path.islink(path):
            continue
        with open(path, "rb") as handle:
            data = handle.read()
        os.unlink(path)
        with open(path, "wb") as handle:
            handle.write(data)
        os.chmod(path, 0o644)


class NfdumpConan(ConanFile):
    name = "nfdump"
    version = "1.7.6"
    description = "nfdump - netflow dump and analysis tools"
    license = "BSD-2-Clause"
    homepage = "https://github.com/phaag/nfdump"
    url = "https://github.com/phaag/nfdump"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The optional compression backends configure probes via
        # --with-bz2path / --with-lz4path / --with-zstdpath. Enabling them is
        # not only a feature gain: the upstream test suite only reaches its
        # full 7-test set when HAVE_BZIP2 and HAVE_ZSTD hold (runbz2.sh and
        # runzstd.sh join `make check` conditionally, see src/test/Makefile.am).
        # lzo needs no external library (bundled minilzo in
        # src/libnffile/compress/), so runlzo.sh runs unconditionally.
        self.requires("bzip2/1.0.8.2")
        self.requires("lz4/1.10.0.3")
        self.requires("zstd/1.5.7.1")

    def build_requirements(self):
        # The release tarball is a git archive without a generated configure
        # script, so build() has to run `autoreconf -fi`. The build host only
        # ships the autoconf family, therefore automake and libtool are
        # pulled in as tool_requires (same approach as abiword-plugin-*).
        # pkgconf is needed because configure.ac calls PKG_CHECK_MODULES and
        # aclocal can only expand it when the pkg.m4 it ships is reachable.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)
        # nfdump has to be built in the source directory: its Makefile.am files
        # invoke helper scripts through relative paths (src/libnffile/Makefile.am
        # generates vcs_track.h with `./gen_version.sh`), which cannot work in an
        # out-of-source tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        _materialize_symlinks(self.source_folder)

    def generate(self):
        _prepare_autotools_env()

        tc = AutotoolsToolchain(self)
        # Optional features which need third party libraries or platform
        # services that are not part of the OHOS baseline.
        tc.configure_args.append("--disable-influxdb")
        tc.configure_args.append("--disable-nfprofile")
        tc.configure_args.append("--disable-nftrack")
        tc.configure_args.append("--disable-nfpcapd")
        tc.configure_args.append("--disable-sflow")
        tc.configure_args.append("--disable-readpcap")
        tc.configure_args.append("--disable-ftconv")
        # config.guess cannot identify HarmonyOS (uname reports "HarmonyOS"),
        # and the generated configure script is the only place that probes it.
        # Passing the triplet explicitly keeps config.guess out of the way.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")

        # PKG_CHECK_MODULES lives in the pkg.m4 shipped by pkgconf; aclocal
        # only finds it when its share/aclocal directory is on ACLOCAL_PATH.
        pkgconf = self.dependencies.build.get("pkgconf")
        if pkgconf is not None and pkgconf.package_folder:
            aclocal_dir = os.path.join(pkgconf.package_folder, "share", "aclocal")
            if os.path.isdir(aclocal_dir):
                self.buildenv.append_path("ACLOCAL_PATH", aclocal_dir)

        # Hand the optional compression libraries to configure through its
        # own --with-*path probes (each appends -I<root>/include and
        # -L<root>/lib itself). This unlocks HAVE_BZIP2 / HAVE_ZSTD / HAVE_LZ4
        # and with them the full 7-test upstream suite (see requirements()).
        for pkg, arg in (("bzip2", "--with-bz2path"),
                         ("lz4", "--with-lz4path"),
                         ("zstd", "--with-zstdpath")):
            dep = self.dependencies.host.get(pkg)
            if dep is None or not dep.package_folder:
                self.output.warning(
                    "{} not resolved; the {} probe stays disabled and "
                    "run*.sh coverage shrinks accordingly".format(pkg, arg))
                continue
            include_dir = os.path.join(dep.package_folder, "include")
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not (os.path.isdir(include_dir) and os.path.isdir(lib_dir)):
                self.output.warning(
                    "{} package layout lacks include/ or lib/ under {}; "
                    "the {} probe stays disabled".format(
                        pkg, dep.package_folder, arg))
                continue
            tc.configure_args.append("{}={}".format(arg, dep.package_folder))
            # configure links every later conftest against the libraries the
            # probes just found (they append -l<name> to LIBS). zstd ships a
            # shared libzstd.so, so those conftests - and later the make
            # check binaries - need the package lib directory on
            # LD_LIBRARY_PATH at run time or configure dies with
            # "cannot compute sizeof (size_t)".
            self.buildenv.append_path("LD_LIBRARY_PATH", lib_dir)

        # Keep config.status working on the HMDFS backed conan cache of the
        # OHOS builders (see _install_mktemp_shim for the details).
        shim_dir = self._install_mktemp_shim()
        if shim_dir:
            self.buildenv.prepend_path("PATH", shim_dir)

        # NOTE on environment injection: VirtualBuildEnv aggregates the
        # profile buildenv (conanfile.buildenv, highest priority) plus the
        # buildenv_info/runenv_info of the DEPENDENCIES - but NOT this
        # recipe's own conanfile.buildenv_info. Entries written to
        # self.buildenv_info never reach the conanbuild script of this very
        # package (that silently disabled the mktemp wrapper and the
        # ACLOCAL_PATH/LD_LIBRARY_PATH entries in earlier CI builds).
        # Mutating conanfile.buildenv above is the working mechanism.

        # Generated last: the tool_requires bin/ directories have to end up on
        # PATH (aclocal/automake/libtoolize come from them), the mktemp wrapper
        # has to shadow the host mktemp, and ACLOCAL_PATH has to be part of the
        # build environment file.
        VirtualBuildEnv(self).generate()
        tc.generate()

    def _install_mktemp_shim(self):
        """Install a mktemp wrapper for config.status's scratch directory.

        autoconf >= 2.71 generated config.status scripts create their scratch
        directory with `(umask 077 && mktemp -d "./confXXXXXX")` and then
        write subs1.awk / subs.awk into it. On the OHOS builders the conan
        cache lives on HMDFS, whose permission check denies writes into
        freshly created owner-only (0700) directories for the worker uid:
        every configure run dies with
            ./config.status: line N: ./confXXXXXX/subs1.awk: Permission denied
        even though automake writes into a fresh 0755 m4/ directory without
        problems at the same time. The wrapper passes every mktemp call
        through unchanged but widens directories to 0777, which keeps
        config.status working on HMDFS and changes nothing on other
        filesystems. If the wrapper cannot be created (no mktemp on the
        recipe PATH) the build falls back to today's behaviour.
        """
        real_mktemp = shutil.which("mktemp")
        if not real_mktemp:
            return None
        shim_dir = os.path.join(self.build_folder, "conan-shims")
        os.makedirs(shim_dir, exist_ok=True)
        script = os.path.join(shim_dir, "mktemp")
        with open(script, "w") as handle:
            handle.write(
                "#!/bin/sh\n"
                "# mktemp wrapper installed by the nfdump recipe. config.status\n"
                "# creates its scratch directory with `mktemp -d` (mode 0700) and\n"
                "# the HMDFS backed conan cache of the OHOS builders refuses to\n"
                "# write into freshly created owner-only directories. Hand such\n"
                "# directories out with mode 0777 instead; everything else passes\n"
                "# through unchanged.\n"
                'real="%s"\n'
                'out=$("$real" "$@") || exit $?\n'
                "want_dir=\n"
                'for arg in "$@"; do\n'
                '    case "$arg" in -d|--directory) want_dir=1 ;; esac\n'
                "done\n"
                "if [ -n \"$want_dir\" ]; then\n"
                '    for path in $out; do chmod 0777 "$path" 2>/dev/null; done\n'
                "fi\n"
                "printf '%%s\\n' \"$out\"\n"
                % real_mktemp
            )
        os.chmod(script, 0o755)
        return shim_dir

    def build(self):
        # generate() sets os.environ only for this process, and self.run()
        # with env="conanbuild" starts a fresh shell, so re-apply it here.
        _prepare_autotools_env()
        apply_conandata_patches(self)
        self._autoreconf_with_retry()
        self._widen_config_status_tmpdir()
        self._probe_scratch_dir()
        autotools = Autotools(self)
        self._configure_with_retry(autotools)
        self._make_with_retry(autotools)

    def _widen_config_status_tmpdir(self):
        """Rewrite the mktemp-based scratch dir creation in the generated
        configure script (see _TMPDIR_SNIPPET_* for the full rationale).

        The replacement covers both embedded copies, so the config.status
        that configure writes out inherits the world-writable variant. If a
        future autoconf stops matching the literal, a loud warning keeps the
        mktemp wrapper as the remaining guard instead of failing here.
        """
        configure = os.path.join(self.source_folder, "configure")
        with open(configure) as handle:
            text = handle.read()
        count = text.count(_TMPDIR_SNIPPET_OLD)
        if count == 0:
            self.output.warning(
                "mktemp-based config.status tmpdir snippet not found in the "
                "generated configure; the mktemp wrapper remains the only "
                "guard against the HMDFS 0700-dir write denial")
            return
        text = text.replace(_TMPDIR_SNIPPET_OLD, _TMPDIR_SNIPPET_NEW)
        with open(configure, "w") as handle:
            handle.write(text)
        self.output.info(
            "widened {} config.status tmpdir snippet(s) to world-writable "
            "(HMDFS 0700-dir workaround)".format(count))

    def _probe_scratch_dir(self):
        """Log evidence about world-writable scratch dirs on the build host.

        CI build #95593 could not tell apart "the mktemp wrapper was not on
        PATH" from "HMDFS even denies the wrapper's chmod". This probe
        creates a fresh 0777 directory, writes into it and prints its mode;
        its output lands in the CI log either way and settles the question
        before configure even runs.
        """
        probe = ('(umask 000 && d=conanscratchprobe.$$ && mkdir "$d" '
                 '&& : > "$d/probe" && ls -lnd "$d" && rm -rf "$d") '
                 "|| echo '[nfdump] WARNING: world-writable scratch dir "
                 "probe FAILED on this filesystem'")
        self.run(probe, cwd=self.build_folder, env="conanbuild")

    def _make_with_retry(self, autotools):
        # The build runs with -j1 (see below), so a retried make resumes the
        # incremental build instead of starting over; the retry only pays the
        # pause, not a second full compile.
        for attempt in range(1, _TRANSIENT_ATTEMPTS + 1):
            try:
                # -j1: the jobserver fifo is not usable on the HMDFS backed
                # build directories used by the OHOS builders.
                autotools.make(args=["-j1"])
                return
            except ConanException as err:
                if attempt == _TRANSIENT_ATTEMPTS:
                    raise
                self.output.warning(
                    "make attempt {}/{} failed ({}); the incremental build "
                    "resumes after retrying in {}s".format(
                        attempt, _TRANSIENT_ATTEMPTS, err,
                        _TRANSIENT_RETRY_WAIT))
                time.sleep(_TRANSIENT_RETRY_WAIT)

    def _autoreconf_with_retry(self):
        for attempt in range(1, _TRANSIENT_ATTEMPTS + 1):
            try:
                self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
                return
            except ConanException as err:
                if attempt == _TRANSIENT_ATTEMPTS:
                    raise
                self.output.warning(
                    "autoreconf attempt {}/{} hit a transient host error ({}); "
                    "retrying in {}s".format(attempt, _TRANSIENT_ATTEMPTS, err,
                                             _TRANSIENT_RETRY_WAIT))
                time.sleep(_TRANSIENT_RETRY_WAIT)

    def _configure_with_retry(self, autotools):
        for attempt in range(1, _TRANSIENT_ATTEMPTS + 1):
            try:
                autotools.configure()
                return
            except ConanException as err:
                if attempt == _TRANSIENT_ATTEMPTS:
                    raise
                self.output.warning(
                    "configure attempt {}/{} hit a transient host error ({}); "
                    "retrying in {}s".format(attempt, _TRANSIENT_ATTEMPTS, err,
                                             _TRANSIENT_RETRY_WAIT))
                # A dying config.status leaves its scratch directory behind
                # (the mktemp variant `confXXXXXX` or the mkdir variant
                # `conf<PID>-<RANDOM>`) and a partially written config.status;
                # clear them so the retry starts from a clean slate.
                for scratch in glob.glob(os.path.join(self.build_folder,
                                                      "conf[0-9]*")):
                    shutil.rmtree(scratch, ignore_errors=True)
                leftover = os.path.join(self.build_folder, "config.status")
                if os.path.isfile(leftover):
                    os.remove(leftover)
                time.sleep(_TRANSIENT_RETRY_WAIT)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "BSD-license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The two internal libraries, in dependency order: libnfdump calls into
        # libnffile, so it has to be listed first.
        self.cpp_info.libs = ["nfdump", "nffile"]

        # nfdump keeps its headers private - `make install` only populates bin/,
        # lib/, etc/ and share/man, there is no include/ directory. Resetting the
        # list keeps the generated CMake config from advertising
        # <package_folder>/include, which does not exist and makes every
        # consumer fail at configure time.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]

        # The package installs the nfdump/nfcapd/nfreplay/nfanon/nfexpire
        # executables (see the software level commands.json).
        self.cpp_info.bindirs = ["bin"]

        self.cpp_info.system_libs = ["m", "pthread"]

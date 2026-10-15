#!/usr/bin/env python3
"""Conan recipe for smalt 0.7.6 - SMALT sequence aligner on HarmonyOS PC.

SMALT (Sequence Mapping and Alignment Tool, Hannes Ponstingl, Wellcome Trust
Sanger Institute, GPL-3) maps DNA sequencing reads against a reference genome:
it builds a hash index of k-mer words sampled along the reference, finds
candidate segments from seed matches and aligns them with Smith-Waterman
dynamic programming.  Reads may be single or paired, FASTA or FASTQ (plain or
gzipped); output is SAM or SMALT's own tabular format.  Upstream builds with
autotools and installs ten executables: ``smalt`` plus nine read utilities
(``simread``, ``fetchseq``, ``splitreads``, ``mixreads``, ``readstats``,
``splitmates``, ``trunkreads``, ``basqcol``, ``simqual``).

HarmonyOS PC (aarch64) adaptation
    * The tarball ships GNU config.guess/config.sub from 2009-11-20.  On the
      worker ``uname -s`` reports HarmonyOS, which that config.guess cannot
      match, so it dies with "unable to guess system type" before configure
      does anything (knowledge E007/E205).  Its config.sub also rejects the
      canonical ``aarch64-unknown-linux-ohos`` triplet - ``linux-ohos`` is
      missing from the KERNEL-OS list, and even with that fixed the trailing
      ``-linux*)`` branch would rewrite it into the bogus ``-linux-gnu-ohos``
      (E072/E122/E268).  patches/0001 and patches/0002 teach both scripts the
      platform, which is the sanctioned route: no ``--build``/``--host``
      forgery.  Neither patch introduces a platform macro (R8/PF5).
    * patches/0003 relaxes the ``umask 077`` with which config.status creates
      its temporary directory; on HMDFS that mkdir fails (E002/E011, same fix
      as rsyslog 8.2404.0).
    * zlib is required, not optional, for the upstream test suite: the
      distributed drivers feed gzipped references (``cigar_ref.fa.gz``,
      ``genome_1.fa.gz``) straight to ``smalt index``, so ``HAVE_ZLIB`` has to
      be on.  ``zlib/1.3.1`` is published in the registry with a prebuilt OHOS
      aarch64 binary and is static-only in this ecosystem, so the packaged
      binaries keep ``libc.so`` as their only runtime dependency and nothing
      named ``libz`` is dropped into the OHOS ``/lib`` (R26).  Dependency
      search paths are injected as plain ``-I``/``-L``; AutotoolsDeps is
      deliberately not used, because it pushes the whole closure into LIBS and
      autoconf's very first "cannot run C compiled programs" probe then links
      against libraries the conftest cannot load (E467/E505).
    * ``--with-bambamc=no``: BAM input/output is an optional upstream feature
      gated on German Tischler's C++ bambamc library.  Upstream 0.7.6 never
      wires up a C++ link for the main program (``AC_PROG_CXX`` is commented
      out in configure.ac, ``smalt_LDADD`` carries no C++ runtime, and the
      ``dummy.cxx`` C++-link helpers in test/Makefile.am are commented out),
      so this recipe builds the C-only configuration documented in upstream's
      own README.  notes.md records what enabling BAM would take.
    * No SSE2: ``AC_CHECK_HEADERS([emmintrin.h])`` fails for an aarch64
      target, so ``WITH_SIMD`` stays off and the portable C alignment path is
      compiled (verified with the OHOS SDK clang: the header errors out with
      "only meant to be used on x86 and x64").
    * In-tree build.  ``test/Makefile.am`` hardcodes ``-I../src/ -I../test``,
      which only resolves when the build directory *is* the source directory;
      an out-of-source VPATH build fails with ``'elib.h' file not found``
      while compiling the test programs.  Hence ``self.folders.build = "."``
      (same idiom as redis/recode/runit in this repository).
    * ``libsgm.a`` embeds ``libseq.a`` as an archive member (upstream sets
      ``libsgm_a_LIBADD = libseq.a``).  OHOS lld accepts that with a warning
      and links correctly; only Apple's ld64 refuses, which affects a
      macOS-native convenience build, not the OHOS target.
    * Source transport.  The official tarball is 72,290,533 bytes and the CI
      worker egress cuts SourceForge transfers mid-stream, so ``source()``
      fetches it as parallel HTTP ranges and keeps ``get()`` as the fallback.
      See ``_ranged_source()`` for the build-number evidence and why neither
      per-URL retry nor mirror rotation can converge on its own.

Upstream tests (layer 1, executed inside build() on the HarmonyOS worker)
    ``make check`` runs the six distributed Python drivers registered in
    ``TESTS``.  They are 2013-vintage Python 2, so patches/0004-0011 port them
    to Python 3 (syntax and gzip byte/text mode only - no assertion, expected
    value or test logic is touched; Debian carries an equivalent 2to3.patch for
    the same upstream release).  ``PYTHON`` is handed to configure from
    ``sys.executable`` because upstream's ``AM_PATH_PYTHON([2.6])`` only looks
    for ``python``/``python2`` and would otherwise register zero tests.
    The two distributed C test programs (``sequenceReverseComplement_test`` in
    check_PROGRAMS, ``diffstr_test`` in EXTRA_PROGRAMS) contain no assertions
    of their own - they are usage-driven harnesses - so ``upstream_c_tests.py``
    drives them over real inputs and asserts their measured upstream output.

Artifacts: ``bin/`` (10 executables) + ``share/`` (the test drivers and
``SAM.py``, installed by upstream's own ``make install``).  The software-level
``commands.json`` declares the CLI (R38).  License: GPL-3.0-or-later.
"""
import concurrent.futures
import hashlib
import os
import re
import shutil
import stat
import sys
import tempfile
import time
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# The six drivers automake registers in TESTS once a Python >= 2.6 interpreter
# is supplied (measured: `make check` reports "TOTAL: 6" and six PASS lines).
EXPECTED_UPSTREAM_DRIVERS = 6
# Independent checks upstream_c_tests.py performs over the two distributed C
# test programs (see that file for the per-check list).
EXPECTED_UPSTREAM_C_CHECKS = 6
# Source transport tuning for _ranged_source(): the official tarball is fetched
# as parallel HTTP ranges so that a mid-transfer cut costs one chunk instead of
# the whole 72 MB (CI evidence in that method's docstring).
SOURCE_ARCHIVE = "smalt-0.7.6.tar.gz"
RANGE_CHUNK = 4 * 1024 * 1024
RANGE_WORKERS = 8
# Attempts per range are cheap because each one resumes from the bytes already
# on disk, so the budget only has to cover "cut many times", not "cut once".
RANGE_ATTEMPTS = 40
# Bail out early only when attempts stop making forward progress altogether.
RANGE_STALL_LIMIT = 5


class SmaltConan(ConanFile):
    name = "smalt"
    version = "0.7.6"
    description = (
        "SMALT - Sequence Mapping and Alignment Tool: hash-index based DNA "
        "read aligner (FASTA/FASTQ, plain or gzipped, single or paired reads) "
        "with SAM output, plus read simulation and inspection utilities"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/smalt/"
    url = "https://sourceforge.net/projects/smalt/"
    topics = ("bioinformatics", "genomics", "sequence-alignment", "sam", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*", "upstream_c_tests.py"

    # Method order follows the project convention (code-style.md §3):
    # export_sources -> requirements -> layout -> source -> generate -> build
    # -> package -> package_info.
    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # filio.c reads gzipped FASTA/FASTQ through zlib when HAVE_ZLIB is set
        # (src/Makefile.am: smalt_LDADD += -lz).  zlib is static in this
        # ecosystem, so nothing named libz reaches the OHOS /lib (R26).
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)
        # Upstream's test/Makefile.am hardcodes -I../src/ -I../test, so the
        # build has to happen in the source tree (see the module docstring).
        self.folders.build = "."

    def source(self):
        sources = self.conan_data["sources"]
        urls = sources["url"]
        if not isinstance(urls, (list, tuple)):
            urls = [urls]
        try:
            self._ranged_source(list(urls), sources["sha256"])
        except ConanException as error:
            # Ordinary Conan download stays as the second opinion: it is the
            # path that produced the two green CI builds (#65959 / CI-030 and
            # #66579 / CI-001) and every local `conan create`.
            self.output.warning(
                "smalt: parallel-range download unavailable (%s); falling "
                "back to conan.tools.files.get()" % str(error)[-160:])
            get(self, strip_root=True, retry=3, retry_wait=15, **sources)

    # -- helpers ----------------------------------------------------------
    def _can_execute_target(self):
        """True only when binaries built here can actually run on this host.

        On the HarmonyOS worker the build is native, so can_run() is True and
        the upstream suite really executes.  The local OHOS SDK cross build
        (profile ohos-local) sets tools.build.cross_building:can_run=False; the
        extra user.build:flex_bison_native probe is the same belt-and-braces
        check used by ylva 1.7 / libidl2 0.8.14 / secpwgen 1.3, in case that
        conf is ever overridden.
        """
        if not can_run(self):
            return False
        try:
            if bool(self.conf.get("user.build:flex_bison_native", default=False)):
                return False
        except Exception:
            pass
        return True

    def _writable_tmpdir(self):
        """E002: /tmp is read-only erofs on OHOS, so use the build folder."""
        d = os.path.join(self.build_folder, "ohos-tmp")
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            d = self.build_folder
        return d

    def _host_triplet(self):
        """Canonical GNU triplet of the target, e.g. aarch64-unknown-linux-ohos."""
        arch = str(self.settings.get_safe("arch") or "")
        cpu = {"armv8": "aarch64", "armv8.3": "aarch64", "armv7": "arm",
               "x86_64": "x86_64"}.get(arch, "")
        if not cpu:
            return ""
        os_ = str(self.settings.get_safe("os") or "")
        kernel = "linux-ohos" if os_ == "OHOS" else "linux-gnu"
        return "%s-unknown-%s" % (cpu, kernel)

    def _restore_autotools_modes(self):
        """E490: some adaptation paths drop the execute bit from the autotools
        helper scripts, which makes configure fail before compiling starts."""
        names = ("configure", "config.guess", "config.sub", "install-sh",
                 "missing", "depcomp", "compile", "ltmain.sh")
        for name in names:
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            mode = os.stat(path).st_mode
            want = mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            if want != mode:
                os.chmod(path, want)
                self.output.info("E490: restored execute bit on %s" % name)

    def _tail(self, path, limit=6000):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()[-limit:]
        except OSError:
            return "<no log at %s>" % path

    def _find_helper(self, name):
        for folder in (self.source_folder, self.recipe_folder, self.build_folder):
            if not folder:
                continue
            cand = os.path.join(folder, name)
            if os.path.isfile(cand):
                return cand
        raise ConanException("smalt: helper %s was not exported" % name)

    @staticmethod
    def _count_driver_results(output):
        """Count automake's "PASS: <driver>.py" lines (XFAIL/SKIP do not count)."""
        return len(re.findall(r"^PASS:\s+\S+\.py\s*$", output, flags=re.M))

    # -- source transport -------------------------------------------------
    def _ranged_source(self, urls, sha256):
        """Fetch the official tarball as parallel HTTP ranges, then verify it.

        Why this exists (CI evidence, not speculation): the worker egress cuts
        this 72,290,533-byte SourceForge transfer mid-stream.  Builds
        #66867/#66928/#67854/#67875 all died at about 7 MB
        (``IncompleteRead(7098096 bytes read, 65192437 more expected)``) and
        #84948 got 28.8 MB and then 10.1 MB before the whole 3600 s budget was
        gone.  Conan restarts every retry from byte 0, so neither per-URL retry
        nor mirror rotation can converge: the three declared URLs were measured
        to 301/302 to the *same* ``master.dl.sourceforge.net`` balancer, which
        makes the rotation cosmetic, and both of CI's own safety nets are dead
        on the worker: its pre-download step dies with ``[Errno 2] No such file
        or directory`` because no HTTP client binary is on PATH there, and
        ``get_mirrors()`` has no SourceForge branch.  Splitting the file into
        4 MB ranges makes progress monotonic and turns a cut into a cheap
        per-chunk retry.

        This is a transport change only: the bytes still come from the URLs
        declared in conandata.yml, every range is validated against its
        ``Content-Range``, and the declared sha256 still gates exactly what
        gets unpacked.  Same approach as archives/g/gcc-snapshot/20260705;
        Range-resume precedent in archives/b/barvinok/0.41.9.
        """
        total, url = self._probe_range_support(urls)
        ranges = [(index, start, min(start + RANGE_CHUNK - 1, total - 1))
                  for index, start in enumerate(range(0, total, RANGE_CHUNK))]
        archive = os.path.join(self.source_folder, SOURCE_ARCHIVE)
        work_dir = tempfile.mkdtemp(prefix=".smalt-ranges-",
                                    dir=self.source_folder)
        partial = archive + ".partial"
        try:
            self.output.info(
                "smalt: downloading %s (%d bytes) in %d parallel HTTP ranges "
                "from %s" % (SOURCE_ARCHIVE, total, len(ranges),
                             url.split("/")[2]))
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(RANGE_WORKERS, len(ranges))) as executor:
                parts = list(executor.map(
                    lambda item: self._fetch_range(url, item, work_dir),
                    ranges))
            digest = hashlib.sha256()
            written = 0
            with open(partial, "wb") as out:
                for part in parts:
                    with open(part, "rb") as src:
                        while True:
                            block = src.read(1024 * 1024)
                            if not block:
                                break
                            out.write(block)
                            digest.update(block)
                            written += len(block)
            if written != total:
                raise ConanException(
                    "smalt source size mismatch: expected %d, got %d"
                    % (total, written))
            if digest.hexdigest() != sha256:
                raise ConanException(
                    "smalt source sha256 mismatch: expected %s, got %s"
                    % (sha256, digest.hexdigest()))
            os.replace(partial, archive)
            self.output.info(
                "smalt: sources downloaded from %s using parallel ranges, "
                "sha256 verified" % url.split("/")[2])
        finally:
            if os.path.exists(partial):
                os.remove(partial)
            shutil.rmtree(work_dir, ignore_errors=True)
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def _probe_range_support(self, urls):
        """Return ``(total_size, url)`` for the first URL that honours Range.

        A one-byte ranged GET is used rather than HEAD: every declared host was
        measured to answer it with ``206 Partial Content`` and
        ``content-range: bytes 0-0/72290533``, while HEAD is not reliably
        served through the balancer's redirect chain.
        """
        errors = []
        for url in urls:
            try:
                request = urllib.request.Request(url, headers={
                    "Range": "bytes=0-0",
                    "Accept-Encoding": "identity",
                })
                with urllib.request.urlopen(request, timeout=60) as response:
                    status = getattr(response, "status", None)
                    if status != 206:
                        raise ConanException("HTTP %s (no partial content)"
                                             % status)
                    content_range = response.headers.get("Content-Range", "")
                    response.read(1)
                total = int(content_range.rsplit("/", 1)[-1])
                if total <= 0:
                    raise ConanException("bad Content-Range %r" % content_range)
                return total, url
            except Exception as error:
                errors.append("%s: %s" % (url.split("/")[2], error))
        raise ConanException(
            "smalt: no declared source URL supports HTTP Range (%s)"
            % "; ".join(errors))

    def _fetch_range(self, url, item, work_dir):
        """Download one range, resuming inside it; return its part file path.

        A retry resumes from the bytes already on disk rather than restarting
        the range.  That matters because the worker's cuts land at varying
        offsets (7 MB, 10.1 MB and 28.8 MB across the logged builds), so a
        fixed range can be cut repeatedly and still converge as long as every
        attempt keeps whatever it managed to transfer.
        """
        index, start, end = item
        wanted = end - start + 1
        part = os.path.join(work_dir, "part-%04d" % index)
        last_error = None
        stalled = 0
        attempt = 0
        for attempt in range(RANGE_ATTEMPTS):
            before = os.path.getsize(part) if os.path.exists(part) else 0
            if before >= wanted:
                return part
            first = start + before
            try:
                request = urllib.request.Request(url, headers={
                    "Range": "bytes=%d-%d" % (first, end),
                    "Accept-Encoding": "identity",
                })
                with urllib.request.urlopen(request, timeout=180) as response:
                    status = getattr(response, "status", None)
                    if status != 206:
                        raise ConanException("HTTP %s" % status)
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(
                            "bytes %d-%d" % (first, end)):
                        raise ConanException(
                            "range response was %r" % (content_range or
                                                        "<missing>"))
                    remaining = end - first + 1
                    with open(part, "ab" if before else "wb") as output:
                        while remaining:
                            block = response.read(min(1024 * 1024, remaining))
                            if not block:
                                break
                            output.write(block)
                            remaining -= len(block)
                have = os.path.getsize(part)
                if have >= wanted:
                    return part
                raise ConanException(
                    "range ended after %d of %d bytes" % (have, wanted))
            except Exception as error:
                last_error = error
                have = os.path.getsize(part) if os.path.exists(part) else 0
                stalled = stalled + 1 if have <= before else 0
                if stalled >= RANGE_STALL_LIMIT:
                    break
                time.sleep(2)
        raise ConanException(
            "smalt: HTTP range %d-%d failed after %d attempts: %s"
            % (start, end, attempt + 1, last_error))

    # -- conan steps ------------------------------------------------------
    def generate(self):
        os.umask(0)
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-bambamc=no")

        # E467/E505: -I/-L only, never LIBS, never a global LD_LIBRARY_PATH.
        zlib = self.dependencies["zlib"]
        inc = os.path.join(zlib.package_folder, "include")
        lib = os.path.join(zlib.package_folder, "lib")
        tc.configure_args.append("CPPFLAGS=-I%s" % inc)
        tc.configure_args.append("LDFLAGS=-L%s" % lib)

        if self._can_execute_target():
            # AM_PATH_PYTHON([2.6]) only probes python/python2*, so without an
            # explicit PYTHON it sets ':' and registers *zero* tests.
            # sys.executable is the interpreter running conan, so it exists.
            tc.configure_args.append("PYTHON=%s" % (sys.executable or "python3"))
        else:
            # Cross building: keep the drivers unregistered and declare the
            # target explicitly so autoconf does not try to execute its conftest
            # binaries on the build machine.  config.sub is patched, so this
            # triplet validates.
            tc.configure_args.append("PYTHON=:")
            triplet = self._host_triplet()
            if triplet:
                tc.configure_args.append("--host=%s" % triplet)

        env = tc.environment()
        tmpdir = self._writable_tmpdir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, tmpdir)
        tc.generate(env=env)

    def build(self):
        # E011/HMDFS: config.status creates its temp dir under the process umask.
        os.umask(0)
        apply_conandata_patches(self)
        self._restore_autotools_modes()

        autotools = Autotools(self)
        autotools.configure()
        # -j1: the generated automake 1.13 rules are not parallel-safe across
        # the three subdirectories, and the tree is small.
        autotools.make(args=["-j1"])

        if self._can_execute_target():
            self._run_upstream_tests()
        else:
            self.output.info(
                "cross building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the %d upstream make check drivers and the %d "
                "C-harness checks execute on the HarmonyOS CI worker instead"
                % (EXPECTED_UPSTREAM_DRIVERS, EXPECTED_UPSTREAM_C_CHECKS))

    def _run_upstream_tests(self):
        """Layer 1: upstream's own suite, run in the build tree."""
        test_dir = os.path.join(self.build_folder, "test")
        python = sys.executable or "python3"

        # (a) the six registered Python drivers, through automake's runner
        check_log = os.path.join(self.build_folder, "upstream-make-check.log")
        rc = self.run('make -j1 check > "%s" 2>&1' % check_log,
                      cwd=self.build_folder, env="conanbuild",
                      ignore_errors=True)
        out = self._tail(check_log)
        self.output.info(out)
        if rc != 0:
            raise ConanException("smalt: upstream `make check` failed (rc=%d)" % rc)
        passed = self._count_driver_results(out)
        if passed != EXPECTED_UPSTREAM_DRIVERS:
            raise ConanException(
                "smalt: expected %d upstream drivers to PASS, counted %d"
                % (EXPECTED_UPSTREAM_DRIVERS, passed))
        self.output.info("smalt: upstream make check %d/%d PASS"
                         % (passed, EXPECTED_UPSTREAM_DRIVERS))

        # (b) the two distributed C test programs.  diffstr_test is an
        # EXTRA_PROGRAMS entry, so it has to be requested explicitly.
        rc = self.run("make -j1 diffstr_test", cwd=test_dir, env="conanbuild",
                      ignore_errors=True)
        if rc != 0:
            raise ConanException("smalt: building upstream diffstr_test failed")

        script = self._find_helper("upstream_c_tests.py")
        workdir = self._writable_tmpdir()
        c_log = os.path.join(self.build_folder, "upstream-c-tests.log")
        rc = self.run('"%s" "%s" --test-dir "%s" --workdir "%s" > "%s" 2>&1'
                      % (python, script, test_dir, workdir, c_log),
                      cwd=test_dir, ignore_errors=True)
        out = self._tail(c_log)
        self.output.info(out)
        m = re.search(r"RESULT: passed=(\d+) failed=(\d+)", out)
        if not m:
            raise ConanException(
                "smalt: upstream C-harness suite printed no RESULT line (rc=%d)" % rc)
        c_passed, c_failed = int(m.group(1)), int(m.group(2))
        if c_failed or c_passed != EXPECTED_UPSTREAM_C_CHECKS:
            raise ConanException(
                "smalt: upstream C harnesses passed=%d failed=%d (expected %d/0)"
                % (c_passed, c_failed, EXPECTED_UPSTREAM_C_CHECKS))
        self.output.info("smalt: upstream C harnesses %d/%d PASS"
                         % (c_passed, EXPECTED_UPSTREAM_C_CHECKS))

    def package(self):
        os.umask(0)
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Application package: nothing to re-export to consumers, but the CLI
        # must be resolvable through PATH for test_package's VirtualRunEnv.
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))

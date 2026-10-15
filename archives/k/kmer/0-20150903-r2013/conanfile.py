#!/usr/bin/env python3
"""Conan recipe for kmer 0-20150903-r2013 -- the k-mer analysis toolkit.

kmer (Celera Genomics / JCVI, Brian Walenz) is a toolkit rather than a single
library.  It ships the k-mer and genome-assembly command line tools (meryl,
leaff, sim4db, snapper2, tapper, seagen, the sim4* polish utilities ...), the
static libraries behind them (libkmer, libmeryl, libseq, libbio, libsim4,
libutil) and the Perl driver scripts.  It is built by its own non-recursive GNU
make build system (Makefile + Make.rules + Make.include), which picks a per-OS
configuration block in configure.sh and writes Make.compilers.

The recipe therefore drives that build system directly: configure.sh is asked
for the OHOS-arm64 target added by patches/0001, make builds the whole tree and
make install stages the result in OHOS-arm64/, which becomes the package.
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, save)
from conan.tools.layout import basic_layout


_SCRATCH_TEST_RUNNER = r"""#!/bin/sh
# Compile and run the upstream scratch tests of kmer.  Their */test/ directories
# have no Make.include, so the shipped non-recursive make never builds them.
#   $1 = source tree      $2 = scratch output directory
set -u
CC="@CC@"
CXX="@CXX@"
INCS="@INCS@"
LIBS="@LIBS@"
WORK="$1"
TMP="$2"
rm -rf "$TMP"
mkdir -p "$TMP"
if command -v timeout >/dev/null 2>&1 ; then TIMEOUT="timeout 120" ; else TIMEOUT="" ; fi

# one small single-record FASTA for the sequence-stream speed test
printf ">one\n" > "$TMP/one.fasta"
i=0
while [ $i -lt 10 ] ; do
  printf "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT" >> "$TMP/one.fasta"
  i=$((i + 1))
done
printf "\n" >> "$TMP/one.fasta"

pass=0
cfail=0
rfail=0
for f in "$WORK"/*/test/*.c "$WORK"/*/test/*.C ; do
  [ -f "$f" ] || continue
  n=`basename "$f"`
  o="$TMP/${n%.*}"
  case "$f" in
    *.c) C="$CC" ;;
    *)   C="$CXX" ;;
  esac
  if $C $INCS "$f" -o "$o" $LIBS -lpthread -lm > "$o.compile.log" 2>&1 ; then
    args=""
    case "$n" in
      test-freeDiskSpace.c)   args="$WORK/README.compiling" ;;
      test-merstream-speed.C) args="$TMP/one.fasta" ;;
    esac
    $TIMEOUT "$o" $args < /dev/null > "$o.run.log" 2>&1
    rc=$?
    if [ $rc -eq 0 ] ; then
      pass=$((pass + 1))
      echo "SCRATCH-PASS         $f"
    else
      rfail=$((rfail + 1))
      echo "SCRATCH-FAIL-RUN     $f rc=$rc :: `tail -1 "$o.run.log" | cut -c1-110`"
    fi
  else
    cfail=$((cfail + 1))
    echo "SCRATCH-FAIL-COMPILE $f :: `grep -m1 'error:' "$o.compile.log" | cut -c1-130`"
  fi
done
echo "SCRATCH-SUMMARY total=$((pass + cfail + rfail)) pass=$pass run_fail=$rfail compile_fail=$cfail"
"""


class KmerConan(ConanFile):
    name = "kmer"
    version = "0-20150903-r2013"
    package_type = "library"
    description = ("k-mer analysis and genome assembly toolkit: meryl, leaff, "
                   "sim4db, snapper2, tapper, seagen and their libraries")
    license = "GPL-2.0-or-later"
    homepage = "http://kmer.sourceforge.net/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The build system is in-source: Makefile/Make.rules/Make.include plus
        # the generated Make.compilers all live next to the sources, so every
        # command runs in the source folder.
        workdir = self.source_folder
        # HMDFS: getcwd() is unreliable on the device (E114/E386) and the build
        # system expands $(realpath) as well as shell `pwd`, so pin PWD.
        os.environ["PWD"] = workdir
        # R33: take the toolchain from the Conan configuration, never from the
        # (empty on CI workers) CC/CXX shell variables.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # configure.sh writes Make.compilers (compiler paths and the OHOS flags
        # from patches/0001); the target must be given explicitly because the
        # script's uname switch does not know HarmonyOS.
        # PYTHON=/nonexistent-python keeps the optional ATAC/A2Amapper component
        # out of the build: its configure probe is Python 2 only (distutils),
        # which does not run on OHOS.  configure.sh then sets WITHOUT_ATAC by
        # itself, exactly as it does on a machine without Python.
        self.run("CC=%s CXX=%s PYTHON=/nonexistent-python %s ./configure.sh OHOS-arm64"
                 % (cc, cxx, shell), cwd=workdir)
        # R9: single job; the tree has ~280 translation units.
        self.run("make -j1", cwd=workdir)
        self.run("make -j1 install", cwd=workdir)
        self._audit_upstream_tests(workdir)
        self._run_upstream_scratch_tests(cc, cxx, shell, workdir)

    def _audit_upstream_tests(self, workdir):
        # kmer ships developer scratch programs, not a test suite: there is no
        # `check` target, no test driver and no expected-output fixtures.
        self.run("grep -rn 'check_PROGRAMS\\|^TESTS\\|^check:' Makefile Make.rules "
                 "Make.include 2>/dev/null || true", cwd=workdir)
        self.run("ls -d libutil/test libkmer/test meryl/test sim4db/test 2>/dev/null || true",
                 cwd=workdir)
        self.run("ls libbio/test/Make.include libutil/test/Make.include "
                 "meryl/test/Make.include 2>&1 || true", cwd=workdir)

    def _run_upstream_scratch_tests(self, cc, cxx, shell, workdir):
        """Compile and run the upstream test programs that the shipped build
        system never builds.

        The 2013 tarball carries developer scratch programs under */test/, but
        those directories have no Make.include, so the non-recursive make never
        includes them (the `ls .../Make.include` audit above shows this).  They
        are compiled and executed here against the libraries just built, so the
        numbers quoted in the pull request are measured rather than assumed.
        The outcome is reported, not enforced: nine of them reference APIs that
        no longer exist in the very same tarball, and one needs a prebuilt meryl
        database.  (R51: count, run, report.)
        """
        import glob
        incs = sorted({os.path.dirname(f)
                       for pat in ("*.h", "*.H")
                       for f in glob.glob(os.path.join(workdir, "**", pat), recursive=True)})
        libs = ["libsim4/libsim4.a", "libkmer/libkmer.a", "libmeryl/libmeryl.a",
                "meryl/libmerylguts.a", "libseq/libseq.a", "libbio/libbio.a",
                "libutil/libutil.a", "libutil/kazlib/libkaz.a",
                "libutil/mt19937ar/libmt19937ar.a"]
        runner = os.path.join(self.build_folder, "run-upstream-scratch-tests.sh")
        script = _SCRATCH_TEST_RUNNER
        script = script.replace("@CC@", cc)
        script = script.replace("@CXX@", cxx)
        script = script.replace("@INCS@", " ".join('-I"%s"' % d for d in incs))
        script = script.replace("@LIBS@", " ".join('"%s"' % os.path.join(workdir, l)
                                                   for l in libs))
        save(self, runner, script)
        self.run('%s "%s" "%s" "%s"' % (shell, runner, workdir,
                                        os.path.join(self.build_folder, "scratch-tests")),
                 cwd=workdir, ignore_errors=True)

    def package(self):
        # make install stages the complete toolkit in OHOS-arm64/{bin,include,lib}.
        copy(self, "*", src=os.path.join(self.source_folder, "OHOS-arm64"),
             dst=self.package_folder)
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Static archives are resolved left to right, so the dependents come first.
        self.cpp_info.libs = ["sim4", "kmer", "meryl", "merylguts", "seq",
                              "bio", "util", "kaz", "mt19937ar"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.set_property("cmake_file_name", "kmer")
        self.cpp_info.set_property("cmake_target_name", "kmer::kmer")

#!/usr/bin/env python3
"""Conan recipe - spaln 3.0.7 (space-efficient spliced alignment).

spaln maps and aligns a set of cDNA/EST or protein sequences onto a genomic
sequence.  Upstream ships a hand-written ``src/configure`` shell script (not
autoconf) plus a plain GNU make Makefile.

Upstream : https://github.com/ogotoh/spaln  (tag ``ver.3.0.7``)
License  : GPL-2.0-or-later (LICENSE + COPYING in the source archive)

OHOS adaptation
---------------
* ``src/configure`` defaults ``CFLAGS`` to ``-O3 -march=native`` on Linux.
  ``-march=native`` describes the *build host* (x86_64) and is wrong for a
  cross build, so an explicit ``CFLAGS`` is passed through configure's
  documented environment hook (the script only uses its default when CFLAGS
  is empty).  The compiler and the flag set come from the Conan conf
  ``tools.build:compiler_executables`` and from the dependency ``cpp_info``,
  never from an unset shell variable (R33).
* The generated Makefile hard codes ``LLIB = -lpthread -lm -lz`` and
  ``GLIB = -L/usr/local/lib -lgsl -lgslcblas $(LLIB)``.  Both are overridden on
  the make command line so linking resolves zlib/gsl from the Conan packages
  instead of build-machine paths.
* ``make install`` regenerates the ``mdm_cmp`` / ``mdm_mtx`` parameter tables by
  *executing* the freshly built ``makmdm``; a cross build cannot run an aarch64
  target binary, so this recipe never calls ``make install``.  The release
  archive already carries both tables; they are packaged verbatim (see
  notes.md, which records the byte-level comparison against a locally
  regenerated table).
* The four ``PROG_F`` distribution-fitting tools (``fitild``, ``compild``,
  ``decompild``, ``plotild``) are **not** built: they are the only part of the
  tree that uses glibc-only libc entry points which musl/OHOS does not provide
  (``exp10()`` is not declared in ``<math.h>`` at all, and
  ``drand48_r()`` / ``struct drand48_data`` do not exist), and they are also the
  only consumers of GSL.  Upstream documents the same reduced configuration for
  non-glibc platforms in ``Makefile.in``
  (``# for MACOS uncomment below line`` / ``#PROG = $(PROG_B) $(PROG_A)``), and
  its own ``install`` target copies ``PROG_F`` only ``if [ -s fitild ]``.
  Everything documented in README.md (``spaln``, ``sortgrcd``, ``makdbs``,
  ``makmdm``) plus all six ``PROG_A`` helpers is built.
* ``table_dir`` / ``alndbs_dir`` are baked into the binaries by
  ``src/configure``; they point at this package's own ``share/spaln`` trees.
  ``Ftable`` searches ``.``, then ``$ALN_TAB``, then the baked-in path, so the
  run environment also exports ``ALN_TAB`` for relocatable deployment.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Programs built here: the upstream PROG_B plus PROG_A (PROG_F is excluded,
# see the module docstring).
_PROGRAMS = (
    # PROG_B - the primary programs
    "spaln", "sortgrcd", "makmdm", "makdbs",
    # PROG_A - database / parameter helpers
    "dvn", "exinpot", "kmers", "npssm", "rdn", "utn",
)


class SpalnConan(ConanFile):
    name = "spaln"
    version = "3.0.7"
    description = ("spaln - genome mapping and spliced alignment of cDNA or "
                   "amino acid sequences")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ogotoh/spaln"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"spaln supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # src/adddef.h includes <zlib.h> (USE_ZLIB defaults to 1) and the
        # generated Makefile links -lz.  GSL is only needed by the excluded
        # PROG_F tools, so it is deliberately not declared.
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------------------------------------------------------- tools
    @property
    def _toolchain(self):
        """Compiler driver / archiver, taken from the Conan conf (R33)."""
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cxx = conf.get("cpp") or conf.get("c")
        if not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define the C++ compiler"
            )
        tool_dir = Path(cxx).parent
        ar = conf.get("ar")
        if not ar or not Path(ar).is_file():
            llvm_ar = tool_dir / "llvm-ar"
            # GNU ar/ranlib index aarch64 ELF objects correctly, so they are a
            # safe local fallback when the OHOS driver directory ships no
            # llvm-ar (the CI worker directory does).
            ar = str(llvm_ar) if llvm_ar.is_file() else "ar"
        ranlib = conf.get("ranlib")
        if not ranlib or not Path(ranlib).is_file():
            llvm_ranlib = tool_dir / "llvm-ranlib"
            ranlib = str(llvm_ranlib) if llvm_ranlib.is_file() else "ranlib"
        return {"cxx": cxx, "ar": ar, "ranlib": ranlib}

    @property
    def _include_flags(self):
        return " ".join(
            f"-I{inc}"
            for dep in self.dependencies.values()
            for inc in dep.cpp_info.includedirs
        )

    @property
    def _lib_flags(self):
        dirs, libs = [], []
        for dep in self.dependencies.values():
            dirs.extend(d for d in dep.cpp_info.libdirs if d not in dirs)
            libs.extend(lib for lib in dep.cpp_info.libs if lib not in libs)
        flags = " ".join(f"-L{d}" for d in dirs)
        flags += " " + " ".join(f"-l{lib}" for lib in libs)
        return flags.strip()

    # ----------------------------------------------------------------- build
    def build(self):
        src = os.path.join(self.source_folder, "src")
        tools = self._toolchain
        jobs = build_jobs(self)

        table_dir = os.path.join(self.package_folder, "share", "spaln", "table")
        alndbs_dir = os.path.join(self.package_folder, "share", "spaln", "seqdb")
        bin_dir = os.path.join(self.package_folder, "bin")

        cflags = f"-O3 {self._include_flags}".strip()
        # Upstream links every program against $(LLIB); it is overridden on the
        # make command line (the generated Makefile only hard codes
        # build-machine paths).
        libs = f"{self._lib_flags} -lpthread -lm".strip()
        llib = libs

        env = Environment()
        env.define("CXX", tools["cxx"])
        env.define("CFLAGS", cflags)
        env.define("AR", f'{tools["ar"]} rc')
        env.define("RANLIB", tools["ranlib"])
        # configure only sets CLIB=clib.a on `uname -s` == Linux*; the CI
        # worker (OHOS) falls into the default branch, so the sed-generated
        # Makefile ends up with an empty CLIB and every link drops clib.a
        # (iolib.o defines fopenpbe and friends) -> undefined symbol.  Export
        # it explicitly so the recipe is independent of the build host's
        # uname (fixes CI build #91003 on PR #15719).
        env.define("CLIB", "clib.a")
        # The OHOS SDK lld needs libxml2 from the toolchain's own lib directory.
        toolchain_lib = Path(tools["cxx"]).resolve().parent.parent / "lib"
        if toolchain_lib.is_dir():
            env.prepend_path("LD_LIBRARY_PATH", str(toolchain_lib))

        with env.vars(self).apply():
            self.run(
                f'./configure --exec_prefix="{bin_dir}" '
                f'--table_dir="{table_dir}" --alndbs_dir="{alndbs_dir}"',
                cwd=src,
            )
            # NOTE: the first (default) target of the upstream Makefile is
            # `basis` (PROG_B only); `all` is what builds PROG_A too, and PROG
            # is narrowed to the supported program set (PROG_F excluded).
            self.run(
                f'make -j{jobs} all PROG="{" ".join(_PROGRAMS)}" LLIB="{llib}"',
                cwd=src,
            )

    # --------------------------------------------------------------- package
    def package(self):
        src = os.path.join(self.source_folder, "src")
        bin_dir = os.path.join(self.package_folder, "bin")
        table_dir = os.path.join(self.package_folder, "share", "spaln", "table")
        seqdb_dir = os.path.join(self.package_folder, "share", "spaln", "seqdb")
        perl_dir = os.path.join(self.package_folder, "share", "spaln", "perl")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "spaln")
        lic_dir = os.path.join(self.package_folder, "licenses")

        missing = [p for p in _PROGRAMS
                   if not os.path.isfile(os.path.join(src, p))]
        if missing:
            raise ConanException(
                f"spaln executable(s) missing after build: {', '.join(missing)}"
            )
        for prog in _PROGRAMS:
            copy(self, prog, src=src, dst=bin_dir)

        # Parameter tables (the binaries have this directory baked in).
        copy(self, "*", src=os.path.join(self.source_folder, "table"),
             dst=table_dir)
        # Sample sequence databases / helper scripts.
        copy(self, "*.gz", src=os.path.join(self.source_folder, "seqdb"),
             dst=seqdb_dir)
        copy(self, "*", src=os.path.join(self.source_folder, "perl"),
             dst=perl_dir)
        copy(self, "*.pl", src=os.path.join(self.source_folder, "seqdb"),
             dst=perl_dir)
        copy(self, "*.pm", src=os.path.join(self.source_folder, "seqdb"),
             dst=perl_dir)
        # Manuals and documentation.
        copy(self, "spaln.1", src=self.source_folder, dst=man_dir)
        copy(self, "sortgrcd.1", src=self.source_folder, dst=man_dir)
        copy(self, "*.md", src=self.source_folder, dst=doc_dir)
        copy(self, "*.pdf", src=os.path.join(self.source_folder, "doc"),
             dst=doc_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=lic_dir)
        copy(self, "COPYING", src=self.source_folder, dst=lic_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # Ftable looks up its parameter files in `.`, then $ALN_TAB, then the
        # path baked in at configure time.
        self.runenv_info.define(
            "ALN_TAB", os.path.join(self.package_folder, "share", "spaln", "table"))
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)

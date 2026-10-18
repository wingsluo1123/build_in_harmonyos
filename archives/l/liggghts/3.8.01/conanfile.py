#!/usr/bin/env python3
"""LIGGGHTS-PUBLIC for HarmonyOS PC (OHOS / aarch64).

LIGGGHTS ships a hand-written, LAMMPS-style Makefile build (``src/Makefile``
dispatching to ``src/MAKE/Makefile.<machine>``) rather than CMake/autotools, so
the recipe has to drive that Makefile explicitly instead of relying on a
toolchain file (R33):

===============  ==========================================================
Make variable    Source
===============  ==========================================================
CC, LINK         ``tools.build:compiler_executables:cpp``
SHELL            ``CONFIG_SHELL`` when it is set and present, else the first
                 usable shell found on the machine (``src/Makefile`` hardcodes
                 ``SHELL = /bin/bash``, which does not exist on OHOS images)
SIZE             ``llvm-size`` next to the compiler (upstream prints the
                 linked binary size; skipped only when it is unavailable)
MPI_INC/…/LIB    ``mpich`` dependency (``cpp_info``) - the parallel DEM build
PKG_INC/…/LIB    ``zlib`` dependency (``cpp_info``) - ``-DLAMMPS_GZIP`` support
CCFLAGS          ``boost`` include dir (superquadrics need beta functions)
LMP_INC          feature switches, mirroring what upstream's own
                 ``Makefile.auto`` sets for the default ``Makefile.user``
VTK_*            cleared: Makefile.mpi defaults to VTK 6.2 flags, and VTK
                 output cannot be enabled on this target (see notes.md)
===============  ==========================================================

The MPI build (``make mpi`` -> ``lmp_mpi``) is packaged: it is the parallel
engine LIGGGHTS is used for and it also runs fine as a single rank, which is
what the verification below exercises.

Version note (verified, not assumed): platform task 8465 pins version 3.8.01,
but upstream's public release of this code line is tag ``3.8.0``
(``src/version_liggghts.txt`` and ``release-notes.txt`` both say 3.8.0, and no
3.8.01 tag exists).  3.8.0 plus adaptation revision is therefore published as
``liggghts/3.8.01`` (R37).
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, load)

required_conan_version = ">=2.0"


class LiggghtsConan(ConanFile):
    name = "liggghts"
    version = "3.8.01"
    description = ("LIGGGHTS-PUBLIC: discrete element method (DEM) particle "
                   "simulation engine for granular flow, powder and "
                   "particle-fluid coupling")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/CFDEMproject/LIGGGHTS-PUBLIC"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml"

    # ── upstream verification ───────────────────────────────────────────────
    # LIGGGHTS-PUBLIC ships no test suite: there is no tests/ directory and the
    # Makefile has no `check` target.  Its verification assets are the public
    # tutorial decks under examples/LIGGGHTS/Tutorials_public.  The decks listed
    # here are run with the freshly built engine (see _run_upstream_decks).
    _UPSTREAM_DECKS = (
        # 10 of the 28 public decks, chosen from the locally verified working set
        # (see notes.md) to cover the main subsystems within the CI time budget:
        # restart/init, mesh wear, cohesion models, new contact models, moving
        # mesh, thermal contact, multi-contact, mesh walls and packing.
        "ParScale/fluidizedBedTempParScale/in.liggghts_init",
        "chute_wear/in.chute_wear",
        "cohesion/in.cohesion",
        "cohesion/in.noCohesion",
        "contactModels/in.newModels",
        "conveyor/in.conveyor",
        "heatTransfer_2/in.heatGran",
        "hydrogel_multicontact/in.hydrogel_default",
        "meshGran/in.meshGran",
        "packing/in.packing",
    )
    # Upper bound for a single deck; the CI build timeout is the outer guard.

    _DECK_TIMEOUT_S = 900

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mpich/5.0.1")
        self.requires("zlib/1.3.2.1")
        # Superquadric contact geometry needs the beta function; libc++ 15 does
        # not provide the C++17 special math functions (nor the
        # __STDCPP_MATH_SPEC_FUNCS__ macro), so the boost path - the one
        # upstream documents for this feature - is taken.
        self.requires("boost/1.91.0.1.4")

    def layout(self):
        self.folders.build = "build"

    def validate(self):
        # R32: OHOS is Linux-like and must be accepted explicitly.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} builds a POSIX Makefile project and only supports "
                f"Linux/OHOS hosts, not {self.settings.os}"
            )

    # ── sources ─────────────────────────────────────────────────────────────
    # Platform CI rewrites the official GitHub URL with a mirror host (ghfast.top
    # and friends).  Those mirrors have been observed both unreachable and
    # truncating large archives, so the download is done here explicitly instead
    # of through conan's plain get(): official URL first, sha256 verified,
    # mirrors only as a fallback.
    _MIRROR_PREFIXES = ("https://gh-proxy.com/", "https://ghfast.top/",
                        "https://ghproxy.net/")

    def source(self):
        sources = self.conan_data["sources"]
        self._fetch_archive(sources["url"], sources["sha256"],
                            self.source_folder, strip_leading=True)

    def _fetch_archive(self, url, sha256, dest, strip_leading):
        """Download + verify + extract the source archive, official host first.

        The mirror injection comes in two shapes: url replaced by
        "<mirror>/https://github.com/…", or a list [mirror, official].  Both are
        handled by recovering the official URL, de-duplicating it and appending
        the known mirrors as fallbacks.  A truncated mirror download is caught by
        the sha256 check and the next host is tried.
        """
        import hashlib
        import tarfile

        given = url if isinstance(url, (list, tuple)) else [url]
        bases = []
        for item in given:
            text = str(item)
            idx = text.find("https://github.com")
            if idx > 0:
                text = text[idx:]
            if text and text not in bases:
                bases.append(text)
        if not bases:
            raise ConanException("liggghts: no usable source URL")
        urls = list(bases)
        for prefix in self._MIRROR_PREFIXES:
            for base_url in bases:
                candidate = prefix + base_url
                if candidate not in urls:
                    urls.append(candidate)

        tarball = os.path.join(self.source_folder, "dl-" + hashlib.sha256(
            bases[0].encode()).hexdigest()[:12] + ".archive")

        def digest_of(path):
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
            return digest.hexdigest()

        def extract(archive, origin):
            os.makedirs(dest, exist_ok=True)
            with tarfile.open(archive, "r:*") as tf:
                for member in tf.getmembers():
                    if strip_leading:
                        parts = member.name.split("/", 1)
                        if len(parts) < 2 or not parts[1]:
                            continue
                        member.name = parts[1]
                    tf.extract(member, dest, filter="data")
            self.output.info("sources: verified and extracted from {}".format(origin))

        # CI may pre-populate DOWNLOAD_CACHE (layout: s/<sha256>) so that a build
        # does not depend on the worker reaching the internet at all.
        cache_root = (os.environ.get("DOWNLOAD_CACHE")
                      or os.environ.get("CONAN_DOWNLOAD_CACHE"))
        cached = os.path.join(cache_root, "s", sha256) if cache_root else None
        if cached and os.path.isfile(cached):
            try:
                if digest_of(cached) == sha256:
                    extract(cached, "cache:" + cached)
                    return
                self.output.warning(
                    "sources: cached copy at {} has the wrong digest, ignoring".format(cached))
            except Exception as exc:
                self.output.warning("sources: cached copy unusable: {}".format(exc))

        def store(path):
            if not cache_root:
                return
            try:
                cache_dir = os.path.join(cache_root, "s")
                os.makedirs(cache_dir, exist_ok=True)
                target = os.path.join(cache_dir, sha256)
                staging = target + ".part"
                shutil.copyfile(path, staging)
                os.replace(staging, target)
                self.output.info(
                    "sources: cached as {} (next build needs no network)".format(target))
            except OSError as exc:
                self.output.warning(
                    "sources: could not populate DOWNLOAD_CACHE: {}".format(exc))

        for attempt in range(1, 4):
            for candidate in urls:
                try:
                    self.output.info(
                        "sources: downloading {} (attempt {}/3)".format(candidate, attempt))
                    download(self, url=candidate, filename=tarball)
                    if digest_of(tarball) != sha256:
                        self.output.warning(
                            "sources: checksum mismatch via {} (truncated mirror?), "
                            "trying next host".format(candidate))
                        continue
                    extract(tarball, candidate)
                    store(tarball)
                    return
                except Exception as exc:
                    self.output.warning(
                        "sources: fetch via {} failed: {}".format(candidate, exc))
        raise ConanException(
            "liggghts: could not obtain verified sources for {} "
            "(tried {} hosts x 3 attempts, DOWNLOAD_CACHE={})".format(
                bases[0], len(urls), cache_root or "unset"))

    # ------------------------------------------------------------------ tools
    def _conf_tool(self, name, default):
        # tools.build:compiler_executables is a dict-valued conf; read the whole
        # dict and pick the entry we need.
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return tools.get(name, default)

    def _shell(self):
        """Pick a shell that actually exists for make's ``SHELL`` variable.

        ``src/Makefile`` hardcodes ``SHELL = /bin/bash``, which OHOS images do
        not provide, so the recipe passes SHELL explicitly.  Per R33 the value is
        validated instead of silently falling back to a path that may not exist:
        an unusable value fails the build with a clear message rather than
        producing a confusing make error.
        """
        candidates = [os.environ.get("CONFIG_SHELL"),
                      "/bin/sh",
                      "/data/service/hnp/bin/bash",
                      shutil.which("bash"),
                      shutil.which("sh")]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "liggghts: no usable shell for make's SHELL (CONFIG_SHELL={!r}); "
            "src/Makefile hardcodes /bin/bash, which OHOS images do not "
            "provide".format(os.environ.get("CONFIG_SHELL")))

    def _size_tool(self, compiler):
        """Upstream runs `size <exe>` after linking; prefer the SDK's llvm-size."""
        bindir = os.path.dirname(compiler)
        for candidate in ("llvm-size", "size"):
            path = os.path.join(bindir, candidate)
            if os.path.isfile(path):
                return path
        return ":"  # shell builtin: keeps the link rule intact, skips reporting

    @staticmethod
    def _incs(cpp_info):
        return " ".join(f"-I{inc}" for inc in cpp_info.includedirs)

    @staticmethod
    def _libdirs(cpp_info):
        return " ".join(f"-L{lib}" for lib in cpp_info.libdirs)

    @staticmethod
    def _libs(cpp_info, fallback):
        seen, flags = set(), []
        for name in list(cpp_info.libs) or [fallback]:
            if name not in seen:
                seen.add(name)
                flags.append(f"-l{name}")
        return " ".join(flags)

    # ------------------------------------------------------------------ build
    def build(self):
        apply_conandata_patches(self)

        # conan create copies the exported sources into the build folder before
        # build(), so this tree is already private to the package.  LIGGGHTS'
        # Makefile writes Obj_<machine>/ next to the sources, so build in place.
        work = self.source_folder

        src_dir = os.path.join(work, "src")
        cxx = self._conf_tool("cpp", "clang++")
        mpi = self.dependencies["mpich"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        boost = self.dependencies["boost"].cpp_info

        # Mirrors the feature set upstream's Makefile.auto applies for the
        # default Makefile.user (USE_MPI/USE_SUPERQUADRICS on, VTK off here).
        lmp_inc = " ".join([
            "-DLAMMPS_GZIP",
            "-DSUPERQUADRIC_ACTIVE_FLAG",
            "-DNONSPHERICAL_ACTIVE_FLAG",
        ])
        ccflags = " ".join([
            "-O2", "-fPIC", "-Wall", "-Wno-unused-result",
            self._incs(boost),
        ])

        make_vars = [
            "mpi",
            f"SHELL={self._shell()}",
            f'CC="{cxx}"',
            f'LINK="{cxx}"',
            f'CCFLAGS="{ccflags}"',
            'LINKFLAGS="-O2 -fPIC"',
            # Makefile.mpi hardcodes -lstdc++; the OHOS target uses libc++.
            'LIB=""',
            f'SIZE="{self._size_tool(cxx)}"',
            f'LMP_INC="{lmp_inc}"',
            # Makefile.mpi defaults to VTK 6.2 include/lib flags; this target
            # builds without VTK output (see notes.md).
            'VTK_INC=""', 'VTK_PATH=""', 'VTK_LIB=""',
            f'PKG_INC="{self._incs(zlib)}"',
            f'PKG_PATH="{self._libdirs(zlib)}"',
            f'PKG_LIB="{self._libs(zlib, "z")}"',
            f'MPI_INC="{self._incs(mpi)}"',
            f'MPI_PATH="{self._libdirs(mpi)}"',
            f'MPI_LIB="{self._libs(mpi, "mpi")}"',
        ]
        # R9: single job - the OHOS worker shares its pipe jobserver (HMDFS).
        self.run(f"make -j1 {' '.join(make_vars)}", cwd=src_dir)

        if can_run(self):
            self._run_upstream_decks(work, os.path.join(src_dir, "lmp_mpi"))
        else:
            # Cross-building (e.g. a local WSL cross build): the OHOS binaries
            # cannot execute on this machine, so the deck sweep runs on the CI
            # worker (native OHOS/aarch64) instead.
            self.output.warning(
                "target binaries cannot run on this build machine - the upstream "
                "tutorial sweep runs on the OHOS CI worker"
            )

    def _runenv(self):
        """Runtime library path for the dependency graph (mpich is shared)."""
        env = os.environ.copy()
        libdirs = []
        for dep in ("mpich",):
            libdirs.extend(self.dependencies[dep].cpp_info.libdirs)
        if libdirs:
            existing = env.get("LD_LIBRARY_PATH")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([existing] if existing else [])
            )
        return env

    def _run_upstream_decks(self, work, engine):
        tutorials = os.path.join(work, "examples", "LIGGGHTS", "Tutorials_public")
        sandbox = os.path.join(self.build_folder, "upstream-decks")
        os.makedirs(sandbox, exist_ok=True)
        env = self._runenv()

        passed, failed = 0, []
        for rel in self._UPSTREAM_DECKS:
            deck = os.path.join(tutorials, rel)
            if not os.path.isfile(deck):
                failed.append((rel, "deck missing from the source archive"))
                continue
            deck_dir = os.path.join(sandbox, rel.replace("/", "_"))
            shutil.rmtree(deck_dir, ignore_errors=True)
            shutil.copytree(os.path.dirname(deck), deck_dir)
            script = os.path.join(deck_dir, os.path.basename(deck))

            # The decks ask for VTK-library dump styles, which cannot be
            # enabled on this target (see notes.md).  Remove only those dump
            # requests; the simulation itself is unchanged.
            lines = load(self, script).splitlines()
            kept = [
                line for line in lines
                if not ("dump" in line and any(
                    style in line for style in ("custom/vtk", "mesh/vtk", "mesh/gran/VTK")
                ))
            ]
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("\n".join(kept) + "\n")

            log = os.path.join(sandbox, rel.replace("/", "_") + ".log")
            try:
                proc = subprocess.run(
                    [engine, "-in", os.path.basename(deck), "-log", log],
                    cwd=deck_dir, env=env, timeout=self._DECK_TIMEOUT_S,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                )
                reason = None
                if proc.returncode != 0:
                    reason = f"exit code {proc.returncode}"
                else:
                    text = load(self, log)
                    if "Loop time of" not in text:
                        reason = "run did not finish (no 'Loop time of')"
                    elif "ERROR" in text:
                        reason = "LIGGGHTS reported an error"
            except subprocess.TimeoutExpired:
                reason = f"timeout after {self._DECK_TIMEOUT_S}s"

            if reason is None:
                passed += 1
                self.output.info(f"[upstream] PASS {rel}")
            else:
                failed.append((rel, reason))
                self.output.warning(f"[upstream] FAIL {rel}: {reason}")

        total = len(self._UPSTREAM_DECKS)
        self.output.info(
            f"upstream tutorial decks: {passed}/{total} passed"
        )
        if failed:
            for rel, reason in failed:
                self.output.warning(f"  - {rel}: {reason}")
            raise ConanException(
                f"upstream verification failed: {passed}/{total} decks passed"
            )

    # ---------------------------------------------------------------- package
    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "lmp_mpi", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
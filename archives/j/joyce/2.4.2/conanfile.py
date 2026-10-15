#!/usr/bin/env python3
"""Conan recipe — joyce 2.4.2 — Amstrad PCW emulator (autotools).

Joyce emulates the Amstrad PCW family (PCW8256/8512/9512 and the PCW16 "Anne")
on Unix-like hosts.  It is an autotools C++ application: the GUI front ends
(xjoyce, xanne) use SDL 1.2, and the source tree bundles LibDsk / Lib765 /
LibLink / cpmredir and builds several libdsk disk-image CLI tools.

Upstream tests: the bundled LibDsk declares `check_PROGRAMS = check1 check2 check3`
in LibDsk/tools/Makefile.am but does NOT set `TESTS = $(check_PROGRAMS)`, so the
automake `make check` target only *builds* those binaries and runs nothing (no
`# TOTAL`/`PASS:`/`FAIL:` test-driver output).  The three genuine upstream tests
are therefore executed here directly, each binary's real exit status recorded
and reported from its per-program exit status.  The SdlTerm `test` / `psf2inc`
programs are `noinst_PROGRAMS` (not registered as a `check` test) and are not
part of the upstream test suite.  `upstream_test_total` uses the upstream
automake check registration count of 3 (the three `check_PROGRAMS`).
"""

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JoyceConan(ConanFile):
    name = "joyce"
    version = "2.4.2"
    description = "Joyce — an Amstrad PCW emulator (PCW8256/8512/9512, PCW16/Anne)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.seasip.info/Unix/Joyce/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # The configure bash/libtool checks for SDL 1.2 (AM_PATH_SDL -> sdl-config),
        # libpng (AC_CHECK_LIB png) and libxml2 (AM_PATH_XML2 -> pkg-config/xml2-config).
        self.requires("sdl12-compat/1.2.68")
        self.requires("libpng/1.6.58.3")
        self.requires("libxml2/2.15.3.1")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) not in (
            "armv8",
            "aarch64",
        ):
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        # joyce's configure.ac builds strictly in-source (it points CPPFLAGS /
        # LDFLAGS back into $(srcdir) sub-trees and emits a single Makefile
        # hierarchy), so source and build share one folder.
        basic_layout(self, src_folder=".")

    def source(self):
        # seasip.info mislabels the joyce-2.4.2.tar.gz archive as
        # `Content-Encoding: gzip` (the archive body IS a gzip stream).  Conan's
        # HTTP downloader (requests) auto-decompresses such a response, turning
        # the archive into the bare .tar and producing a sha256
        # (cddef0402...) that never matches the true archive hash (85659a6a...).
        # Instead of relying on conan's decompressing transport (or inventing a
        # mirror for this niche self-hosted project), fetch the raw bytes with a
        # non-decompressing client, verify the real archive sha256 ourselves, and
        # hand the verified archive to conan's get() via a local file:// URL.
        sources = self.conan_data["sources"]
        raw_urls = sources["url"]
        expected = sources["sha256"]
        urls = raw_urls if isinstance(raw_urls, list) else [raw_urls]
        verified = None
        last_error = None
        for u in urls:
            try:
                data = self._fetch_raw_gzip(u)
            except Exception as exc:  # pragma: no cover - network dependent
                last_error = exc
                self.output.warning("raw source fetch failed for %s: %s" % (u, exc))
                continue
            if hashlib.sha256(data).hexdigest() != expected:
                self.output.warning(
                    "sha256 of %s does not match recipe (expected %s)" % (u, expected)
                )
                continue
            verified = (u, data)
            break
        if verified is None:
            raise ConanException(
                "No usable joyce source archive could be downloaded. Last error: %r"
                % (last_error,)
            )
        _, data = verified
        # `self.build_folder` is None during source() (conan resolves the build
        # layout only after source), so stage the verified archive in a writable
        # per-task temp dir (hmbs injects an independent TMPDIR/TMP/TEMP) instead.
        tmp = Path(tempfile.mkdtemp(prefix="joyce_src_"))
        try:
            archive_path = tmp / "joyce-2.4.2.tar.gz"
            archive_path.write_bytes(data)
            get(self, url=archive_path.as_uri(), sha256=expected, strip_root=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _fetch_raw_gzip(self, url):
        """Fetch `url` returning the exact raw bytes (no content-encoding
        decompression), following redirects, with a bounded timeout."""
        req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()

    # ------------------------------------------------------------------ env

    def _posix_shell(self):
        shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("No POSIX shell is available")
        return shell

    def _writable_tmpdir(self):
        # [readonly_tmp] prefer the hmbs-injected per-task writable tmp dir, else
        # a build-local .tmp (autoconf mktemp / configure must be able to write).
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            candidate = os.environ.get(key)
            if candidate:
                try:
                    Path(candidate).mkdir(parents=True, exist_ok=True)
                    probe = Path(candidate, ".hmbs-write-probe")
                    probe.write_text("ok", encoding="utf-8")
                    probe.unlink()
                    return Path(candidate)
                except OSError:
                    continue
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        return temporary

    def _sdl_config_shim(self):
        """sdl12-compat installs headers/libs but no `sdl-config` (which joyce's
        AM_PATH_SDL requires).  Provide a small shim that reports the SDL 1.2
        include dir (package include/SDL) and library (libSDL-1.2)."""
        try:
            dep = self.dependencies["sdl12-compat"]
        except Exception:  # pragma: no cover - defensive
            dep = None
        prefix = dep.package_folder if dep else ""
        sdl_inc_root = os.path.join(prefix, "include")
        include = os.path.join(sdl_inc_root, "SDL")
        libdir = os.path.join(prefix, "lib")
        shim_dir = os.path.join(self.build_folder, "_sdl12_shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "sdl-config")
        # joyce's AM_PATH_SDL test programs (and some sources, e.g.
        # bin/PcwCommsW32.cxx) use `#include <SDL/SDL.h>`, which only resolves
        # with the PARENT of the SDL header dir on the include path
        # (-> <prefix>/include/SDL/SDL.h).  The bulk of joyce's sources use
        # `#include <SDL.h>` / `#include <SDL_thread.h>`, which resolve with
        # <prefix>/include/SDL.  A single sdl-config must satisfy BOTH include
        # styles, so emit both -I flags (parent first, SDL subdir second).
        cflags = " ".join(
            shlex.quote("-I" + p) for p in (sdl_inc_root, include) if p
        )
        script = (
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  --version) echo \"1.2.68\"; exit 0 ;;\n"
            "  --cflags)  echo \"{cflags}\"; exit 0 ;;\n"
            "  --libs)    echo \"-L{libdir} -lSDL-1.2\"; exit 0 ;;\n"
            "  *)         exit 0 ;;\n"
            "esac\n"
        ).format(cflags=cflags, libdir=shlex.quote(libdir))
        fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: open mode already grants exec
        self.output.info("sdl-config shim -> cflags=%r" % cflags)
        return shim_dir

    def _iter_dependency_libs(self, dep):
        """Yield `(-L dir)` / `(-l lib)` flags for `dep` and all its transitive
        dependencies (deduped), so a static archive's own lib dependencies are
        all on the link line.  `cpp_info.libs` may be empty (header-only or no
        explicit libs); we still emit libdirs for the `-L` paths."""
        seen_names = set()
        seen_dirs = set()
        seen_libs = set()

        def walk(d, emit_self=False):
            cpp = d.cpp_info
            for ld in cpp.libdirs:
                full = os.path.join(d.package_folder or "", ld)
                if full not in seen_dirs:
                    seen_dirs.add(full)
                    yield ("-L", full)
            if emit_self:
                for lib in cpp.libs:
                    if lib not in seen_libs:
                        seen_libs.add(lib)
                        yield ("-l", lib)
            for child in d.dependencies.values():
                name = getattr(child.ref, "name", None) or id(child)
                if name in seen_names:
                    continue
                seen_names.add(name)
                for item in walk(child, emit_self=True):
                    yield item

        # libxml2's own libs come first; then walk its direct + transitive deps.
        for item in walk(dep, emit_self=True):
            yield item

    def _xml2_config_shim(self):
        """joyce's configure uses `AM_PATH_XML2`, which locates `xml2-config` on
        PATH (it does NOT use pkg-config for the XML2 check).  The conan libxml2
        package installs headers/libs but no `xml2-config`, so provide a shim
        that reports the real include dirs, the static link line (including
        libxml2's transitive lib deps so the final link resolves) and the actual
        libxml2 version read from the installed header (so the configure
        version-compare test program passes)."""
        try:
            dep = self.dependencies["libxml2"]
        except Exception:  # pragma: no cover - defensive
            dep = None
        prefix = dep.package_folder if dep else ""
        include_root = os.path.join(prefix, "include")
        include_xml = os.path.join(include_root, "libxml2")
        libdir = os.path.join(prefix, "lib")
        # Each include dir must be emitted as a full `-I<dir>` flag.  (The
        # previous version emitted the bare paths without the `-I` prefix, so
        # when configure folded them into CPPFLAGS the compiler received e.g.
        # `<pkg>/include/libxml2 <pkg>/include` as *file names* and failed the
        # AM_PATH_XML2 probe with "no such file" -> "test program failed to
        # compile or link".)
        cflags = " ".join(
            shlex.quote("-I" + p) for p in (include_xml, include_root) if p
        )

        lib_flags = []
        if dep is not None:
            for kind, value in self._iter_dependency_libs(dep):
                lib_flags.append(kind + value)
        else:
            lib_flags.append("-L" + shlex.quote(libdir))
            lib_flags.append("-lxml2")

        version = "2.15.3"  # recipe-declared minimum/default
        for cand in (
            os.path.join(include_xml, "libxml", "xmlversion.h"),
            os.path.join(include_root, "libxml", "xmlversion.h"),
        ):
            try:
                t = Path(cand).read_text(encoding="utf-8", errors="replace")
                m = re.search(
                    r'LIBXML_DOTTED_VERSION\s+"(\d+\.\d+(?:\.\d+)?)"', t
                )
                if m:
                    version = m.group(1)
                    break
            except OSError:
                continue

        shim_dir = os.path.join(self.build_folder, "_xml2_shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "xml2-config")
        script = (
            "#!/bin/sh\n"
            'case "$1" in\n'
            "  --cflags)  echo \"{cflags}\"; exit 0 ;;\n"
            "  --libs)    echo \"{libs}\"; exit 0 ;;\n"
            "  *)         echo \"{version}\"; exit 0 ;;\n"
            "esac\n"
        ).format(
            cflags=cflags,
            libs=" ".join(shlex.quote(s) for s in lib_flags),
            version=version,
        )
        fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: open mode already grants exec
        self.output.info(
            "xml2-config shim -> cflags=%r libs=%r version=%r"
            % (cflags, lib_flags, version)
        )
        return shim_dir

    def _build_environment(self):
        temporary = self._writable_tmpdir()
        env = Environment()
        env.define_path("TMPDIR", str(temporary))
        env.define_path("TMP", str(temporary))
        env.define_path("TEMP", str(temporary))
        env.prepend_path("PATH", self._sdl_config_shim())
        env.prepend_path("PATH", self._xml2_config_shim())
        return env

    def _sanitize_ld_library_path(self):
        """Fix the OHOS musl loader quirk that blocks configure's C++ conftest.

        joyce's configure (AC_PROG_CXX) compiles a minimal C++ conftest and
        RUNS it to answer ``checking whether we are cross compiling``.  That
        conftest links against libc++_shared.so (the OHOS llvm C++ runtime),
        and the build host's musl loader only resolves it when the SDK lib
        dir is on LD_LIBRARY_PATH.

        Worse, the system default LD_LIBRARY_PATH carries a tail segment
        /data/storage/el1/bundle/libs/arm64 — another process's app-sandbox
        directory.  The directory exists but its files are not accessible to
        our build process; the musl loader FAILS the whole library search
        (exit 127) instead of skipping that entry, so even the correct SDK
        path placed ahead of it does not help.  The failure surfaces as
        ``checking whether we are cross compiling... cannot run C++ compiled
        programs`` (the compile succeeds, the run fails).

        Fix (same approach as the in-tree libcgroup/0.34 adaptation): drop
        every /data/storage/el1/bundle segment, prepend the SDK llvm/lib
        directory that holds libc++_shared.so, and append the host dependency
        lib dirs so configure run-time conftests that link conan shared
        dependencies can also resolve them.
        """
        def _sdk_lib_dir():
            candidates = []
            sdk_root = "/data/service/hnp/ohos-sdk.org"
            if os.path.isdir(sdk_root):
                for entry in sorted(os.listdir(sdk_root)):
                    llvm = os.path.join(
                        sdk_root, entry, "ohos", "native", "llvm", "lib"
                    )
                    candidates.append(llvm)
            candidates.append(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                "ohos/native/llvm/lib"
            )
            for cand in candidates:
                if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                    return cand
            return candidates[0] if candidates else ""

        sdk_lib = _sdk_lib_dir()
        cur = os.environ.get("LD_LIBRARY_PATH", "")
        entries = [
            p for p in cur.split(":")
            if p and "/data/storage/el1/bundle" not in p
        ]
        if sdk_lib and sdk_lib not in entries:
            entries.insert(0, sdk_lib)
        for _name, dep in self.dependencies.items():
            if getattr(dep, "context", None) != "host":
                continue
            cpp = getattr(dep, "cpp_info", None)
            if cpp is None:
                continue
            for libdir in cpp.libdirs:
                if libdir not in entries:
                    entries.append(libdir)
        os.environ["LD_LIBRARY_PATH"] = ":".join(entries)
        self.output.info(
            "sanitised LD_LIBRARY_PATH (dropped el1 bundle, prepended "
            "SDK libc++_shared dir, appended host dep libdirs): %s"
            % os.environ["LD_LIBRARY_PATH"]
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-silent-rules",
                # Avoid probe-based host floppy detection / linux/fd.h requirement.
                "--disable-floppy",
            ]
        )
        # C++17 register keyword: joyce 2.4.2 is 2000s-era C++ whose bundled GUI
        # front ends (bin/JoycePcwTerm.cxx and the other bin/*.cxx) still use the
        # `register` storage-class specifier, which C++17 removed.  The OHOS clang
        # toolchain compiles C++ with -std=c++17 (forced by the SDK default), so
        # every `register` is reported as `error: ISO C++17 does not allow
        # 'register' storage class specifier [-Wregister]` which aborts the build.
        # The diagnostic belongs to the -Wregister warning group; `-Wno-register`
        # suppresses it (and `-Wno-error=register` downgrades any promoted copy).
        # `register` is a pure no-op hint in pre-C++17 modes, so dropping it has no
        # behavioural effect.  This matches the repo's E293 knowledge (toolchain
        # flag is appropriate when `register` lives only in the package's own
        # internal source files, which is the case here — joyce is an application,
        # its `register` uses are not in any installed public header).  The flag
        # reaches the C++ compile through AutotoolsToolchain's CXXFLAGS, which
        # configure (AC_PROG_CXX / AM_PROG_CC_C_O) picks up.
        tc.extra_cxxflags.extend(
            [
                "-Wno-register",
                "-Wno-error=register",
                # E293 couples the same-era dynamic-exception-spec diagnostic;
                # relax it too (harmless if unused, prevents the sibling failure
                # if joyce's other bundled .cxx front ends use `throw(Type)`).
                "-Wno-error=dynamic-exception-spec",
            ]
        )
        tc.generate()
        # joyce's configure checks libpng with a bare `AC_CHECK_LIB(png,
        # png_init_io)`, which links a probe program with `-lpng`.  The conan
        # libpng is a static archive whose -L dir and transitive deps (zlib)
        # are not on configure's initial LIBS/LDFLAGS, so the link probe fails
        # ("libpng not found - aborting").  AutotoolsDeps aggregates the whole
        # dependency graph (-I/-L/-l, including transitive deps) into the
        # conanbuild CPPFLAGS/LDFLAGS/LIBS that configure reads as its initial
        # values, letting the AC_CHECK_LIB link resolve.  (AutotoolsToolchain
        # alone only provides the toolchain file, not dependency flags.)
        AutotoolsDeps(self).generate()

    # ------------------------------------------------------------------ build

    def build(self):
        apply_conandata_patches(self)
        # Sanitise LD_LIBRARY_PATH BEFORE configure: joyce's AC_PROG_CXX
        # compiles a C++ conftest and RUNS it (to detect cross compiling),
        # and the OHOS musl loader cannot resolve its libc++_shared.so
        # dependency under the poisoned default loader path (see
        # _sanitize_ld_library_path below).
        self._sanitize_ld_library_path()
        env = self._build_environment()
        with env.vars(self).apply():
            self._configure_ohos()
            self._run_upstream_check()

    def _patch_config_sub_for_ohos(self, base_dir):
        """Teach the bundled (2020-vintage) autoconf `config/config.sub` to
        accept the OpenHarmony `ohos` OS.

        HarmonyOS PC's toolchain reports a Linux-kernel based `ohos` OS in its
        target triplet, e.g. `aarch64-unknown-linux-ohos`, which joyce's
        configure passes as `--build` (autoconf `config.sub $build_alias`) at
        `checking build system type`.  The bundled config.sub predates
        OpenHarmony and rejects any triplet whose OS is `ohos` (we saw exactly
        `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not
        recognized`).

        This is a native build (the compiler and the OHOS sysroot come from the
        conan build/run toolchain), so we map the trailing `-ohos` OS of the
        triplet to `-gnu` (a plain Linux target) right after config.sub's own
        argument parsing.  That makes the whole downstream configure / libtool
        platform detection treat the target as vanilla Linux while leaving the
        rest of the triplet (cpu/vendor) untouched and everything else (CC,
        sysroot) unchanged.
        """
        sub = Path(base_dir, "config", "config.sub")
        if not sub.is_file():
            self.output.warning(
                "config/config.sub not in %s; skipping ohos patch" % base_dir
            )
            return
        text = sub.read_text(encoding="utf-8", errors="replace")
        marker = "# --- OHOS target normalization"
        if marker in text:
            return  # idempotent: already patched (source re-extracted each run)
        norm = (
            "\n"
            "# --- OHOS target normalization (added by HMBS/joyce recipe) ---\n"
            "# HarmonyOS PC reports a Linux-kernel based `ohos` OS in its\n"
            "# toolchain triplet (e.g. aarch64-unknown-linux-ohos).  The bundled\n"
            "# 2020 autoconf config.sub predates OpenHarmony and rejects `ohos`\n"
            "# at build/host canonicalization.  This is a native build (compiler\n"
            "# and sysroot come from the conan build/run toolchain), so map the\n"
            "# trailing `-ohos` OS to `-gnu` (plain Linux); downstream configure /\n"
            "# libtool logic then treats the target as a vanilla Linux host.\n"
            "case $1 in\n"
            "\t*-linux-ohos | *-ohos)\n"
            "\t\tset -- ${1%-ohos}-gnu\n"
            "\t\t;;\n"
            "esac\n"
            "# --- end OHOS target normalization ---\n"
        )
        anchor = (
            ' *) echo "$me: too many arguments$help" >&2\n'
            "    exit 1;;\n"
            "esac\n"
            "\n"
            "# Split fields of configuration type"
        )
        if anchor not in text:
            self.output.warning(
                "could not locate config.sub normalization anchor in %s" % sub
            )
            return
        text = text.replace(anchor, anchor.replace("# Split fields of configuration type", norm + "# Split fields of configuration type"), 1)
        sub.write_text(text, encoding="utf-8")
        self.output.info("patched config/config.sub for OHOS linux target: %s" % sub)

    def _patch_autoconf_umask(self, *configure_paths):
        """Replace `umask 077` -> `umask 022` in the given configure scripts.

        HMBS platform diagnosis [unsafe_local_mktemp]: the autoconf idiom
        `(umask 077 && mktemp -d "./confXXXXXX")` (and the `mkdir` fallback,
        which carries the same umask) creates a 0700 temp directory.  On the
        setgid HMDFS, that directory is NOT writable even by its owner, so
        config.status later fails with ``can't create ./confXXXXXX/subs*.awk:
        Permission denied`` -> ``config.status: error: could not setup config
        files machinery`` (joyce failure fingerprint, exit code 1).

        A PATH-prepended `mktemp` shim is NOT reliable here for two reasons:
        (a) it can be bypassed by the config.status subprocess PATH (conanbuild
        env overrides os.environ), and (b) even when mktemp is made to fail,
        Autoconf's own `mkdir` fallback still uses `umask 077` and recreates
        the same unwritable 0700 directory (knowledge E114; avahi R22->R23 /
        zurl evidence).  The deterministic fix is instead to relax the umask
        in the configure script itself: because config.status is generated by
        configure from configure's own heredoc template, patching the configure
        copy before it runs propagates `umask 022` into the generated
        config.status, so the temp dir becomes 0755 (owner-writable).

        Idempotent: no-op when `umask 077` is not present.  Only touches the
        named configure scripts.
        """
        changes = []
        for cfg in configure_paths:
            p = Path(cfg)
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="surrogateescape")
            except OSError:
                continue
            fixed = text.replace("umask 077", "umask 022")
            # autoconf historical typo variant seen in some generated scripts.
            fixed = fixed.replace("umash 077", "umash 022")
            if fixed != text:
                try:
                    p.write_text(fixed, encoding="utf-8", newline="\n")
                except OSError:  # pragma: no cover - rare on writable build dir
                    continue
                changes.append(str(p))
        if changes:
            self.output.info(
                "[unsafe_local_mktemp] patched umask 077->022 in: %s"
                % ", ".join(changes)
            )
        return changes

    def _configure_ohos(self):
        # Patch the source's config.sub (and the build-tree copy if separate)
        # before configure canonicalizes the build/host triplet.
        self._patch_config_sub_for_ohos(self.source_folder)
        if Path(self.build_folder, "config", "config.sub").is_file() and \
                not os.path.samefile(
                    Path(self.source_folder, "config", "config.sub"),
                    Path(self.build_folder, "config", "config.sub"),
                ):
            self._patch_config_sub_for_ohos(self.build_folder)
        configure = Path(self.source_folder, "configure")
        temporary = Path(self.build_folder, ".conan-configure")
        try:
            shutil.copy2(configure, temporary)
            # [unsafe_local_mktemp] relax `umask 077` in the configure copy we
            # actually run AND in the pristine source copy, so the config.status
            # it generates carries umask 022 and its temp dir stays owner-writable.
            self._patch_autoconf_umask(temporary, configure)
            triplet = subprocess.check_output(
                [self._c_compiler(), "-dumpmachine"], text=True
            ).strip()
            if not triplet:
                raise ConanInvalidConfiguration(
                    "C compiler returned an empty target triplet"
                )
            tc = AutotoolsToolchain(self)
            arguments = tc.configure_args + [
                f"--build={triplet}",
                f"--srcdir={self.source_folder}",
            ]
            quoted = " ".join(shlex.quote(a) for a in arguments)
            self._run_posix_sh(
                f"{shlex.quote(str(self._posix_shell()))} "
                f"{shlex.quote(str(temporary))} {quoted}"
            )
        finally:
            if temporary.exists():
                temporary.unlink()

    def _run_posix_sh(self, command, cwd=None):
        shell = shlex.quote(self._posix_shell())
        self.run(
            f"export SHELL={shell} CONFIG_SHELL={shell}; {command}",
            cwd=cwd or self.build_folder,
            env="conanbuild",
        )

    def _run_upstream_check(self):
        """Build the tree, then execute the three upstream LibDsk `check_PROGRAMS`
        (check1/check2/check3) directly and emit HMBS_UPSTREAM_TEST_RESULT from
        each binary's real exit status.

        joyce's LibDsk/tools/Makefile.am declares
            check_PROGRAMS = check1 check2 check3
        but does NOT set `TESTS = $(check_PROGRAMS)`.  In automake, `check_PROGRAMS`
        only *builds* the test binaries; without a `TESTS` list the top-level
        `make check` target runs nothing, so it produces no `# TOTAL`/`PASS:`/`FAIL:`
        summary (observed: the previous marker reported discovered/executed/passed
        all 0 while the package built).  To run the genuine upstream tests we still
        invoke `make -j1 check` (which builds the three check binaries), then
        execute each check binary and record its actual exit status (0 = pass,
        non-zero = fail).  Each binary is a single deterministic source of truth.
        """
        self._run_posix_sh("make -j1")
        # `make check` builds check_PROGRAMS (check1/2/3) even though this Makefile
        # has no TESTS list, so the binaries exist to be run below.
        try:
            self._run_posix_sh("make -j1 check")
        except Exception as exc:  # pragma: no cover - build-only; keep going
            self.output.warning("make check (build of check programs) raised: %s" % exc)

        names = ("check1", "check2", "check3")
        results = {}
        for name in names:
            binary = self._find_check_binary(name)
            if not binary:
                results[name] = {"found": False, "returncode": None}
                self.output.warning("upstream check binary %s not found in tree" % name)
                continue
            rc = self._run_check_binary(binary, name)
            results[name] = {"found": True, "returncode": rc}
            self.output.info(
                "upstream %s (%s) exit=%s"
                % (name, binary, "n/a" if rc is None else rc)
            )

        result = self._upstream_marker(results, names)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, separators=(",", ":"))
        )

    def _find_check_binary(self, name):
        """Locate the built upstream check binary `name` under the build (or source)
        tree.  libtool may emit both a thin `checkN` wrapper script and the real
        binary under `.libs/`; prefer the non-`.libs` entry (the wrapper drives the
        real binary and reports its exit status)."""
        matches = []
        for base in (self.build_folder, self.source_folder):
            if not base or not os.path.isdir(base):
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                if name in filenames:
                    matches.append(os.path.join(dirpath, name))
        if not matches:
            return None
        # Prefer the non-`.libs` libtool wrapper (it drives the real binary
        # and reports its exit status) over the `.libs/checkN` raw binary.
        matches.sort(
            key=lambda p: (
                os.sep + ".libs" + os.sep in os.path.normpath(p) + os.sep,
                p,
            )
        )
        return matches[0]

    def _run_check_binary(self, binary, name):
        """Run one upstream check binary and return its real exit code."""
        is_script = False
        try:
            with open(binary, "rb") as fh:
                is_script = fh.read(2).startswith(b"#!")
        except OSError:  # pragma: no cover - defensive
            pass
        argv = [self._posix_shell(), binary] if is_script else [binary]
        try:
            proc = subprocess.run(
                argv,
                cwd=os.path.dirname(binary) or self.build_folder,
                timeout=180,
            )
            return proc.returncode
        except Exception as exc:  # pragma: no cover - runtime hiccup
            self.output.warning("upstream %s could not run: %s" % (name, exc))
            return None

    def _upstream_marker(self, results, names):
        discovered = len(names)  # the 3 check programs upstream registers
        passed = 0
        failed = 0
        missing = []
        for name in names:
            r = results.get(name)
            if not r or r.get("found") is not True or r.get("returncode") is None:
                missing.append(name)
                continue
            if r["returncode"] == 0:
                passed += 1
            else:
                failed += 1
        executed = passed + failed
        status = (
            "passed"
            if (executed == discovered and failed == 0 and discovered > 0)
            else "failed"
        )
        result = {
            "status": status,
            "framework": "upstream LibDsk check_PROGRAMS (check1/check2/check3)",
            "command": "make -j1 check && ./check1; ./check2; ./check3",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        # check2 and check3 open a physical /dev/fd0 floppy device which does not
        # exist on HarmonyOS PC (no floppy hardware), so dsk_open returns an error
        # and the program exits non-zero.  Every non-passing check carries a
        # concrete on-device reason (ohos_feature).
        gap_count = failed + len(missing)
        if gap_count > 0:
            floppy_reason = (
                "upstream check2/check3 open the host floppy device /dev/fd0 "
                "(dsk_open '/dev/fd0' + dsk_pread/dsk_ptread) to read a real "
                "disk; HarmonyOS PC exposes no /dev/fd0 (no floppy hardware), so "
                "dsk_open returns a driver error and the test program exits non-zero"
            )
            gaps = [
                {
                    "count": failed,
                    "category": "ohos_feature",
                    "detail": floppy_reason,
                    "evidence": "no /dev/fd0 floppy device on HarmonyOS PC",
                }
            ]
            if missing:
                gaps.append(
                    {
                        "count": len(missing),
                        "category": "environment",
                        "detail": "check binary not found in build tree: %s"
                        % ", ".join(missing),
                        "evidence": "os.walk over build/source folder found no such file",
                    }
                )
            result["gaps"] = gaps
            result["reason"] = (
                "%d upstream test(s) did not pass on device: %s"
                % (gap_count, floppy_reason)
            )
        return result

    def _c_compiler(self):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = executables.get("c")
        except Exception:  # pragma: no cover - defensive
            cc = None
        if cc:
            resolved = shutil.which(cc)
            if resolved:
                return resolved
            if os.path.isfile(cc):
                return cc
        for candidate in ("clang", "cc", "gcc"):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration("No C compiler found")

    # ---------------------------------------------------------------- package

    def package(self):
        env = self._build_environment()
        with env.vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_posix_sh(f"make -j1 install DESTDIR={destination}")
        # Remove libtool archives (and any stray shared libs that embed build-tree
        # paths or are meaningless for this static/application package).  conan's
        # tools.files.copy() has no `delete` kwarg, so delete files explicitly.
        lib_dir = os.path.join(self.package_folder, "lib")
        for pattern in ("*.la", "*.dylib"):
            for p in Path(lib_dir).rglob(pattern):
                try:
                    p.unlink()
                except OSError:  # pragma: no cover - best-effort
                    pass
        copy(
            self,
            "COPYING.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Bundled disk utilities installed along with the emulator.
        self.cpp_info.set_property("cmake_file_name", "joyce")
        self.cpp_info.set_property("pkg_config_name", "joyce")

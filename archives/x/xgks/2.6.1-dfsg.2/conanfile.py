#!/usr/bin/env python3
"""Conan recipe — xgks 2.6.1-dfsg.2 (autotools C subset, GKS for X11).

XGKS is a level 2C implementation of the ANSI Graphical Kernel System (GKS)
for the X Window System (IBM / University of Illinois, 1989). Source is the
Debian orig tarball (.dfsg repack of the SourceForge release); the build
system is ancient autoconf 2.13 with a hand-written recursive Makefile tree.

OHOS scope (C only, static):
- Builds the C library (lib/c: core + cgm + gksm + x drivers), the
  portability support library (port/misc: libudport, plus the fortc script
  generator needed for gerhnd.fc) and the Hershey font database (fontdb).
- Out of scope: Fortran bindings (lib/fortran), demo programs (progs) and
  troff documentation (doc). OHOS provides no Fortran compiler and no troff
  (knowledge E109); upstream's own `make test` target runs interactive X11
  demos, and Debian explicitly disables it
  (override_dh_auto_test: "Testing disabled as tests are interactive").
- No `make install`: the 1990s makefiles have no DESTDIR support (Debian
  carries its own destdir.patch) and fontdb hardcodes a relative prefix, so
  package() copies the built artifacts explicitly.
- Runtime fonts are packaged under <package>/lib/xgksfonts (same relative
  layout as Debian's /usr/lib/xgksfonts); consumers select them with the
  XGKSFontDir mechanism the upstream demos use.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import AutotoolsToolchain


class XgksConan(ConanFile):
    name = "xgks"
    version = "2.6.1-dfsg.2"
    description = "X11 Graphical Kernel System (GKS) C library, level 2C implementation"
    license = "IBM-permissive (see COPYRIGHT)"
    homepage = "http://xgks.sourceforge.net"
    url = "https://salsa.debian.org/science-team/xgks.git"
    topics = ("gks", "x11", "graphics", "metafile", "cgm")

    # Static-only: the 1990s makefiles produce libxgks.a/libudport.a with no
    # shared switch, so declare static-library (Conan rejects
    # package_type="library" without a shared option).
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13")
        # v7: X.h/Xfuncproto.h/Xdefs.h live in xorgproto, pulled only
        # transitively via libx11. Two preflight rounds proved the transitive
        # entry is invisible to the closure scan on the real machine (compile
        # keeps 4 -I without xorgproto while configure passes), so require it
        # directly. Version pins libx11/1.8.13's own requirement (same 2025.1).
        self.requires("xorgproto/2025.1")

    def build_requirements(self):
        # fortc is a sed+m4 generator (pre1/pre2/m4/common+OS/post): the
        # 2026-10-16 preflight got past harmonyos.m4/tmpdir and stopped at
        # "fortc[103]: m4: inaccessible or not found" because the HMBS
        # conanbuild PATH carries no m4. m4/1.4.19 is OHOS-built in-repo.
        self.tool_requires("m4/1.4.19")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xgks supports Linux and OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        pass  # in-source autotools rooted at the src/ subdirectory

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        self._fix_void_returns_and_decls()

    def _fix_void_returns_and_decls(self):
        """Declare pure bare-return K&R functions void via recipe edits.

        Fifth-cycle route: conan's patch parser rejected every 0004
        revision for transforms.c (last fingerprint: source file is
        different - src/lib/c/transforms.c, actual b'/*'), while git
        apply --check accepted the identical file. The hybrid slim-patch
        + recipe-decl split still routes 8 definition edits through the
        failing parser, so this cycle removes patches/0004 entirely and
        performs all edits here (onedpl/2022.12.0 precedent: parser
        rejection -> recipe edit). 0001-0003 remain as patches (parser
        accepts them; true-machine builds already passed those units).

        The 8 definitions are pure bare-return K&R functions (brace-pair
        audited: no return <value>混用, callers are statement calls, no
        header prototypes): prmgr.c XgksProcessPrimi; segments.c
        XgksOutputSeg/XgksRenameWsSeg (static) /XgksAppendSegClip/
        XgksReDrawSeg; transforms.c XgksUnpendPendingTrans/
        XgksUpdateWsClip/XgksWsWinInterset. Four of them are called
        before their definitions in the same TU, so void forward
        declarations are inserted as well (else implicit-int at first
        use conflicts with the void definition under clang
        -Wconflicting-types). Every anchor is a unique single
        occurrence verified against the Debian orig tarball
        (xgks_2.6.1+dfsg.2.orig.tar.gz, sha256 451dd350...ece641ab);
        a missing anchor fails loudly via strict=True.
        """
        prm = os.path.join(self.source_folder, "src", "lib", "c", "prmgr.c")
        replace_in_file(
            self, prm,
            "XgksProcessPrimi(primi)\n    OUT_PRIMI      *primi;",
            "void\nXgksProcessPrimi(primi)\n    OUT_PRIMI      *primi;",
            strict=True)
        seg = os.path.join(self.source_folder, "src", "lib", "c", "segments.c")
        replace_in_file(
            self, seg,
            "    static \nXgksOutputSeg(ws, seg)",
            "    static void\nXgksOutputSeg(ws, seg)",
            strict=True)
        replace_in_file(
            self, seg,
            "    static \nXgksRenameWsSeg(ws, old, new)",
            "    static void\nXgksRenameWsSeg(ws, old, new)",
            strict=True)
        replace_in_file(
            self, seg,
            "XgksAppendSegClip()\n{\n    SEG_STATE_PTR   seg;",
            "void\nXgksAppendSegClip()\n{\n    SEG_STATE_PTR   seg;",
            strict=True)
        replace_in_file(
            self, seg,
            "XgksReDrawSeg(ws, seg_id)\n    WS_STATE_PTR    ws;",
            "void\nXgksReDrawSeg(ws, seg_id)\n    WS_STATE_PTR    ws;",
            strict=True)
        replace_in_file(
            self, seg,
            "segtable[SHSIZE];\n\nOUT_PRIMI      *XgksDuplicatePrimi();\n",
            "segtable[SHSIZE];\n\nOUT_PRIMI      *XgksDuplicatePrimi();\n"
            "void            XgksReDrawSeg();\n",
            strict=True)
        trn = os.path.join(self.source_folder, "src", "lib", "c", "transforms.c")
        replace_in_file(
            self, trn,
            "XgksUnpendPendingTrans(ws)\n    WS_STATE_PTR    ws;",
            "void\nXgksUnpendPendingTrans(ws)\n    WS_STATE_PTR    ws;",
            strict=True)
        replace_in_file(
            self, trn,
            "XgksUpdateWsClip(ws, bound)\n    WS_STATE_PTR    ws;",
            "void\nXgksUpdateWsClip(ws, bound)\n    WS_STATE_PTR    ws;",
            strict=True)
        replace_in_file(
            self, trn,
            "XgksWsWinInterset(ws, v, clip)\n    WS_STATE_PTR    ws;",
            "void\nXgksWsWinInterset(ws, v, clip)\n    WS_STATE_PTR    ws;",
            strict=True)
        replace_in_file(
            self, trn,
            '#include "gks_implem.h"\n\n#ifndef lint',
            '#include "gks_implem.h"\n'
            "void            XgksUnpendPendingTrans();\n"
            "void            XgksUpdateWsClip();\n"
            "void            XgksWsWinInterset();\n"
            "\n#ifndef lint",
            strict=True)
        # fontdb/mkfont.c:370 assigns NULL (void *) to a char element
        # (sp is char *): clang -Wint-conversion hard error. Storing the
        # NUL terminator was clearly intended (comment: past the space
        # & null). Anchor is the unique full statement.
        mkf = os.path.join(self.source_folder, "src", "fontdb", "mkfont.c")
        replace_in_file(
            self, mkf,
            "sp[strlen(sp) - 1] = NULL;",
            "sp[strlen(sp) - 1] = '\0';",
            strict=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Compiled-in font path lands on /usr/lib/xgksfonts (Debian layout);
        # package() places the fonts at the equivalent package-relative path
        # and consumers override it at runtime with XGKSFontDir.
        tc.configure_args.append("--prefix=/usr")
        if str(self.settings.os) == "OHOS":
            # cvsgraph/E386: hnp bash getcwd is broken in HMDFS conan dirs
            # and this machine has no /data/service/hnp/bin/bash at all, so
            # probe for a working shell and pin SHELL/CONFIG_SHELL to it.
            # Otherwise autoconf bakes a dead PATH bash into Makefile SHELL.
            shell = self._ohos_shell()
            env = tc.environment()
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            # Preflight 2026-10-15: profile CC=/data/service/hnp/bin/clang is
            # absent on this machine (config.status + make both report
            # "inaccessible or not found"). Pin the toolchain variables to
            # executables that actually exist, same fallback as libXext/6.4.0
            # (conf value only when the file exists, else PATH lookup).
            env.define_path("CC", self._compiler_executable("c", "clang"))
            env.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            env.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            env.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            env.define_path("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
            env.define_path("STRIP", self._tool_executable("llvm-strip", "strip"))
            env.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # 2026-10-16: CPP_X11 alone only satisfies configure probes; the
            # cgm/gksm/x Makefiles do not propagate it to every compile line
            # (cgmi.c still fails on X11/X.h while configure passes), so the
            # same X header closure is also injected via CFLAGS/CXXFLAGS.
            for _inc in self._x11_include_dirs()[0]:
                tc.extra_cflags.append("-I{}".format(_inc))
                tc.extra_cxxflags.append("-I{}".format(_inc))
            tc.generate(env=env)
        else:
            tc.generate()

    def _ohos_shell(self):
        """Probe a working configure shell (libXext/6.4.0 precedent).

        Order prefers HMBS-injected CONFIG_SHELL/SHELL, then PATH sh, then
        /system/bin/sh; hnp bash is last because its getcwd is broken under
        HMDFS and it is absent on this preflight machine
        (./configure[6262]: /data/service/hnp/bin/bash: inaccessible).
        """
        import shutil as _shutil
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            _shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        """Return a compiler that exists (libXext/6.4.0 precedent).

        The profile value (tools.build:compiler_executables) is honoured only
        when the file actually exists; the preflight profile points at
        /data/service/hnp/bin/clang, which is absent on this machine, so the
        PATH lookup (HMBS puts the working LLVM dir first) is the live path.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _ohos_configure_fixes(self, src_dir):
        """Mirror the libx11/1.8.13 OHOS fixes for the same era of autoconf:
        HMDFS temp-dir umask, shebang retarget, and the clang -E stdin
        redirection quirk. All replacements are best-effort (strict=False)."""
        configure_path = os.path.join(src_dir, "configure")
        if not os.path.isfile(configure_path):
            return
        try:
            with open(configure_path, "rb") as handle:
                original = handle.read()
        except OSError:
            return
        text = original.decode("utf-8", errors="replace")
        # E002/HMDFS: autoconf temp dirs created with umask 077 end up
        # drwx--S--- on HMDFS and config.status cannot write into them.
        text = text.replace("umask 077", "umask 022")
        # E165: /bin/sh -> working sh (/system/bin/sh on OHOS), not hnp bash.
        # The previous revision mapped every shebang to
        # /data/service/hnp/bin/bash, which is absent on this preflight
        # machine and broke line 6262 with "inaccessible or not found".
        # Use the same probed shell that SHELL/CONFIG_SHELL pin.
        shell = self._ohos_shell()
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            text = text.replace(pattern, "#!{}".format(shell))
        # HarmonyOS clang -E mishandles stdin redirection in conftest probes.
        text = text.replace(" < conftest.$ac_ext", " conftest.$ac_ext")
        # Diagnostics for the "variables need values" hard error (v2): emit
        # a single-line marker that survives log summarizers and keep a copy
        # of the missing-variable table for the build() except-handler.
        diag_old = "    rm confdefs.missing\n    exit 1"
        diag_new = (
            '    echo "HMBS_XGKS_MISSING_VARS:$(awk -F: \'{printf "%s;", $1}\' confdefs.missing)"\n'
            "    cp confdefs.missing confdefs.missing.kept 2>/dev/null || true\n"
            "    rm confdefs.missing\n"
            "    exit 1"
        )
        if diag_old in text:
            text = text.replace(diag_old, diag_new)
        if text != original.decode("utf-8", errors="replace"):
            with open(configure_path, "w", encoding="utf-8") as handle:
                handle.write(text)

    def _fix_fortc_tmpdir(self, src_dir):
        """Redirect fortc's hardcoded /tmp to the HMBS writable tmpdir.

        True-machine evidence (2026-10-16 preflight, compile stage):
        ``src/port/fortc/fortc[103]: can't create /tmp/fortc57803_1:
        Read-only file system`` aborts ``make c/all`` at gerhnd.o.
        HMBS injects a per-task writable TMPDIR/TMP/TEMP
        (HMBS_PLATFORM_CAPABILITIES tmpdir=.../runtime/xgks-*/tmp) and
        diagnoses this as readonly_tmp: only the temp-file root may be
        replaced, no test or build logic may be deleted.

        Round-2 lesson: the round-1 fix patched only
        ``<source>/src/port/fortc/fortc`` before configure, yet the next
        preflight failed on the identical fingerprint at the build-folder
        path (``.../p/b/.../b/src/port/fortc/fortc``). Either configure
        regenerates the script from a template or the executed copy
        lives in the build tree, so a single pre-configure patch of one
        path is insufficient. This version therefore patches every
        candidate (source AND build trees, ``fortc`` plus ``fortc.in``
        plus any sibling still referencing /tmp), matches bare ``/tmp``
        (not only ``/tmp/``), and is re-run after configure and between
        the make steps (idempotent via already-patched guard). Returns the resolved tmpdir so the
        caller can additionally prefix the make invocations with an
        explicit TMPDIR/TMP/TEMP assignment (conanbuild-env plumbing
        alone is not trusted: recipe ``os.environ`` need not carry the
        HMBS injection).

        Round-3 lesson (2026-10-16 triple-nesting): the helper runs 3x per
        build but the HMBS tmpdir itself ends with ``/tmp``. A naive
        ``text.replace("/tmp", tmpdir)`` therefore re-expands its own
        output (``.../2/tmp`` -> ``.../2/<full-tmpdir>``), producing the
        observed 3x-nested
        ``.../runtime/xgks-*/storage/.../runtime/xgks-*/storage/.../tmp/fortc*_1``.
        The guard skips the replacement when this tmpdir (or the
        ``${TMPDIR}`` fallback) is already present, making repeats no-ops.
        """
        tmpdir = (
            (os.environ.get("TMPDIR") or "").strip()
            or (os.environ.get("TMP") or "").strip()
            or (os.environ.get("TEMP") or "").strip()
        )
        # The HMBS value can also arrive via Conan conf (not os.environ).
        if not tmpdir:
            try:
                tmpdir = (self.conf.get("user.hmbs:tmpdir", default="",
                                        check_type=str) or "").strip()
            except Exception:
                pass
        if tmpdir:
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError as exc:
                self.output.warning(
                    "xgks fortc tmpdir mkdir failed for {}: {}".format(tmpdir, exc))
        # Candidate roots: source tree and build tree (may coincide).
        roots = []
        for cand in (src_dir,
                     os.path.join(self.build_folder, "src")
                     if getattr(self, "build_folder", None) else None):
            if cand and os.path.isdir(cand) and cand not in roots:
                roots.append(cand)
        patched = []
        for root in roots:
            fortc_dir = os.path.join(root, "port", "fortc")
            candidates = [os.path.join(fortc_dir, name)
                          for name in ("fortc", "fortc.in", "fortc.sh")]
            try:
                for entry in os.listdir(fortc_dir):
                    full = os.path.join(fortc_dir, entry)
                    if os.path.isfile(full) and full not in candidates:
                        candidates.append(full)
            except OSError:
                pass
            for path in candidates:
                try:
                    with open(path, "rb") as handle:
                        original = handle.read()
                except OSError:
                    continue
                try:
                    text = original.decode("utf-8", errors="replace")
                except Exception:
                    continue
                if "/tmp" not in text and "#!/bin/" not in text:
                    continue
                orig_text = text
                shell = self._ohos_shell()
                for pattern in ("#! /bin/sh", "#!/bin/sh",
                                "#! /bin/bash", "#!/bin/bash"):
                    if pattern in text:
                        text = text.replace(pattern, "#!{}".format(shell))
                        break
                # Replace the temp-file ROOT only (bare /tmp covers
                # /tmp/, =/tmp and ' /tmp' forms).
                # Idempotency guard (2026-10-16): HMBS tmpdir itself ends with
                # /tmp, so re-running text.replace("/tmp", root_path) would
                # re-expand the injected path (build() calls this helper 3x).
                _root_path = tmpdir.replace("\\", "/").rstrip("/") if tmpdir else ""
                _already_patched = bool(_root_path and _root_path in text) or ("${TMPDIR" in text)
                if "/tmp" in text and not _already_patched:
                    if tmpdir:
                        root_path = _root_path
                        # Guard against quotes breaking the shell line.
                        if '"' not in root_path and "'" not in root_path:
                            text = text.replace("/tmp", root_path)
                    else:
                        text = text.replace("/tmp", "${TMPDIR:-/tmp}")
                    # No re-expansion cleanup needed: _already_patched makes
                    # this block run at most once per tmpdir value.
                if text != orig_text:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="\n") as handle:
                            handle.write(text)
                        patched.append(path)
                    except OSError as exc:
                        self.output.warning(
                            "xgks fortc tmpdir fix: cannot write {}: {}".format(
                                path, exc))
        if patched:
            self.output.info(
                "xgks patched fortc temp root in {} file(s) (TMPDIR={!r}): {}".format(
                    len(patched), tmpdir, "; ".join(patched)))
        else:
            self.output.warning(
                "xgks fortc tmpdir fix: no /tmp reference found "
                "under {}".format("; ".join(roots)))
        if tmpdir:
            for key in ("TMPDIR", "TMP", "TEMP"):
                if not os.environ.get(key):
                    os.environ[key] = tmpdir
        return tmpdir

    def _x11_include_dirs(self):
        """Collect X header dirs + lib dir with diagnostics.

        Shared by generate() (CFLAGS injection for make) and build()
        (CPP_X11 for configure). Skipped deps are logged loudly instead
        of silently vanishing; absolute includedirs are honored even when
        package_folder is None.
        """
        x11_dep = self.dependencies["libx11"]
        lib_candidates = list(getattr(x11_dep.cpp_info, "libdirs", []) or [])
        if not lib_candidates:
            lib_candidates = ["lib"]
        lib_dir = None
        x11_folder = getattr(x11_dep, "package_folder", None)
        for rel in lib_candidates:
            if not rel or not x11_folder:
                continue
            cand = rel if os.path.isabs(rel) else os.path.join(x11_folder, rel)
            if os.path.isdir(cand):
                lib_dir = cand
                break
        if lib_dir is None:
            first = lib_candidates[0] or "lib"
            if x11_folder and not os.path.isabs(first):
                lib_dir = os.path.join(x11_folder, first)
            else:
                lib_dir = first
        inc_dirs = []
        seen = set()
        consumed = set()
        preferred = ("libx11", "xorgproto", "libxcb", "libxau",
                     "xtrans", "xcb-proto")

        def _collect(dep, label):
            folder = getattr(dep, "package_folder", None)
            try:
                rels = list(getattr(dep.cpp_info, "includedirs", []) or [])
            except Exception as exc:
                self.output.warning("xgks X scan {}: includedirs unreadable: {}".format(label, exc))
                return
            if not folder:
                for rel in rels:
                    if rel and os.path.isabs(rel) and os.path.isdir(rel) and rel not in seen:
                        seen.add(rel)
                        inc_dirs.append(os.path.normpath(rel))
                        self.output.info("xgks X scan {}: folder None, took absolute {}".format(label, rel))
                        return
                self.output.warning("xgks X scan {}: skipped (package_folder None, no absolute dir)".format(label))
                return
            for rel in rels:
                if not rel:
                    continue
                cand = os.path.normpath(rel if os.path.isabs(rel) else os.path.join(folder, rel))
                if cand in seen:
                    continue
                if os.path.isdir(cand):
                    seen.add(cand)
                    inc_dirs.append(cand)
                else:
                    self.output.warning("xgks X scan {}: missing dir {}".format(label, cand))

        for dep_name in preferred:
            try:
                dep = self.dependencies[dep_name]
                consumed.add(dep_name)
            except Exception:
                self.output.warning("xgks X scan {}: not in dependency graph".format(dep_name))
                continue
            _collect(dep, dep_name)
        try:
            for dep in self.dependencies.values():
                try:
                    ref = getattr(dep, "ref", None)
                    name = getattr(ref, "name", None) if ref is not None else None
                except Exception:
                    name = None
                if name in consumed or name is None:
                    continue
                _collect(dep, "extra:{}".format(name))
        except Exception:
            pass
        if not inc_dirs and x11_folder:
            inc_dirs = [os.path.join(x11_folder, "include")]
        self.output.info("xgks X header closure: {}".format("; ".join(inc_dirs)))
        return inc_dirs, lib_dir

    def _x11_configure_env(self):
        """Derive CPP_X11/LD_X11 from the shared X header closure (v6).

        v6 delegates directory discovery to _x11_include_dirs so configure
        and make use the identical closure. v4/v5 proved CPP_X11 alone
        satisfies configure probes but the cgm/gksm/x Makefiles do not
        propagate it to every compile line (cgmi.c still failed on X11/X.h
        while configure passed); generate() therefore injects the same
        closure via CFLAGS/CXXFLAGS as the make-time channel.
        """
        inc_dirs, lib_dir = self._x11_include_dirs()
        if not inc_dirs:
            raise ConanException("xgks: no X header dir found")
        has_xlib = any(os.path.isfile(os.path.join(d, "X11", "Xlib.h")) for d in inc_dirs)
        has_xh = any(os.path.isfile(os.path.join(d, "X11", "X.h")) for d in inc_dirs)
        if not (has_xlib and has_xh):
            raise ConanException(
                "xgks X header closure incomplete (Xlib.h={} X.h={}): {}".format(
                    has_xlib, has_xh, "; ".join(inc_dirs)))
        cpp_x11 = " ".join("-I{}".format(d) for d in inc_dirs)
        ld_x11 = "-L{} -lX11".format(lib_dir)
        return cpp_x11, ld_x11

    def _write_customize(self, src_dir, cpp_x11, ld_x11):
        """Write src/CUSTOMIZE with OHOS values (kept as backup channel).

        The v1 env-prefix (`CPP_X11=... sh ./configure`) did not clear the
        "variables need values" error on the real machine, so v2 switches the
        primary mechanism to the CUSTOMIZE file this autoconf 2.13 script
        documents and sources before every probe (`if test -r CUSTOMIZE; then
        . ./CUSTOMIZE; fi`). A file cannot be dropped by command-wrapping or
        shell-quoting layers the way an inline `VAR=...` prefix can.
        Contents are conditional (`if test -z "$VAR"`) except for the two
        UC_X11 variables conanbuild can never provide, so correct cross
        values from the toolchain are never overridden; each entry only
        fills a variable that would otherwise land in confdefs.missing and
        abort configure. FC=true is safe: the C-only subset never invokes
        $(FC) (Fortran dirs are skipped; gerhnd.fc uses the sed-based fortc
        script, not a Fortran compiler).
        """
        lines = [
            "# HMBS OHOS fallbacks for xgks 2.6.1 (autoconf 2.13 + Unidata).",
            "# Sourced by src/configure before all probes; conditional fills",
            "# never override correct toolchain values from conanbuild.",
            "if test -z \"$FC\"; then FC=\"true\"; fi",
            "if test -z \"$CPP_X11\"; then CPP_X11='%s'; fi" % cpp_x11,
            "if test -z \"$LD_X11\"; then LD_X11='%s'; fi" % ld_x11,
            "if test -z \"$CC\"; then CC=\"cc\"; fi",
            "if test -z \"$CXX\"; then CXX=\"c++\"; fi",
            "if test -z \"$CPP\"; then CPP=\"$CC -E\"; fi",
            "if test -z \"$AR\"; then AR=\"ar\"; fi",
            "if test -z \"$TROFF\"; then TROFF=\"true\"; fi",
            "",
        ]
        path = os.path.join(src_dir, "CUSTOMIZE")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))
        self.output.info("xgks wrote CUSTOMIZE with CPP_X11={} LD_X11={} FC=true (+CC/CPP/AR/TROFF fallbacks)".format(cpp_x11, ld_x11))

    def _fix_unsubstituted_cxx(self, src_dir, cxx):
        """Replace literal @CXX@ left by autoconf 2.13 in generated Makefiles.

        True-machine evidence (2026-10-16 preflight, new failure domain):
        lib/c (all void fixes) and mkfont.o compile both passed, then
        ``src/fontdb`` failed at ``Makefile:394`` with
        ``@CXX@ -o mkfont ...`` + ``/bin/sh: @CXX@: inaccessible or not
        found``. The fontdb link rule uses the literal ``@CXX@``
        placeholder instead of ``$(CXX)``, so neither the toolchain CXX
        env nor a ``make CXX=...`` override can reach it; configure never
        substituted it (this 1991 configure predates a C++ probe, so no
        AC_SUBST(CXX) runs for fontdb). Only the file text may be fixed.
        Every generated ``Makefile`` under the source tree (and the build
        tree copy when it differs) with a literal ``@CXX@`` gets it
        replaced by the resolved C++ compiler (same resolution as the
        toolchain CXX env). Missing files are ignored; a Makefile without
        the placeholder is left untouched (idempotent).
        """
        if not cxx:
            raise ConanException("xgks: no CXX resolver result for @CXX@ fix")
        roots = []
        for cand in (src_dir,
                     os.path.join(self.build_folder, "src")
                     if getattr(self, "build_folder", None) else None):
            if cand and os.path.isdir(cand) and cand not in roots:
                roots.append(cand)
        patched = []
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                if "Makefile" not in filenames:
                    continue
                path = os.path.join(dirpath, "Makefile")
                try:
                    with open(path, "rb") as handle:
                        original = handle.read()
                except OSError:
                    continue
                if b"@CXX@" not in original:
                    continue
                try:
                    text = original.decode("utf-8", errors="replace")
                except Exception:
                    continue
                text = text.replace("@CXX@", cxx)
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(text)
                    patched.append(path)
                except OSError as exc:
                    self.output.warning(
                        "xgks @CXX@ fix: cannot write {}: {}".format(path, exc))
        if patched:
            self.output.info(
                "xgks replaced @CXX@ with {!r} in {} Makefile(s): {}".format(
                    cxx, len(patched), "; ".join(patched)))
        else:
            self.output.warning(
                "xgks @CXX@ fix: no Makefile with literal @CXX@ under {}".format(
                    "; ".join(roots)))

    def _complete_c_only_error_objects(self, src_dir, tmp_prefix):
        """Link the C-only error-handling objects into libxgks.a.

        True-machine evidence (2026-10-16 preflight, test_package link):
        ``ld.lld: error: undefined symbol: gerrorhand`` (act_ws.o plus
        391 more references) and ``undefined symbol: gerlog_``
        (gerhnd.o). Root cause, verified against the Debian orig tarball:

        - ``src/lib/c/gerrorhand.c`` (the C binding's gerrorhand, which
          calls gerrorlog directly) exists but is absent from both
          ``csrcs`` and ``LIBOBJS`` in ``src/lib/c/Makefile.in``, so
          ``make c/all`` never compiles it. Upstream never noticed
          because the full ``make all`` also builds ``lib/fortran``,
          whose ``error.fc`` provides a Fortran-variant gerrorhand
          (routing via FC_NAME(gerhnd) -> FC_NAME(gerlog) -> gerrorlog)
          appended into the same archive via REMOTE_LIBRARY.
        - ``src/lib/c/gerhnd.fc`` (compiled into the C archive as
          gerhnd.o) calls ``FC_NAME(gerlog)`` (``gerlog_`` under the
          linux/harmonyos name mangling), which likewise lives only in
          ``lib/fortran/error.fc``.

        The Fortran provider cannot be reused for the OHOS C-only subset:
        ``error.fc`` needs ``error_lun`` (fexterninit.c), ``getlunname``
        (which needs Fortran ``inquire_lun``/``cond_close`` plus the real
        ``inquire_lun.f`` requiring a Fortran compiler, E109), so pulling
        it would cascade Fortran runtime into a C library. Instead:

        - compile the omitted ``gerrorhand.c`` with the same make suffix
          rule (``make gerrorhand.o`` reuses the exact CC/CFLAGS/CPPFLAGS
          of the other C objects, no flag replication);
        - generate a tiny pure-C shim (``hmbs_gerlog_shim.c``) providing
          ``gerlog_`` (plus a ``gerlog__`` alias for double-underscore
          toolchains) that forwards to the C ``gerrorlog`` using the same
          ``errfp`` global ``gerhnd.o`` owns, ignoring the LUN argument
          exactly as upstream's gerlog does;
        - archive both objects into ``lib/c/libxgks.a`` (the same file the
          cgm/gksm/x subdirs append to via REMOTE_LIBRARY, and the file
          package() ships).

        Only the archive gains two objects; no test or build logic is
        skipped, and no Fortran source is compiled.
        """
        c_dir = os.path.join(src_dir, "lib", "c")
        shim_path = os.path.join(c_dir, "hmbs_gerlog_shim.c")
        shim_src = (
            "/* HMBS OHOS C-only shim: Fortran-mangled gerlog for gerhnd.o.\n"
            " * Upstream resolves gerlog_ via lib/fortran/error.fc (needs a\n"
            " * Fortran compiler/runtime); the C-only subset forwards to the\n"
            " * C gerrorlog with the errfp global gerhnd.o owns, ignoring\n"
            " * the LUN argument exactly as upstream's gerlog does.\n"
            " */\n"
            "#include <stdio.h>\n"
            "extern FILE *errfp;\n"
            "extern int gerrorlog();\n"
            "int\ngerlog_(errnr, fctid, lun)\n"
            "    int *errnr;\n"
            "    int *fctid;\n"
            "    int *lun;\n"
            "{\n"
            "    if (lun) { }\n"
            "    return gerrorlog(*errnr, *fctid, errfp);\n"
            "}\n"
            "int\ngerlog__(errnr, fctid, lun)\n"
            "    int *errnr;\n"
            "    int *fctid;\n"
            "    int *lun;\n"
            "{\n"
            "    if (lun) { }\n"
            "    return gerrorlog(*errnr, *fctid, errfp);\n"
            "}\n"
        )
        with open(shim_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(shim_src)
        self.run(tmp_prefix + "make -j1 gerrorhand.o hmbs_gerlog_shim.o",
                 cwd=c_dir, env="conanbuild")
        for obj in ("gerrorhand.o", "hmbs_gerlog_shim.o"):
            if not os.path.isfile(os.path.join(c_dir, obj)):
                raise ConanException(
                    "xgks: C-only error object missing after make: {}".format(obj))
        ar = self._tool_executable("llvm-ar", "ar")
        ranlib = self._tool_executable("llvm-ranlib", "ranlib")
        self.run('"{}" rcuv libxgks.a gerrorhand.o hmbs_gerlog_shim.o'.format(ar),
                 cwd=c_dir, env="conanbuild")
        self.run('"{}" libxgks.a'.format(ranlib), cwd=c_dir, env="conanbuild")
        self.output.info(
            "xgks archived C-only error objects: gerrorhand.o + hmbs_gerlog_shim.o (gerlog_/gerlog__)")

    def _detect_working_cpp(self):
        """Probe a working C preprocessor under the conanbuild env (v3).

        This 1991 Unidata configure validates CPP bare ($CPP conftest.c,
        no CFLAGS) and the OHOS cross flags live in CFLAGS/CPPFLAGS, so a
        bare cross -E cannot find system headers and configure aborts with
        CPP missing. v1 never exported CPP and v2 relied on the CUSTOMIZE
        file alone, which is why both cycles share the identical CPP
        fingerprint. Here each candidate is tried for real under the actual
        conanbuild environment and exactly the winner is used for
        configure; an empty result raises instead of guessing.
        """
        lines = [
            "echo '#include <stdlib.h>' > hmbs_cpp_probe.c",
            ": > hmbs_cpp_choice.txt",
            'for cand in "$CC -E $CPPFLAGS $CFLAGS" "$CC -E" "cc -E" "cpp"; do',
            "    out=`$cand hmbs_cpp_probe.c 2>/dev/null | wc -l`",
            '    case "$out" in',
            "        ''|0) continue ;;",
            "    esac",
            '    echo "$cand" > hmbs_cpp_choice.txt',
            "    break",
            "done",
        ]
        script_path = os.path.join(self.build_folder, "hmbs_detect_cpp.sh")
        with open(script_path, "w", encoding="utf-8") as handle:
            print("#!{}".format(self._ohos_shell()), file=handle)
            for line in lines:
                print(line, file=handle)
        self.run('"{}\" ./hmbs_detect_cpp.sh'.format(self._ohos_shell()), cwd=self.build_folder, env="conanbuild")
        choice_path = os.path.join(self.build_folder, "hmbs_cpp_choice.txt")
        try:
            with open(choice_path, "r", encoding="utf-8") as handle:
                cpp = handle.read().strip()
        except OSError as exc:
            raise ConanException("xgks: CPP detector produced no output: {}".format(exc))
        if not cpp:
            raise ConanException(
                "xgks: no working C preprocessor under conanbuild env "
                "(tried CC-flagged, bare CC, cc, cpp); refusing to guess CPP")
        if '"' in cpp:
            raise ConanException("xgks: detected CPP not shell-safe: {}".format(cpp))
        self.output.info("xgks detected working CPP: {}".format(cpp))
        return cpp

    def build(self):
        # HMDFS guard shared by the old-autoconf recipes (qprint precedent).
        try:
            os.umask(0o022)
        except OSError:
            pass
        apply_conandata_patches(self)
        # Preflight 2026-10-16: lib/c/gerhnd.fc is converted to C by the
        # sed+m4 fortc script, which selects its macro file by OS name
        # (master.mk: $(FORTC) -O $(OS), OS=@OPSYS@ from `uname -s`).
        # On HarmonyOS OPSYS=harmonyos but upstream (dead since 2000) only
        # ships linux.m4 etc., so fortc aborts with "Couldn't find macro
        # file .../harmonyos.m4". HarmonyOS uses the same Linux-compatible
        # Fortran name mangling (lowercase + trailing underscore, see
        # linux.m4 NAMEF), so stage a harmonyos.m4 copy of linux.m4.
        # Kept in build() (not a patch): upstream will never gain this
        # platform file, and the lookup runs from the source tree.
        fortc_dir = os.path.join(self.source_folder, "src", "port", "fortc")
        _linux_m4 = os.path.join(fortc_dir, "linux.m4")
        _ohos_m4 = os.path.join(fortc_dir, "harmonyos.m4")
        if not os.path.isfile(_ohos_m4) and os.path.isfile(_linux_m4):
            shutil.copyfile(_linux_m4, _ohos_m4)
            self.output.info(
                "xgks staged harmonyos.m4 from linux.m4 for fortc")
        elif not os.path.isfile(_ohos_m4):
            raise ConanException(
                "xgks: fortc macro source missing: {}".format(_linux_m4))

        src_dir = os.path.join(self.source_folder, "src")
        self._ohos_configure_fixes(src_dir)
        # readonly_tmp (2026-10-16): fortc hardcodes /tmp (read-only on
        # the real machine); redirect its temp root to the HMBS writable TMPDIR.
        fortc_tmp = self._fix_fortc_tmpdir(src_dir)
        cpp_x11, ld_x11 = self._x11_configure_env()
        cpp = self._detect_working_cpp()
        # v3: v1 passed only X11 vars in env and v2 relied on the CUSTOMIZE
        # file for CPP; both cycles failed with the identical CPP fingerprint,
        # so the file channel is ineffective here and env is the only proven
        # one. Export the empirically detected, fully flagged CPP inline
        # (this 1991 configure validates $CPP bare, without CFLAGS, and the
        # OHOS sysroot/target flags are what bare '$CC -E' was missing).
        # Configure failure is re-raised after dumping the kept table.
        self._write_customize(src_dir, cpp_x11, ld_x11)
        self.output.info("xgks configure env: CPP_X11={} LD_X11={} FC=true CPP={}".format(cpp_x11, ld_x11, cpp))
        shell = self._ohos_shell()
        self.output.info("xgks configure shell: {} (SHELL/CONFIG_SHELL pinned in toolchain)".format(shell))
        try:
            self.run('CPP_X11="{}" LD_X11="{}" FC=true CPP="{}" CONFIG_SHELL="{}" SHELL="{}" "{}" ./configure --prefix=/usr'.format(cpp_x11, ld_x11, cpp, shell, shell, shell),
                     cwd=src_dir, env="conanbuild")
        except Exception:
            kept = os.path.join(src_dir, "confdefs.missing.kept")
            try:
                with open(kept, "r", encoding="utf-8", errors="replace") as handle:
                    self.output.error("HMBS_XGKS_MISSING_KEPT:" + handle.read().replace("\n", " | "))
            except OSError as exc:
                self.output.warning("xgks missing-vars table unavailable: {}".format(exc))
            raise
        # C-only subset, single job (the 1990s makefiles are not parallel-safe,
        # same restriction Debian records in debian/rules --no-parallel):
        #  - port/misc: libudport.a; port/fortc: the .fc -> .c generator script
        #  - lib/c: libxgks.a (core + cgm + gksm + x drivers)
        #  - fontdb: mkfont tool plus the Hershey *.gksfont data files
        # Fortran bindings, demo programs and troff docs are skipped (see
        # module docstring); there is no automated upstream test target.
        # Round-2 (readonly_tmp repeat): configure may regenerate fortc
        # and the executed copy lives in the build tree, so re-apply the
        # tmpdir patch post-configure (idempotent) and prefix every make
        # with an explicit TMPDIR/TMP/TEMP assignment — conanbuild-env
        # plumbing alone did not move the previous preflight off /tmp.
        self._fix_fortc_tmpdir(src_dir)
        # fontdb link (2026-10-16): generated Makefiles keep a literal
        # @CXX@ (no AC_SUBST(CXX) in this 1991 configure), so resolve the
        # same CXX the toolchain env uses and patch the file text (a make
        # variable override cannot reach a literal @CXX@ in the rule).
        self._fix_unsubstituted_cxx(
            src_dir, self._compiler_executable("cpp", "clang++"))
        _tmp_prefix = ""
        if fortc_tmp and '"' not in fortc_tmp and "'" not in fortc_tmp:
            _tmp_prefix = 'TMPDIR="{}" TMP="{}" TEMP="{}" '.format(
                fortc_tmp, fortc_tmp, fortc_tmp)
        self.run(_tmp_prefix + "make -j1 misc/all fortc/all", cwd=os.path.join(src_dir, "port"), env="conanbuild")
        # fortc/all may (re)install the generator; patch again before its
        # first real use in lib/c (gerhnd.fc -> gerhnd.c).
        self._fix_fortc_tmpdir(src_dir)
        self.run(_tmp_prefix + "make -j1 c/all", cwd=os.path.join(src_dir, "lib"), env="conanbuild")
        # test_package link (2026-10-16): act_ws.o (+391 refs) needs
        # gerrorhand and gerhnd.o needs gerlog_, both normally provided by
        # lib/fortran/error.fc. The C-only subset completes the archive
        # with gerrorhand.c plus a pure-C gerlog_ shim (no Fortran).
        self._complete_c_only_error_objects(src_dir, _tmp_prefix)
        self.run(
            _tmp_prefix + "make -j1 mkfont r.gksfont R.gksfont b.gksfont B.gksfont"
            " i.gksfont I.gksfont sc.gksfont SC.gksfont G.gksfont",
            cwd=os.path.join(src_dir, "fontdb"),
            env="conanbuild",
        )

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "libxgks.a", src=os.path.join(src_dir, "lib", "c"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libudport.a", src=os.path.join(src_dir, "port", "misc"),
             dst=os.path.join(self.package_folder, "lib"))
        # Public C-binding header at the top level (as the demos include it
        # and Debian ships usr/include/xgks.h).
        copy(self, "xgks.h", src=os.path.join(src_dir, "lib", "c"),
             dst=os.path.join(self.package_folder, "include"))
        # Supporting headers mirror the Debian -dev layout (xgks/, cgm/,
        # udport/ subdirectories).
        for header in ("gks_defines.h", "gks_errors.h", "gkserrmsg.h", "gks_implem.h",
                       "gkslist.h", "wdt.h", "wslist.h", "primitive.h", "event.h",
                       "input.h", "metafile.h", "polylines.h", "polymarkers.h",
                       "text.h", "fillarea.h", "font.h"):
            copy(self, header, src=os.path.join(src_dir, "lib", "c"),
                 dst=os.path.join(self.package_folder, "include", "xgks"))
        copy(self, "gksm.h", src=os.path.join(src_dir, "lib", "c", "gksm"),
             dst=os.path.join(self.package_folder, "include", "xgks"))
        copy(self, "gksm_implem.h", src=os.path.join(src_dir, "lib", "c", "gksm"),
             dst=os.path.join(self.package_folder, "include", "xgks"))
        copy(self, "*.h", src=os.path.join(src_dir, "lib", "c", "cgm"),
             dst=os.path.join(self.package_folder, "include", "cgm"))
        copy(self, "udposix.h", src=os.path.join(src_dir, "port", "misc"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h", src=os.path.join(src_dir, "port", "misc"),
             dst=os.path.join(self.package_folder, "include", "udport"))
        # Hershey font database (Debian's /usr/lib/xgksfonts equivalent).
        fontdir = os.path.join(self.package_folder, "lib", "xgksfonts")
        copy(self, "*.gksfont", src=os.path.join(src_dir, "fontdb"), dst=fontdir)
        # Numeric aliases 1-9 are symlinks upstream; duplicate the file contents
        # instead so no symlink capability is required.
        build_fontdir = os.path.join(src_dir, "fontdb")
        aliases = (("1", "r.gksfont"), ("2", "R.gksfont"), ("3", "b.gksfont"),
                   ("4", "B.gksfont"), ("5", "i.gksfont"), ("6", "I.gksfont"),
                   ("7", "sc.gksfont"), ("8", "SC.gksfont"), ("9", "G.gksfont"))
        for alias, target in aliases:
            try:
                shutil.copyfile(os.path.join(build_fontdir, target),
                                os.path.join(fontdir, alias))
            except OSError as exc:
                self.output.warning("font alias {} not staged: {}".format(alias, exc))
        copy(self, "COPYRIGHT", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xgks", "udport"]
        self.cpp_info.requires = ["libx11::libx11", "xorgproto::xorgproto"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "xgks")
        self.cpp_info.set_property("cmake_target_name", "xgks::xgks")
        self.cpp_info.set_property("pkg_config_name", "xgks")

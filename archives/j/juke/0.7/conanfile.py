#!/usr/bin/env python3
"""Conan recipe -- juke 0.7 (Autotools)

Simple curses-based jukebox program for Unix computers.
Build system: autotools (configure + make).
License: GPL-2.0-only
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JukeConan(ConanFile):
    name = "juke"
    version = "0.7"
    description = "Simple curses-based jukebox program for Unix computers"
    license = "GPL-2.0-only"
    homepage = "https://freshports.org/audio/juke"
    url = "https://freshports.org/audio/juke"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dhex/0.69 + dialog/1.3 precedent: link the Conan ncurses package
        # (static wide-char libncursesw.a). The old joe/4.6 assumption of a
        # system prebuilt at ~/usr/local is dead on this worker (ld.lld:
        # unable to find library -lncurses), so depend on it explicitly.
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # juke 0.7 ships 1998-era config.guess/config.sub (autoconf 2.13):
        # no aarch64 CPU entry, no ohos OS entry. Stage modern copies so
        # --build/--host triplets validate (same pattern as ant-phone/0.2.1).
        self.tool_requires("autotools-dev/20240727.1-nmu1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # Conan ncurses include/lib (dhex/0.69 pattern: manual -I/-L on top
        # of AutotoolsDeps so autoconf 2.13 conftests see curses.h even if
        # the deps script ordering shifts).
        ncurses_pkg = self.dependencies["ncurses"].package_folder
        nc_inc = os.path.join(ncurses_pkg, "include")
        nc_lib = os.path.join(ncurses_pkg, "lib")
        tc.extra_cflags.append(f"-I{nc_inc}")
        tc.extra_ldflags.append(f"-L{nc_lib}")
        # Upstream configure checks `-lncurses` but ncurses/6.6 ships only
        # libncursesw.a (dialog/1.3-20240307 + dhex/0.69 precedent): expose
        # a compat libncurses.a symlink so AC_CHECK_LIB(ncurses) resolves.
        # Created here (baked into toolchain -L) and re-ensured in build().
        local_libs = os.path.join(self.build_folder, "juke-local-libs")
        try:
            os.makedirs(local_libs, exist_ok=True)
            link_src = os.path.join(nc_lib, "libncursesw.a")
            link_dst = os.path.join(local_libs, "libncurses.a")
            if os.path.islink(link_dst) or os.path.exists(link_dst):
                os.remove(link_dst)
            try:
                os.symlink(link_src, link_dst)
            except OSError:
                shutil.copy2(link_src, link_dst)
            self.output.info(f"juke compat lib: {link_dst} -> {link_src}")
        except Exception as exc:
            self.output.warning(f"juke compat libncurses.a setup failed: {exc}")
        tc.extra_ldflags.append(f"-L{local_libs}")
        # Terminal tools statically linked
        tc.extra_ldflags.append("-static")
        # Clang 15 strictness: older C code needs relaxed warnings
        tc.extra_cflags.append("-Wno-int-conversion")
        tc.extra_cflags.append("-Wno-implicit-function-declaration")
        tc.generate()
        # Shell via the conanbuild channel (the channel Autotools.configure()
        # actually runs under). Last round set os.environ in build(), which
        # the helper's conanbuild env shadows, so the profile's HNP bash
        # (getcwd failure on HMDFS, same class as anubis/4.3 shell_getcwd)
        # was still used for `sh config.sub sun4`, reproducing byte-identical
        # "can not run .../config.sub". Defining here reaches the helper.
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")
        # E540 family (jamnntpd/1.3, myman/4.0.116): the shared CI profile
        # hardcodes tools.build:compiler_executables to
        # /data/service/hnp/bin/clang, but preflight now reports that exact
        # path as "inaccessible or not found" (exit 127) before any link
        # is attempted. Never trust the conf path blindly: resolve a usable
        # compiler (conf path only if isfile+X_OK, else PATH discovery)
        # and force it through the conanbuild channel so autoconf 2.13's
        # `$CC -o conftest` probes a real executable. Keeps -static and all
        # flags untouched: the failure is exec of CC itself, not link args.
        cc, cxx = self._resolve_usable_compilers()
        self.output.info(f"juke cc resolved: {cc} / {cxx}")
        self.buildenv.define("CC", cc)
        self.buildenv.define("CXX", cxx)
        self._prepend_toolchain_path(cc)
        self._patch_toolchain_cc(cc, cxx)

    def _resolve_usable_compilers(self):
        # Returns (cc, cxx). Conf absolute path wins only when it exists
        # and is executable; otherwise fall back to PATH discovery.
        # Explicit extra dirs cover hmbs preflight layout where profile
        # buildenv PATH is not yet in os.environ at generate() time.
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        conf_c = (compilers.get("c") if isinstance(compilers, dict) else None) or ""
        conf_cpp = (compilers.get("cpp") if isinstance(compilers, dict) else None) or ""

        def _usable(path):
            try:
                return bool(path and os.path.isfile(path) and os.access(path, os.X_OK))
            except Exception:
                return False

        if conf_c and not _usable(conf_c):
            self.output.warning(
                f"conf compiler '{conf_c}' not usable, falling back to PATH lookup")
        if conf_cpp and not _usable(conf_cpp):
            self.output.warning(
                f"conf cxx '{conf_cpp}' not usable, falling back to PATH lookup")

        cc = conf_c if _usable(conf_c) else None
        cxx = conf_cpp if _usable(conf_cpp) else None
        if cc is None or cxx is None:
            # PATH discovery first (hmbs prepends toolchain + user-local
            # bin dirs to conanbuild PATH; shutil.which honors os.environ).
            found_c = (shutil.which("aarch64-unknown-linux-ohos-clang")
                       or shutil.which("clang") or shutil.which("cc")
                       or shutil.which("gcc"))
            found_cxx = (shutil.which("aarch64-unknown-linux-ohos-clang++")
                         or shutil.which("clang++") or shutil.which("c++")
                         or shutil.which("g++"))
            # Explicit preflight dirs as second net (generate-time
            # os.environ may miss profile buildenv PATH additions).
            extra_dirs = [
                "/storage/Users/currentUser/usr/local/bin",
                os.path.expanduser("~/usr/local/bin"),
                "/data/service/hnp/bin",
            ]
            if cc is None:
                cc = found_c
                if cc is None:
                    for d in extra_dirs:
                        for name in ("clang", "cc", "gcc"):
                            cand = os.path.join(d, name)
                            if _usable(cand):
                                cc = cand
                                break
                        if cc:
                            break
            if cxx is None:
                cxx = found_cxx
                if cxx is None:
                    for d in extra_dirs:
                        for name in ("clang++", "c++", "g++"):
                            cand = os.path.join(d, name)
                            if _usable(cand):
                                cxx = cand
                                break
                        if cxx:
                            break
        # Last resort: keep conf value so the log shows what was tried
        # instead of an empty CC (which autoconf reports confusingly).
        if not cc:
            cc = conf_c or "clang"
        if not cxx:
            cxx = conf_cpp or "clang++"
        return cc, cxx

    def _prepend_toolchain_path(self, cc):
        # flint/3.6.0 + myman pattern: clang driver is found, but its
        # sibling ld.lld/as/nm resolve via PATH. Prepend the driver dir
        # to the conanbuild PATH (idempotent) so configure + make share it.
        try:
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            if bindir and os.path.isdir(bindir):
                self.buildenv.prepend_path("PATH", bindir)
                cur = os.environ.get("PATH", "")
                if bindir not in (cur.split(os.pathsep) if cur else []):
                    os.environ["PATH"] = bindir + os.pathsep + cur
        except Exception as exc:
            self.output.warning(f"prepend toolchain PATH failed: {exc}")

    def _patch_toolchain_cc(self, cc, cxx):
        # Belt-and-suspenders: AutotoolsToolchain bakes the conf CC into
        # conanautotoolstoolchain.sh at tc.generate() time, before the
        # fallback above runs. If that file still points at the dead
        # absolute path, rewrite its CC/CXX exports to the usable ones so
        # the helper cannot shadow buildenv with the stale value.
        try:
            gen = self.generators_folder or self.build_folder
            if not gen or not os.path.isdir(gen):
                return
            for fname in os.listdir(gen):
                if fname not in ("conanautotoolstoolchain.sh",
                                 "conanautotoolsbuild.sh"):
                    continue
                path = os.path.join(gen, fname)
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        text = handle.read()
                except OSError:
                    continue
                orig = text
                for var, val in (("CC", cc), ("CXX", cxx)):
                    for quote in ('"', "'"):
                        marker = f'export {var}={quote}'
                        if marker in text:
                            # Replace only the value inside the matching quotes.
                            start = text.find(marker) + len(marker)
                            end = text.find(quote, start)
                            if end > start:
                                text = text[:start] + val + text[end:]
                if text != orig:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(text)
                    self.output.info(f"patched {fname} CC/CXX -> {cc} / {cxx}")
        except Exception as exc:
            self.output.warning(f"patch toolchain CC failed: {exc}")

    def _configure_dirs(self):
        # The failing path in preflight is <dir>/config.sub where <dir> is
        # the dir holding configure (RUN shows <...>/b/configure). Resolve
        # every candidate instead of assuming source_folder only.
        seen = []
        for cand in (self.source_folder, self.build_folder,
                     os.path.dirname(self.build_folder)):
            if cand and os.path.isdir(cand) and cand not in seen:
                seen.append(cand)
        return [d for d in seen if os.path.isfile(os.path.join(d, "configure"))] \
            or [d for d in seen]

    def _stage_modern_autotools(self):
        # Replace the 1998 config.guess/config.sub with modern ones from
        # autotools-dev, then ensure linux-ohos validates (E072/E122/E268).
        # Runs in build() (not generate()) so it hits the real configure
        # dir. Idempotent: re-runs never duplicate entries.
        try:
            misc = os.path.join(
                self.dependencies.build["autotools-dev"].package_folder,
                "share", "misc",
            )
        except Exception as exc:
            self.output.warning(f"stage modern autotools failed: {exc}")
            return
        for target in self._configure_dirs():
            staged = 0
            for fname in ("config.guess", "config.sub"):
                src = os.path.join(misc, fname)
                if os.path.isfile(src):
                    copy(self, fname, src=misc, dst=target)
                    staged += 1
            self.output.info(f"staged modern autotools files: {staged}/2 -> {target}")
            sub = os.path.join(target, "config.sub")
            if os.path.isfile(sub):
                self._patch_config_sub_ohos(sub)
        self._selftest_config_sub()

    def _patch_config_sub_ohos(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            self.output.warning(f"read {path} failed: {exc}")
            return
        orig = text
        # 1) kernel-OS validation must accept linux-ohos (E122/E268).
        # Modern 2025 files already have it; 2024 files miss it.
        if "linux-ohos" not in text:
            if "linux-uclibc*-" in text:
                text = text.replace("linux-uclibc*-", "linux-uclibc*- | linux-ohos*-", 1)
            elif "linux-gnu*" in text:
                text = text.replace("linux-gnu*", "linux-gnu* | linux-ohos*", 1)
        # 2) OS list must accept ohos (E072). Modern files already have it.
        if "| ohos*" not in text and "ohos*" not in text:
            if "android*" in text:
                text = text.replace("android*", "ohos* | android*", 1)
        if text != orig:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            self.output.info("patched config.sub for linux-ohos (E072/E122)")
        else:
            self.output.info("config.sub already ohos-aware, no patch needed")

    def _selftest_config_sub(self):
        # Preflight evidence: prove the staged config.sub passes the exact
        # sanity check configure performs, plus our triplets, before
        # configure runs. Fails loudly here instead of inside configure.
        for target in self._configure_dirs():
            sub = os.path.join(target, "config.sub")
            if not os.path.isfile(sub):
                continue
            for triplet in ("sun4", "aarch64-unknown-linux-gnu",
                            "aarch64-unknown-linux-ohos"):
                self.run(f'/bin/sh "{sub}" {triplet}', env="conanbuild", cwd=target)

    def _restore_helper_modes(self):
        # E490: source extraction on HMDFS can lose exec bits for Autotools
        # helpers. Best-effort restore (no-op where chmod unsupported).
        for target in self._configure_dirs():
            for relative in ("configure", "config.guess", "config.sub",
                             "install-sh", "missing", "mkinstalldirs"):
                path = os.path.join(target, relative)
                if os.path.isfile(path):
                    try:
                        mode = os.stat(path).st_mode
                        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    except OSError:
                        pass

    def _candidate_prefixes(self):
        # Ordered unique prefixes that may hold the system ncurses.
        # DEFAULT_PREFIX stays first (sanctioned pattern); the rest are
        # read-only fallbacks probed for headers/libs, never replacing it.
        seen = []
        for cand in (
            os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local")),
            os.environ.get("HMBS_INSTALL", ""),
            os.path.expanduser("~/usr/local"),
            os.path.expanduser("~/.harmonybrew"),
            "/storage/Users/currentUser/usr/local",
            "/data/service/hnp",
        ):
            if cand and cand not in seen:
                seen.append(cand)
        return [d for d in seen if d and os.path.isdir(d)]

    def _probe_ncurses(self):
        # Read-only probe executed on the build machine. Logs JUKE-NC-* so
        # preflight shows exactly which prefix provides headers/libs.
        # Returns (lib_dirs_with_ncurses, libs_suffix).
        prefixes = self._candidate_prefixes()
        self.output.info(f"JUKE-NC prefixes: {prefixes}")
        lib_dirs = []
        has_tinfo = False
        has_tinfow = False
        for pref in prefixes:
            inc = os.path.join(pref, "include")
            lib = os.path.join(pref, "lib")
            try:
                inc_files = os.listdir(inc) if os.path.isdir(inc) else []
                lib_files = os.listdir(lib) if os.path.isdir(lib) else []
            except OSError:
                inc_files, lib_files = [], []
            nc_h = any(n in ("ncurses.h", "curses.h") for n in inc_files)
            ncw_h = "ncursesw" in inc_files or any("ncurses" in n for n in inc_files)
            nc_lib = [n for n in lib_files if n.startswith("libncurses")]
            ti_lib = [n for n in lib_files if n.startswith("libtinfo")]
            self.output.info(
                f"JUKE-NC {pref} inc_nc={nc_h}/{ncw_h} libs={nc_lib[:6]} tinfo={ti_lib[:6]}")
            if nc_lib and lib not in lib_dirs:
                lib_dirs.append(lib)
            if any(n.startswith("libtinfo.") or n.startswith("libtinfow.")
                   or n == "libtinfo.a" or n == "libtinfo.so" for n in lib_files):
                has_tinfo = True
            if any(n.startswith("libtinfow.") or n == "libtinfow.a"
                   or n == "libtinfow.so" for n in lib_files):
                has_tinfow = True
        suffix = ""
        if has_tinfow:
            suffix = " -ltinfow"
        elif has_tinfo:
            suffix = " -ltinfo"
        self.output.info(f"JUKE-NC result lib_dirs={lib_dirs} suffix={suffix!r}")
        return lib_dirs, suffix

    def _ensure_compat_ncurses(self):
        # Re-create juke-local-libs/libncurses.a -> libncursesw.a (dialog +
        # dhex precedent). generate() already did this, but a clean build
        # folder between generate/build would lose it before configure.
        try:
            nc_lib = os.path.join(
                self.dependencies["ncurses"].package_folder, "lib")
            local_libs = os.path.join(self.build_folder, "juke-local-libs")
            os.makedirs(local_libs, exist_ok=True)
            link_src = os.path.join(nc_lib, "libncursesw.a")
            link_dst = os.path.join(local_libs, "libncurses.a")
            if os.path.isfile(link_src):
                if os.path.islink(link_dst) or os.path.exists(link_dst):
                    os.remove(link_dst)
                try:
                    os.symlink(link_src, link_dst)
                except OSError:
                    shutil.copy2(link_src, link_dst)
                self.output.info(f"juke compat lib ensured: {link_dst}")
            else:
                self.output.warning(
                    f"juke compat source missing: {link_src}")
        except Exception as exc:
            self.output.warning(f"ensure compat ncurses failed: {exc}")

    def _build_dirs_for_makefile_check(self):
        seen = []
        for cand in (self.build_folder,
                     os.path.join(self.build_folder, "build-release") if self.build_folder else "",
                     self.source_folder):
            if cand and os.path.isdir(cand) and cand not in seen:
                seen.append(cand)
        return seen

    def _assert_makefile_or_dump(self, libs_value):
        for d in self._build_dirs_for_makefile_check():
            if os.path.isfile(os.path.join(d, "Makefile")):
                self.output.info(f"JUKE-NC makefile OK: {os.path.join(d, 'Makefile')}")
                return
        self.output.warning(
            "JUKE-NC: configure returned 0 but no Makefile was generated "
            f"(checked {self._build_dirs_for_makefile_check()}, LIBS={libs_value!r}). "
            "Upstream configure.in uses AC_CHECK_LIB(ncurses,main,,[exit]): "
            "a bare `exit` after `checking for main in -lncurses... no` exits 0 "
            "without generating Makefiles, so `make` then reports "
            "`No targets specified and no makefile found'. Dumping config.log.")
        self._dump_config_log()
        raise ConanException(
            "juke configure produced no Makefile (ncurses check likely failed: "
            f"LIBS={libs_value!r}); see JUKE-NC/JUKE-FORENSIC lines above")

    def build(self):
        apply_conandata_patches(self)
        # File staging must happen here (not generate()): last round staged
        # only source_folder at generate time while the failure path shows
        # configure executing from a different dir, so the 1998 config.sub
        # was never replaced. Shell comes from buildenv in generate().
        self._stage_modern_autotools()
        self._restore_helper_modes()
        # juke's configure ends with a bare `exit` (status 0) when -lncurses
        # fails to link, leaving no Makefile behind. Feed the Conan ncurses
        # compat lib (libncurses.a -> libncursesw.a, created in generate())
        # through LIBS (AC_CHECK_LIB tests `-lncurses $LIBS`). Re-ensure it
        # here in case the build folder was cleaned between generate/build.
        self._ensure_compat_ncurses()
        libs_value = "-lncurses"
        autotools = Autotools(self)
        # Force cross-compile mode to skip conftest execution on OHOS
        # OHOS security prevents running unsigned conftest binaries
        try:
            if self.settings.os == "OHOS":
                autotools.configure(args=["--build=aarch64-unknown-linux-gnu",
                                           "--host=aarch64-unknown-linux-ohos",
                                           f"LIBS={libs_value}"])
            else:
                autotools.configure(args=[f"LIBS={libs_value}"])
            self._assert_makefile_or_dump(libs_value)
        except Exception:
            self._dump_config_log()
            raise
        autotools.make(args=["-j1"])

    def _dump_config_log(self):
        # Preflight only forwards a truncated summary, which hides the real
        # linker error behind "C compiler cannot create executables".
        # Surface config.log (link command + error lines + tail) so the next
        # round can fix precisely instead of guessing flags. Never masks the
        # failure: never raises, caller re-raises.
        try:
            candidates = []
            for d in list(self._configure_dirs()) + [self.build_folder]:
                if d and os.path.isdir(d):
                    for root, _dirs, files in os.walk(d):
                        if "config.log" in files:
                            candidates.append(os.path.join(root, "config.log"))
                            break
                if candidates:
                    break
            if not candidates:
                self.output.warning("JUKE-FORENSIC: config.log not found "
                                    f"(searched {self._configure_dirs()} + build_folder)")
                return
            path = candidates[0]
            with open(path, encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
            self.output.warning(f"JUKE-FORENSIC: {path} ({len(lines)} lines)")
            shown = 0
            for line in lines:
                low = line.lower()
                if ("clang" in low and "conftest" in low) or "ac_link" in low:
                    self.output.warning("JUKE-FORENSIC-CC: " + line[:400])
                    shown += 1
                    if shown >= 10:
                        break
            shown = 0
            for line in lines:
                low = line.lower()
                if ("error" in low or "cannot find" in low or "undefined" in low
                        or "ld.lld" in low or "not found" in low):
                    self.output.warning("JUKE-FORENSIC-ERR: " + line[:400])
                    shown += 1
                    if shown >= 30:
                        break
            self.output.warning("JUKE-FORENSIC-TAIL-BEGIN")
            for line in lines[-60:]:
                self.output.warning("JUKE-FORENSIC-TAIL: " + line[:400])
            self.output.warning("JUKE-FORENSIC-TAIL-END")
        except Exception as exc:
            self.output.warning(f"JUKE-FORENSIC: dump failed: {exc}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # juke is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

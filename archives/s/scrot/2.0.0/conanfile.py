#!/usr/bin/env python3
"""Conan recipe --- scrot 2.0.0 (Autotools: configure + make).

SCReenshOT: command line screen capture utility for X11, using imlib2
to grab and save images. Upstream 2.0.0 needs imlib2 >= 1.11.0 with X;
this recipe carries an in-source compat port (patches/0001+0002) so it
builds against the repo's X-less imlib2 1.9.1: deps.pc floor relaxed to
>= 1.9.1 plus XGetImage-based capture shims and a temp-file splice for
imlib_save_image_fd(). The shims self-disable against imlib2 >= 1.11
with X (see src/scrot_imlib_compat.h).

R32: settings.os checks in ("Linux", "OHOS").
R38: scrot is a command-line tool (commands.json at software level).
Upstream ships no test suite (no tests/ dir, no TESTS in Makefile.am,
no `make check` target), so build() does not invoke upstream tests;
see test_package/MANIFEST.yml for the no-tests audit.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class ScrotConan(ConanFile):
    name = "scrot"
    version = "2.0.0"
    package_type = "application"
    description = "Command line screen capture utility for X11"
    license = "MIT-feh"
    homepage = "https://github.com/resurrecting-open-source-projects/scrot"
    url = "https://github.com/resurrecting-open-source-projects/scrot"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "libx11/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxcomposite/0.4.6",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxfixes/6.1.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxrandr/1.5.5.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        # Upstream deps.pc floor is relaxed to imlib2 >= 1.9.1 by
        # patches/0001 (the in-source compat port in patches/0002 provides
        # the post-1.9.1 X-capture and save-fd APIs), so the 1.9.1 pin below
        # genuinely satisfies configure's PKG_CHECK_MODULES. Only imlib2
        # version with a complete recipe in-repo; a range floor was verified
        # (cycle 16) to die in graph resolution.
        self.requires(
            "imlib2/1.9.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        # libpng/1.6.58 avoids the stale-compiler -dumpmachine crash
        # present in 1.6.58.1/1.6.58.2/1.6.58.3 (same upstream v1.6.58).
        self.requires("libpng/1.6.58", override=True)
        # libxrender/0.9.12.1 targets the 6.4.0 X stack (same tarball as
        # 0.9.12, newer packaging revision).
        self.requires("libxrender/0.9.12.1", override=True)

    def build_requirements(self):
        # scrot configure.ac uses PKG_CHECK_MODULES (needs a pkg-config
        # binary); HMBS true device injects only cmake/make/ninja/python3,
        # so no system pkg-config exists. In-repo pkgconf installs only
        # bin/pkgconf (no pkg-config alias), hence the recipe must also
        # export PKG_CONFIG=<absolute pkgconf path> in generate().
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "scrot is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )
        # NOTE (cycle 28, fourth strategy cycle): the version/X gap is now
        # bridged inside this recipe by an in-source compat port
        # (patches/0001 relaxes the deps.pc floor to >= 1.9.1; 0002 adds
        # src/scrot_imlib_compat.h with XGetImage-based capture shims and a
        # temp-file splice for imlib_save_image_fd, self-disabling against
        # imlib2 >= 1.11 with X). imlib2 1.9.1 is therefore a supported
        # dependency, not a warning condition: only below-1.9.1 warns, and
        # the real gates stay configure's PKG_CHECK_MODULES + compiler.
        try:
            imlib_dep = self.dependencies.get("imlib2")
        except Exception:
            imlib_dep = None
        if imlib_dep is not None:
            try:
                imlib_ver = str(imlib_dep.ref.version)
            except Exception:
                imlib_ver = ""
            if imlib_ver:
                self.output.info(
                    "scrot/2.0.0 resolved imlib2 %s; in-source imlib compat "
                    "port active (patches/0001+0002)" % imlib_ver
                )
            try:
                _v = Version(imlib_ver) if imlib_ver else None
            except Exception:
                _v = None
            if _v is not None and _v < Version("1.9.1"):
                self.output.warning(
                    "scrot/2.0.0 compat port supports imlib2 >= 1.9.1 but "
                    "resolved imlib2 %s; continuing so configure's own "
                    "PKG_CHECK_MODULES is the real gate"
                    % (imlib_ver or "unknown")
                )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _resolve_tool(configured, names):
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        try:
            home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        except Exception:
            home_bin = ""
        if home_bin:
            for name in names:
                cand = os.path.join(home_bin, name)
                if os.path.exists(cand):
                    return cand
        return configured or names[0]

    @staticmethod
    def _resolve_shell():
        env_sh = (os.environ.get("SHELL", "") or "").split()[0] if os.environ.get("SHELL", "") else ""
        if env_sh and os.path.isfile(env_sh):
            return env_sh
        legacy = "/data/service/hnp/bin/bash"
        if os.path.exists(legacy):
            return legacy
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        found = shutil.which("sh")
        if found:
            return found
        return "/bin/sh"

    def _configured_compilers(self):
        cc = ""
        cxx = ""
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            exes = None
        if isinstance(exes, dict):
            cc = exes.get("c", "") or ""
            cxx = exes.get("cpp", "") or ""
        if not cc:
            try:
                cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str) or "clang"
            except Exception:
                cc = "clang"
        if not cxx:
            try:
                cxx = self.conf.get("tools.build:compiler_executables:cpp", "clang++", check_type=str) or "clang++"
            except Exception:
                cxx = "clang++"
        return cc, cxx

    def _resolve_pkgconf(self):
        try:
            pkg_folder = self.dependencies.build["pkgconf"].package_folder
            cand = os.path.join(pkg_folder, "bin", "pkgconf")
            if os.path.isfile(cand):
                return cand
        except Exception:
            pass
        for name in ("pkgconf", "pkg-config"):
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                return found
        return ""

    def _mktemp_fallback_requested(self):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory created
        # by mktemp on the true-machine filesystem cannot be written by
        # later config.status steps. When HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK!=0, shadow mktemp so calls for
        # "./conf*" fail and Autoconf falls back to its `mkdir` path.
        # All other mktemp calls delegate to the real binary (cyrus-sasl
        # precedent); TMPDIR itself stays writable. Configure-phase only
        # in effect (conf* filter), no tests skipped. Opt-out gate (!=0)
        # replaces the previous strict =="1" gate which never fired
        # in preflight (no shim-active line in generate log).
        return os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "0"

    def _setup_mktemp_shim(self, tmpdir):
        # Create a conf*-scoped mktemp shim under the writable tmp root;
        # return its bin dir (or "" when not requested / install fails).
        # Kept under TMPDIR (regular FS) so chmod +x is effective even
        # when HMBS_CAP_CHMOD=0 on the HMDFS workspace.
        if not self._mktemp_fallback_requested():
            return ""
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except Exception:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as _h:
                _h.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        self.output.info(
            "[ok] HMBS mktemp fallback shim active for configure: %s"
            % shim_dir
        )
        return shim_dir

    def _fix_autoconf_umask_for_ohos(self, source_folder):
        # SKILL fuse-tmp-write-guard strategy 2: config.status carries
        # its own hardcoded `umask 077` copy, so outer umask injection
        # is ineffective (oddjob precedent). Relax it to 022 in the
        # generated configure script so the mkdir-fallback temp dir
        # stays writable on HMDFS. Best-effort, info-logged.
        try:
            conf = os.path.join(source_folder or "", "configure")
            if not conf or not os.path.isfile(conf):
                return
            with open(conf, "r", encoding="utf-8",
                      errors="surrogateescape") as _f:
                _txt = _f.read()
            if "umask 077" not in _txt:
                self.output.info(
                    "HMBS diag scrot configure umask 077 not present")
                return
            _n = _txt.count("umask 077")
            _txt = _txt.replace("umask 077", "umask 022")
            with open(conf, "w", encoding="utf-8",
                      errors="surrogateescape") as _f:
                _f.write(_txt)
            self.output.info(
                "HMBS diag scrot relaxed umask 077->022 in configure (%d)"
                % _n)
        except Exception as _e:
            self.output.warning(
                "scrot configure umask relax failed: %s" % _e)

    def _resolve_hmbs_tmp(self):
        # Prefer the HMBS-injected writable root; validate with a probe
        # write; fall back to build_folder/.tmp. Never return bare /tmp
        # (read-only on the true machine) or flag values "0"/"1".
        def _is_path_cand(v):
            if not v or v in ("0", "1", "/tmp"):
                return False
            return os.path.isabs(v)
        cands = [
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ]
        for cand in cands:
            if not _is_path_cand(cand):
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w", encoding="utf-8") as _pf:
                    _pf.write("probe")
                os.remove(probe)
                return cand
            except Exception:
                continue
        fallback = os.path.join(self.build_folder, ".tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _log_imlib2_pc_evidence(self):
        # Generate-phase real pc-file evidence: Version + Cflags/Libs +
        # X_DISPLAY_MISSING flag from the deterministic PkgConfigDeps
        # output, plus the upstream deps.pc Requires floor. Pure info,
        # never raises, gates unchanged.
        try:
            pc = os.path.join(self.generators_folder, "imlib2.pc")
            if os.path.isfile(pc):
                with open(pc, encoding="utf-8", errors="ignore") as _f:
                    _txt = _f.read()
                _ver = ""
                _cflags = ""
                _libs = ""
                for _line in _txt.splitlines():
                    _s = _line.strip()
                    if _s.lower().startswith("version:"):
                        _ver = _line.split(":", 1)[1].strip()
                    elif _s.lower().startswith("cflags:"):
                        _cflags = _line.split(":", 1)[1].strip()
                    elif _s.lower().startswith("libs:"):
                        _libs = _line.split(":", 1)[1].strip()
                _xless = "yes" if "X_DISPLAY_MISSING" in _txt else "no"
                self.output.info(
                    "HMBS diag scrot imlib2.pc Version=%s X_DISPLAY_MISSING=%s "
                    "Cflags=[%s] Libs=[%s] path=%s"
                    % (_ver or "unknown", _xless, _cflags, _libs, pc)
                )
            else:
                self.output.info(
                    "HMBS diag scrot imlib2.pc missing in %s"
                    % self.generators_folder
                )
            _deps = os.path.join(self.source_folder or "", "deps.pc")
            if _deps and os.path.isfile(_deps):
                with open(_deps, encoding="utf-8", errors="ignore") as _f:
                    _dtxt = _f.read()
                _req = ""
                for _line in _dtxt.splitlines():
                    if _line.strip().lower().startswith("requires"):
                        _req = _line.strip()
                        break
                self.output.info(
                    "HMBS diag scrot upstream deps.pc %s" % (_req or "Requires line not found")
                )
            else:
                self.output.info(
                    "HMBS diag scrot upstream deps.pc not found in %s"
                    % (self.source_folder or "?")
                )
        except Exception as _e:
            self.output.info(
                "HMBS diag scrot imlib2.pc read failed: %s" % _e
            )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._log_imlib2_pc_evidence()
        self.output.info(
            "HMBS diag scrot mktemp-fb env=%r TMPDIR=%r TMP=%r TEMP=%r"
            % (os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"),
               os.environ.get("TMPDIR"), os.environ.get("TMP"),
               os.environ.get("TEMP")))
        _hmbs_tmp = self._resolve_hmbs_tmp()
        self.output.info("HMBS diag scrot hmbs_tmp=%s" % _hmbs_tmp)
        _mktemp_shim = self._setup_mktemp_shim(_hmbs_tmp)
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        pkgconf = self._resolve_pkgconf()
        if pkgconf:
            self.output.info("HMBS diag scrot PKG_CONFIG=%s" % pkgconf)
        else:
            self.output.warning(
                "scrot/2.0.0 pkgconf binary unresolved; configure "
                "pkg-config probe is expected to fail"
            )
        if str(self.settings.os) == "OHOS":
            ohos_sh = self._resolve_shell()
            cc_cfg, cxx_cfg = self._configured_compilers()
            cc = self._resolve_tool(cc_cfg, ("clang", "cc"))
            cxx = self._resolve_tool(cxx_cfg, ("clang++", "c++"))
            self.output.info("HMBS diag scrot shell=%s cc_cfg=%s cc=%s cxx_cfg=%s cxx=%s" % (ohos_sh, cc_cfg, cc, cxx_cfg, cxx))
            env = tc.environment()
            env.define_path("SHELL", ohos_sh)
            env.define_path("CONFIG_SHELL", ohos_sh)
            env.define_path("CC", cc)
            env.define_path("CXX", cxx)
            if pkgconf:
                env.define_path("PKG_CONFIG", pkgconf)
                pkg_bindir = os.path.dirname(pkgconf)
                if pkg_bindir:
                    env.prepend_path("PATH", pkg_bindir)
            env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
            if _mktemp_shim:
                env.prepend_path("PATH", _mktemp_shim)
            tc.generate(env=env)
        else:
            if pkgconf:
                env = tc.environment()
                env.define_path("PKG_CONFIG", pkgconf)
                pkg_bindir = os.path.dirname(pkgconf)
                if pkg_bindir:
                    env.prepend_path("PATH", pkg_bindir)
                env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
                if _mktemp_shim:
                    env.prepend_path("PATH", _mktemp_shim)
                tc.generate(env=env)
            else:
                if _mktemp_shim:
                    env = tc.environment()
                    env.prepend_path("PATH", _mktemp_shim)
                    tc.generate(env=env)
                else:
                    tc.generate()

    def build(self):
        # Single scrot configure+make over the compat-patched source tree
        # (patches applied in source()). No vendored second configure+make:
        # cycles 21-24 proved a double autotools load OOMs the constrained
        # true device. Real gates stay configure's PKG_CHECK_MODULES
        # (floor now >= 1.9.1, satisfied by the pinned imlib2) + compiler.
        # HMDFS trap: config.status self-sets `umask 077` then mktemp -d
        # ./confXXXXXX; the dir becomes owner-unwritable so subs1.awk
        # fails. Fix both layers here (skill strategy 2 + mkdir fallback):
        # relax the embedded umask and ensure the conf* mktemp shim is on
        # PATH even if the generate-phase env was aggregated away.
        try:
            _btmp = self._resolve_hmbs_tmp()
            self._fix_autoconf_umask_for_ohos(self.source_folder)
            _bshim = self._setup_mktemp_shim(_btmp)
            if _bshim and _bshim not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _bshim + os.pathsep + os.environ.get("PATH", "")
                self.output.info(
                    "HMBS diag scrot build-phase mktemp shim on PATH: %s"
                    % _bshim)
            try:
                os.umask(0o022)
            except Exception:
                pass
        except Exception as _e:
            self.output.warning("scrot build-phase fs guard failed: %s" % _e)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _write_install_shim(self):
        # E182/E188: true-machine HMFS/HMBS runtime install
        # (runtime/<task>/bin/install) only accepts single-file two-arg
        # calls; multi-source batch installs (automake
        # install-dist_docDATA: `install -c -m 644 A B C ... dir/`) exit
        # 64 (EX_USAGE). Seen as lzop dist_docDATA / xeyes headers /
        # adms+aribb24+cxxtools precedents. scrot top-level Makefile has
        # dist_doc_DATA (7 files) so `make install` always hits this.
        # Write a cp/mkdir shim (single + multi source, mkdir -p,
        # chmod || true for HMBS_CAP_CHMOD=0) and redirect generated
        # Makefiles' INSTALL to it. No files skipped, no docs dropped.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except Exception:
            pass
        install = os.path.join(shim_dir, "install")
        # HMFS grants exec from open mode (chmod cap may be 0): use
        # os.open 0o755 so the shim is directly executable.
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  d=${dest%/*}; [ -n \"$d\" ] || d=.; mkdir -p \"$d\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else chmod \"$mode\" \"$dest\" 2>/dev/null || true; fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable; INSTALL_DATA/INSTALL_PROGRAM derive
        # from ${INSTALL}, so replacing INSTALL covers the failing
        # install-dist_docDATA in one pass (aribb24/cxxtools precedent).
        for _root, _, _files in os.walk(self.build_folder):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append("%sINSTALL = %s\n" % (_indent, shim_install))
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8", newline="\n") as _f:
                    _f.write("".join(_lines))
        self.output.info(
            "[ok] OHOS port: redirected INSTALL to shim %s" % shim_install)

    def package(self):
        # HMBS install-shim gate (see _write_install_shim): redirect before
        # make install so the 7-file install-dist_docDATA goes through the
        # mkdir -p + chmod-tolerant cp shim instead of the single-file-only
        # runtime install (Error 64). Best-effort: failure only warns and
        # falls back to system install, never skips files.
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim)
        except Exception as _e:
            self.output.warning("install shim setup failed, using system install: %s" % _e)
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

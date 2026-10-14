#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for svox 1.0 -- SVOX Pico small-footprint TTS engine.

SVOX Pico is the offline small footprint speech synthesis engine from
Android AOSP (German/English/Spanish/French/Italian), producing libttspico
(C API: picoapi.h/picodefs.h) and the pico2wave command line tool. This
recipe builds the Debian official source snapshot
(svox_1.0+git20130326.orig.tar.gz, the same tarball used by OpenWrt
sound/svox) as a static library on HarmonyOS PC (aarch64, native build).

Build notes (updated 2026-10-13 after real-device evidence):
- source() is pure-Python (download + check_sha256 + stdlib tarfile with
  manual strip_root): it never execs the host tar binary. True-device
  2026-10-13 reported `sh: .../.harmonybrew/bin/tar: Operation not
  permitted` (EPERM/126, same signature as stale-codesign DRAFT-14257 /
  vgmplay cases) during the compile phase; the recipe itself never calls
  tar, so the only tar dependency was Conan's automatic unpacking. The
  vendored-popt and orig-tarball URLs/sha256 are unchanged; only the
  extraction mechanism changed. build() logs a non-fatal HOST_TAR_PROBE
  (candidate existence + --version rc) for next-round triage.
- The pico/ subdirectory of the Debian orig tarball contains no autotools
  files at all (no configure.ac/configure/Makefile.am; the real-device
  source tree shows only Android.mk/compat/lang/lib/res/src/tests/tts).
  The autotools files are added on the fly by Debian packaging
  (debian.tar.xz patches), so the orig tarball cannot be autoreconfed.
  OpenWrt PKG_FIXUP:=autoreconf works only because it applies the Debian
  patches first. This recipe therefore does not use
  AutotoolsToolchain/configure/make; instead it compiles directly with CC
  following upstream pico/lib/Android.mk (30 lib/*.c files plus
  bin/pico2wave.c) via CC + ar + CC link. Artifacts match Debian shape:
  include/pico*.h + lib/libttspico.a(.so) + bin/pico2wave +
  share/pico/lang/* (lingware voice data, architecture independent).
- pico2wave parses its command line with popt, which is vendored as source
  and built statically (conandata popt entry, following the merged
  logrotate 3.22.0 precedent). No external Conan dependency. Vendored popt
  is built WITHOUT configure/make: the 5 lib sources listed in
  Makefile.am (libpopt_la_SOURCES) are compiled directly with CC and
  archived with ar, so config.sub/config.guess are never invoked and no
  SHELL/CONFIG_SHELL interpreter is needed (immune to the broken
  interpreter exported by the profile).
- Upstream ships no automated tests (see test_package/MANIFEST.yml audit):
  build() performs no `make check`; it only greps the real source tree for
  audit evidence kept in the conan create log; the no_tests marker is
  emitted at the test_package stage per upstream_test_in_build: false
  (aribb24/cvechecker precedent).

Artifacts: include/picoapi.h and other headers + lib/libttspico.a +
bin/pico2wave + share/pico/lang/* (lingware voice data, arch independent).
"""
import glob
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, check_sha256, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class SvoxConan(ConanFile):
    name = "svox"
    version = "1.0"
    description = (
        "SVOX Pico small-footprint text-to-speech engine "
        "(libttspico C API and pico2wave utility)"
    )
    license = "Apache-2.0"
    homepage = "https://android.googlesource.com/platform/external/svox/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tts", "text-to-speech", "speech-synthesis", "svox", "pico")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "pico2wave.c", src=os.path.join(self.recipe_folder, "files"),
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("svox is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def build_requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def _download_first_ok(self, entry, filename):
        """Download tarball trying each mirror URL in order (pure-Python).

        Uses conan download (urllib, no external tar/curl exec) so a broken
        host tar binary can never break the download step. sha256 is verified
        after download; conandata sha256 is unchanged.
        """
        urls = entry.get("url", [])
        if isinstance(urls, str):
            urls = [urls]
        sha256 = entry.get("sha256", "")
        last_err = None
        for _url in urls:
            try:
                self.output.info("SVOX download trying: %s" % _url)
                download(self, _url, filename)
                _base = getattr(self, "base_source_folder", None) or self.source_folder
                _local = os.path.join(_base,
                                      filename)
                if not os.path.isfile(_local):
                    # download() saved relative to base source folder layout;
                    # fall back to searching a few well-known spots.
                    for _cand in (os.path.join(self.source_folder, filename),
                                  os.path.join(os.getcwd(), filename),
                                  filename):
                        if os.path.isfile(_cand):
                            _local = _cand
                            break
                if sha256:
                    check_sha256(self, _local, sha256)
                self.output.info("SVOX download ok: %s (%d bytes)" % (_url, os.path.getsize(_local)))
                return _local
            except Exception as _e:
                self.output.warning("SVOX download failed %s: %s" % (_url, _e))
                last_err = _e
                continue
        raise ConanException("svox download failed for all mirrors %s: %s" % (urls, last_err))

    @staticmethod
    def _extract_tar_gz_noexec(tar_path, dest_dir, strip_root=True):
        """Extract .tar.gz with stdlib tarfile only (never exec /bin/tar).

        HarmonyOS runners may carry a harmonybrew GNU tar whose ELF signature
        is rejected (sh: .../bin/tar: Operation not permitted, EPERM/126).
        tarfile avoids that host binary entirely. strip_root mirrors conan
        get(strip_root=True) semantics for a single top-level directory.
        """
        os.makedirs(dest_dir, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as _tf:
            _members = _tf.getmembers()
            _root = ""
            if strip_root and _members:
                _tops = sorted(set(_m.name.split("/")[0] for _m in _members if _m.name))
                if len(_tops) == 1 and any("/" in _m.name for _m in _members):
                    _root = _tops[0] + "/"
            for _m in _members:
                _name = _m.name
                if _root:
                    if _name == _root.rstrip("/"):
                        continue
                    if not _name.startswith(_root):
                        # Archive without a single root: keep as-is.
                        pass
                    else:
                        _name = _name[len(_root):]
                        if not _name:
                            continue
                        _m.name = _name
                _tf.extract(_m, path=dest_dir)

    def source(self):
        # Pure-Python fetch+extract: never exec host tar (harmonybrew tar may
        # be EPERM on some runners). conandata URLs/sha256 unchanged.
        _main_tgz = self._download_first_ok(self.conan_data["sources"], "svox-orig.tar.gz")
        self._extract_tar_gz_noexec(_main_tgz, self.source_folder, strip_root=True)
        try:
            os.remove(_main_tgz)
        except OSError:
            pass
        _popt_dest = os.path.join(self.source_folder, "popt")
        # get() with destination= would create the dir first; mirror that.
        try:
            os.makedirs(_popt_dest, exist_ok=True)
        except OSError:
            pass
        _popt_tgz = self._download_first_ok(self.conan_data["popt"], "popt-1.16.tar.gz")
        # popt tarball was downloaded into base source folder; extract into popt/.
        # If _popt_tgz already lives under _popt_dest, extract in place.
        self._extract_tar_gz_noexec(_popt_tgz, _popt_dest, strip_root=True)
        try:
            os.remove(_popt_tgz)
        except OSError:
            pass
        # Remove any stray downloaded copies left in source tree by download().
        for _stray in ("svox-orig.tar.gz", "popt-1.16.tar.gz"):
            for _base in dict.fromkeys([self.source_folder, _popt_dest]):
                _p = os.path.join(_base, _stray)
                if os.path.isfile(_p):
                    try:
                        os.remove(_p)
                    except OSError:
                        pass

    @property
    def _popt_prefix(self):
        return os.path.join(self.build_folder, "poptinst")

    def generate(self):
        pass

    def _get_cc(self):
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        cc = compilers.get("c")
        if cc and os.path.isfile(cc):
            return cc
        for _cand in ("/data/service/hnp/bin/clang", "/usr/bin/cc",
                      "/usr/bin/gcc", "cc"):
            if os.path.isabs(_cand):
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    self.output.info("CC fallback: %s" % _cand)
                    return _cand
            else:
                _w = shutil.which(_cand)
                if _w:
                    self.output.info("CC fallback via PATH: %s" % _w)
                    return _w
        if cc:
            self.output.warning("CC %r not an absolute executable; using as-is" % cc)
            return cc
        return "cc"

    def _find_ar(self, cc):
        # Prefer the toolchain sibling first (hnp clang dir), then system
        # paths. Deprioritise harmonybrew binaries: that tree has shown stale
        # ELF signatures on some runners (tar EPERM this round), so only use
        # it when no system alternative exists.
        _cands = []
        _bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        for _name in ("llvm-ar", "ar"):
            if _bindir:
                _p = os.path.join(_bindir, _name)
                if os.path.isfile(_p):
                    _cands.append(_p)
            for _sys in ("/usr/bin/%s" % _name, "/bin/%s" % _name):
                if os.path.isfile(_sys):
                    _cands.append(_sys)
            _w = shutil.which(_name)
            if _w and _w not in _cands:
                _cands.append(_w)
        _cands.append("ar")
        _brew = [c for c in _cands if "harmonybrew" in c or ".harmonybrew" in c]
        _plain = [c for c in _cands if c not in _brew]
        for _p in _plain + _brew:
            if os.path.isabs(_p):
                if os.path.isfile(_p) and os.access(_p, os.X_OK):
                    return _p
            elif _p:
                return _p
        return "ar"

    def _probe_host_tar(self):
        """Non-fatal evidence probe for the broken host tar (next-round triage).

        Never fails the build; only logs which tar binaries exist and whether
        they exec. Recipe extraction/build never calls tar (pure-Python +
        CC/ar only), so a broken harmonybrew tar must not break the build.
        """
        try:
            import subprocess
            _cands = []
            _w = shutil.which("tar")
            if _w:
                _cands.append(_w)
            for _p in ("/bin/tar", "/usr/bin/tar",
                       "/storage/Users/currentUser/.harmonybrew/bin/tar"):
                if _p not in _cands:
                    _cands.append(_p)
            for _p in _cands:
                _exists = os.path.isfile(_p)
                _exec_bit = os.access(_p, os.X_OK) if _exists else False
                _run = "skipped"
                if _exists:
                    try:
                        _r = subprocess.run([_p, "--version"], capture_output=True,
                                            timeout=10, text=True, errors="ignore")
                        _out = ((_r.stdout or "") + (_r.stderr or "")).strip().splitlines()
                        _run = "rc=%d %s" % (_r.returncode, (_out[0][:120] if _out else ""))
                    except Exception as _e:
                        _run = "exec-failed: %s" % str(_e)[:160]
                self.output.info("HOST_TAR_PROBE path=%s exists=%s x_ok=%s run=%s"
                                 % (_p, _exists, _exec_bit, _run))
            self.output.info("HOST_TAR_PROBE recipe uses pure-Python tarfile only; host tar status is informational")
        except Exception as _e:
            self.output.warning("HOST_TAR_PROBE failed: %s" % _e)

    def _find_pico_dir(self):
        cand = os.path.join(self.source_folder, "pico")
        if os.path.isdir(os.path.join(cand, "lib")) and \
                os.path.isfile(os.path.join(cand, "lib", "picoapi.c")):
            self.output.info("pico root: <source>/pico (lib/picoapi.c found)")
            return cand
        if os.path.isdir(os.path.join(self.source_folder, "lib")) and \
                os.path.isfile(os.path.join(self.source_folder, "lib", "picoapi.c")):
            self.output.info("pico root: <source> (lib/picoapi.c found)")
            return self.source_folder
        popt_dir = os.path.join(self.source_folder, "popt")
        for _root, _dirs, _files in os.walk(self.source_folder):
            if _root == popt_dir or _root.startswith(popt_dir + os.sep):
                _dirs[:] = []
                continue
            _dirs[:] = [_d for _d in _dirs
                        if _d not in ("popt", ".git")]
            if os.path.isfile(os.path.join(_root, "lib", "picoapi.c")):
                self.output.info("pico root discovered: %s"
                                 % os.path.relpath(_root, self.source_folder))
                return _root
        tree = []
        try:
            for _name in sorted(os.listdir(self.source_folder)):
                _p = os.path.join(self.source_folder, _name)
                if os.path.isdir(_p):
                    try:
                        tree.append(_name + "/: " + ",".join(sorted(os.listdir(_p))[:30]))
                    except OSError:
                        tree.append(_name + "/: <unreadable>")
                else:
                    tree.append(_name)
        except OSError as _e:
            tree.append("<listdir failed: %s>" % _e)
        raise ConanException(
            "svox pico root not found (no lib/picoapi.c under <source> "
            "or <source>/pico); source tree:\n" + "\n".join(tree)
        )

    def _pico_layout(self, pico_dir):
        lib_dir = os.path.join(pico_dir, "lib")
        sources = sorted(glob.glob(os.path.join(lib_dir, "*.c")))
        wave_c = ""
        for _cands in (os.path.join(pico_dir, "bin", "pico2wave.c"),
                       os.path.join(pico_dir, "src", "pico2wave.c")):
            if os.path.isfile(_cands):
                wave_c = _cands
                break
        if not wave_c:
            for _root, _dirs, _files in os.walk(pico_dir):
                _dirs[:] = [_d for _d in _dirs if _d not in ("lang", "data", ".git")]
                if "pico2wave.c" in _files:
                    wave_c = os.path.join(_root, "pico2wave.c")
                    break
        if not wave_c:
            _vendored = os.path.join(self.export_sources_folder or "", "pico2wave.c")
            if _vendored and os.path.isfile(_vendored):
                self.output.info("pico2wave.c not in upstream; using vendored files/pico2wave.c")
                wave_c = _vendored
            else:
                _recipe_fallback = os.path.join(self.recipe_folder, "files", "pico2wave.c")
                if os.path.isfile(_recipe_fallback):
                    self.output.info("pico2wave.c not in upstream; using recipe files/pico2wave.c")
                    wave_c = _recipe_fallback
        lang_dir = os.path.join(pico_dir, "lang")
        lang_files = sorted(glob.glob(os.path.join(lang_dir, "*.bin")))
        if not lang_files:
            lang_files = sorted(glob.glob(os.path.join(pico_dir, "**", "*_sg.bin"), recursive=True))
            lang_files += sorted(glob.glob(os.path.join(pico_dir, "**", "*_ta.bin"), recursive=True))
        headers = sorted(glob.glob(os.path.join(lib_dir, "pico*.h")))
        return lib_dir, wave_c, lang_files, headers

    def build(self):
        apply_conandata_patches(self)
        self._probe_host_tar()
        pico_dir = self._find_pico_dir()
        lib_dir, wave_c, lang_files, headers = self._pico_layout(pico_dir)
        self.output.info("SVOX pico_dir=%s lib_sources=%d headers=%d lang_bins=%d wave=%s"
                         % (os.path.relpath(pico_dir, self.source_folder),
                            len(glob.glob(os.path.join(lib_dir, "*.c"))),
                            len(headers), len(lang_files),
                            os.path.relpath(wave_c, self.source_folder) if wave_c else "<missing>"))
        if not headers:
            raise ConanException("svox lib headers not found under %s" % lib_dir)
        if not wave_c:
            raise ConanException("svox pico2wave.c not found under %s" % pico_dir)
        if not lang_files:
            raise ConanException("svox lingware lang/*.bin not found under %s" % pico_dir)
        cc = self._get_cc()
        ar = self._find_ar(cc)
        self.output.info("SVOX toolchain: CC=%s AR=%s" % (cc, ar))
        self._build_popt(cc)
        popt_inc = os.path.join(self._popt_prefix, "include")
        popt_lib = os.path.join(self._popt_prefix, "lib")
        obj_dir = os.path.join(self.build_folder, "pico_objs")
        os.makedirs(obj_dir, exist_ok=True)
        opt = "-O2"
        try:
            if str(self.settings.build_type) == "Debug":
                opt = "-O0 -g"
        except Exception:
            pass
        fpic = ""
        try:
            if self.options.get_safe("fPIC", True):
                fpic = " -fPIC"
        except Exception:
            fpic = " -fPIC"
        lib_sources = sorted(glob.glob(os.path.join(lib_dir, "*.c")))
        if not lib_sources:
            raise ConanException("no C sources in %s" % lib_dir)
        objs = []
        for _src in lib_sources:
            _obj = os.path.join(obj_dir, os.path.splitext(os.path.basename(_src))[0] + ".o")
            _cmd = '"%s" -c %s%s -I"%s" "%s" -o "%s"' % (cc, opt, fpic, lib_dir, _src, _obj)
            self.output.info("compile: %s" % os.path.basename(_src))
            self.run(_cmd)
            objs.append('"%s"' % _obj)
        out_lib = os.path.join(self.build_folder, "out_lib")
        out_bin = os.path.join(self.build_folder, "out_bin")
        os.makedirs(out_lib, exist_ok=True)
        os.makedirs(out_bin, exist_ok=True)
        static_lib = os.path.join(out_lib, "libttspico.a")
        self.run('"%s" rcs "%s" %s' % (ar, static_lib, " ".join(objs)))
        if self.options.shared:
            shared_lib = os.path.join(out_lib, "libttspico.so")
            self.run('"%s" -shared %s -o "%s" -lm' % (cc, " ".join(objs), shared_lib))
        lang_dest = os.path.join(self.package_folder, "share", "pico", "lang")
        self.run('"%s" %s -I"%s" -I"%s" -Dpicolangdir=\\"%s\\" "%s" "%s" -L"%s" -lpopt -lm -o "%s"'
                 % (cc, opt, lib_dir, popt_inc, lang_dest, wave_c, static_lib,
                    popt_lib, os.path.join(out_bin, "pico2wave")))
        self._audit_upstream_tests(pico_dir)

    def _build_popt(self, cc):
        popt_src = os.path.join(self.source_folder, "popt")
        _need = ["popt.c", "poptparse.c", "poptconfig.c", "popthelp.c",
                 "poptint.c", "popt.h", "poptint.h", "system.h"]
        _missing = [n for n in _need
                    if not os.path.isfile(os.path.join(popt_src, n))]
        if _missing:
            raise ConanException(
                "vendored popt source layout changed (missing %s); "
                "see notes.md" % ",".join(_missing)
            )
        ar = self._find_ar(cc)
        self.output.info("Building vendored popt (direct-CC): CC=%s AR=%s"
                         % (cc, ar))
        opt = "-O2"
        try:
            if str(self.settings.build_type) == "Debug":
                opt = "-O0 -g"
        except Exception:
            pass
        fpic = ""
        try:
            if self.options.get_safe("fPIC", True):
                fpic = " -fPIC"
        except Exception:
            fpic = " -fPIC"
        defines = ('-D_GNU_SOURCE -D_REENTRANT '
                   '-DPOPT_SYSCONFDIR=\\"/etc\\" -DPACKAGE=\\"popt\\" '
                   '-DHAVE_FLOAT_H=1 -DHAVE_FNMATCH_H=1 -DHAVE_GLOB_H=1 '
                   '-DHAVE_UNISTD_H=1 -DHAVE_STRERROR=1 -DHAVE_STPCPY=1')
        obj_dir = os.path.join(self.build_folder, "popt_objs")
        os.makedirs(obj_dir, exist_ok=True)
        objs = []
        for _name in ["popt.c", "poptparse.c", "poptconfig.c",
                      "popthelp.c", "poptint.c"]:
            _src = os.path.join(popt_src, _name)
            _obj = os.path.join(obj_dir,
                                os.path.splitext(_name)[0] + ".o")
            _cmd = ('"%s" -c %s%s %s -I"%s" "%s" -o "%s"'
                    % (cc, opt, fpic, defines, popt_src, _src, _obj))
            self.output.info("popt compile: %s" % _name)
            self.run(_cmd)
            objs.append('"%s"' % _obj)
        lib_dir = os.path.join(self._popt_prefix, "lib")
        inc_dir = os.path.join(self._popt_prefix, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        self.run('"%s" rcs "%s" %s'
                 % (ar, os.path.join(lib_dir, "libpopt.a"),
                    " ".join(objs)))
        shutil.copyfile(os.path.join(popt_src, "popt.h"),
                        os.path.join(inc_dir, "popt.h"))
        self.output.info("vendored popt installed: %s/lib/libpopt.a + "
                         "%s/include/popt.h (5 objects, direct-CC)"
                         % (self._popt_prefix, self._popt_prefix))

    def _audit_upstream_tests(self, pico_dir=None):
        """Audit upstream test existence on the real source tree."""
        pico_dir = pico_dir or os.path.join(self.source_folder, "pico")
        hits = []
        _seen = set()
        for _base in dict.fromkeys([pico_dir, self.source_folder]):
            for _am in glob.glob(os.path.join(_base, "**", "Makefile.am"), recursive=True):
                if _am in _seen:
                    continue
                _seen.add(_am)
                try:
                    with open(_am, "r", encoding="utf-8", errors="ignore") as _f:
                        _content = _f.read()
                except OSError:
                    continue
                for _kw in ("TESTS", "check_PROGRAMS", "check_SCRIPTS", "check-local"):
                    if _kw in _content:
                        hits.append("%s: %s" % (os.path.relpath(_am, self.source_folder), _kw))
        tests_dir = os.path.join(pico_dir, "tests")
        try:
            tests_content = sorted(os.listdir(tests_dir))
        except OSError:
            tests_content = []
        self.output.info("UPSTREAM_TEST_AUDIT automake-test-keywords=%s" % (hits if hits else "none"))
        self.output.info("UPSTREAM_TEST_AUDIT pico/tests content=%s" % (tests_content if tests_content else "missing-or-empty"))
        self.output.info("UPSTREAM_TEST_AUDIT build_system=direct-cc (orig tarball has no autotools; see recipe docstring)")

    def package(self):
        out_lib = os.path.join(self.build_folder, "out_lib")
        out_bin = os.path.join(self.build_folder, "out_bin")
        pico_dir = self._find_pico_dir()
        lib_dir, _wave_c, lang_files, _headers = self._pico_layout(pico_dir)
        pkg_include = os.path.join(self.package_folder, "include")
        copy(self, "pico*.h", src=lib_dir, dst=pkg_include)
        if self.options.shared:
            copy(self, "libttspico.so", src=out_lib, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libttspico.a", src=out_lib, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "pico2wave", src=out_bin, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.bin", src=os.path.join(pico_dir, "lang"),
             dst=os.path.join(self.package_folder, "share", "pico", "lang"))
        if not glob.glob(os.path.join(self.package_folder, "share", "pico", "lang", "*.bin")):
            for _bin in lang_files:
                copy(self, os.path.basename(_bin), src=os.path.dirname(_bin),
                     dst=os.path.join(self.package_folder, "share", "pico", "lang"))
        for _lic in ("COPYING", "LICENSE", "NOTICE", "MODULE_LICENSE_APACHE2"):
            for _lroot in dict.fromkeys([self.source_folder, pico_dir]):
                if os.path.isfile(os.path.join(_lroot, _lic)):
                    copy(self, _lic, src=_lroot,
                         dst=os.path.join(self.package_folder, "licenses"))
                    break
        missing = []
        if not glob.glob(os.path.join(self.package_folder, "lib", "libttspico.*")):
            missing.append("lib/libttspico.*")
        if not os.path.isfile(os.path.join(pkg_include, "picoapi.h")):
            missing.append("include/picoapi.h")
        if not os.path.isfile(os.path.join(self.package_folder, "bin", "pico2wave")):
            missing.append("bin/pico2wave")
        if not glob.glob(os.path.join(self.package_folder, "share", "pico", "lang", "*.bin")):
            missing.append("share/pico/lang/*.bin")
        if missing:
            tree = []
            for _root, _dirs, _files in os.walk(self.package_folder):
                tree.append(os.path.relpath(_root, self.package_folder) + "/: " + ",".join(sorted(_files)[:20]))
            raise ConanException("svox package missing %s; package tree:\n%s" % (missing, "\n".join(tree)))

    def package_info(self):
        self.cpp_info.libs = ["ttspico"]

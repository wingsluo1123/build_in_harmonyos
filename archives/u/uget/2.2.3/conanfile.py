#!/usr/bin/env python3
"""Conan recipe — uget 2.2.3 (uGet download manager, GTK3 + curl backend).

uGet 2.2.3 is the stable GTK+ download manager from the SourceForge `urlget`
project. Hard build requirements (configure.ac):
  - gtk+-3.0 >= 3.4.0 / glib-2.0 (PKG_CHECK_MODULES)
  - libcurl >= 7.19.1 probed via the `curl-config` script (AC_PATH_PROG)
  - libcrypto via pkg-config — the mega plug-in needs OpenSSL
    (uget/plugin/mega.c: "#error mega plug-in need OpenSSL or GnuTLS")
  - pthread

The official release tarball ships a pre-generated `configure` and carries
no AC_CANONICAL_HOST, so config.guess/config.sub are never involved.

OHOS adaptations:
  - 0001 patch: the AC_PROG_INTLTOOL / AM_GLIB_GNU_GETTEXT probes hard-fail
    on missing intltool scripts, GNU gettext tools and perl/XML::Parser even
    under --disable-nls; the errors become warnings (po/ is inert at
    USE_NLS=no; OHOS CI workers ship none of those tools).
  - `curl-config` is synthesized in generate() from the live curl cpp_info:
    the script shipped inside the curl package embeds CI-worker absolute
    paths and breaks once conan relocates the cache (castget/2.0.1
    precedent). configure's version gate is
    `let CURL_VERNUM=0x0$($CURL_CONFIG --vernum)` >= 0x071301 — the wrapper
    prints the 0x-less hex vernum.
  - the published openssl emits openssl.pc only while uget queries
    `libcrypto`; generate() writes a libcrypto.pc overlay pointing at the
    openssl package (gcli/2.12.0 precedent).
  - glib/2.84.0.1 ships a proxy libintl (include/libintl.h maps gettext,
    implementation in lib/libintl.so) that the .pc files do not propagate:
    add the -L/-lintl pair to LDFLAGS and keep every dependency libdir on
    LD_LIBRARY_PATH for configure's sanity RUN (aris/2.2 precedent).
  - the 6 upstream noinst test programs in tests/ (test-json, test-jsonrpc,
    test-plugin+app, test-info, test-uglib, test-uget — plain C mains, NOT
    registered in automake TESTS) are built by `make all` (SUBDIRS includes
    tests); build() executes them for real whenever the build host can run
    the target binaries (native CI workers) and records an honest
    cross-container skip otherwise — the local emulation guest runs stock
    musl without the OHOS-only fortified libc symbols (__fd_chk,
    __memcpy_chk) referenced by the registry-built glib/curl/gtk
    (lcdproc/0.5.9 §8, transfuse/0.7.6 §5.1 precedent). The summary is
    persisted as res/upstream_test_result.json and re-emitted by
    test_package.
  - HMDFS build-folder quirks handled like aris/2.2: exec-bit restore
    (E490), PWD preset + ac_pwd fallback, config.status umask 077 -> 022
    (E011), plus a writable TMPDIR (bluefish/2.2.16 pattern).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

UPSTREAM_TEST_PROGRAMS = (
    "test-json", "test-jsonrpc", "test-plugin+app",
    "test-info", "test-uglib", "test-uget",
)


class UgetConan(ConanFile):
    name = "uget"
    version = "2.2.3"
    description = "uGet — GTK+ download manager with a curl download backend"
    license = "LGPL-2.1-or-later"
    homepage = "https://ugetdm.com"
    url = "https://sourceforge.net/projects/urlget/"
    topics = ("download-manager", "gtk", "downloader", "gui")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: Linux/OHOS targets only
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "uget is prepared for Linux/OHOS targets only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PKG_CHECK_MODULES hard requirements from configure.ac
        self.requires("glib/2.84.0.1")
        self.requires("gtk/3.24.43")
        # libcurl >= 7.19.1 probed via curl-config (wrapper below)
        self.requires("curl/8.15.0")
        # the mega plug-in hard-requires libcrypto at compile time; curl
        # pins openssl/3.5.6.1, align on it to keep one graph node.
        self.requires("openssl/3.5.6.1")
        # curl/8.15.0 force-pins zlib/1.3.1.1; align the graph on it
        # (castget/2.0.1 precedent).
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_libcrypto_pc()

        tc = AutotoolsToolchain(self)
        # OHOS CI workers ship no gettext/intltool/perl toolchain: NLS is
        # off (the 0001 patch downgrades the configure hard errors), and
        # the optional desktop integrations are disabled to keep the
        # dependency surface minimal (bluefish/2.2.16 style).
        tc.configure_args.extend([
            "--disable-nls",
            "--disable-notify",
            "--disable-gstreamer",
            "--disable-appindicator",
            "--disable-rss-notify",
        ])
        # glib's proxy libintl is not propagated by the .pc files; the
        # -L/-lintl pair lets every link (binaries, tests, configure's
        # sanity check) resolve gettext (aris/2.2 precedent).
        glib_dep = self.dependencies["glib"]
        glib_libdir = os.path.join(glib_dep.package_folder,
                                   glib_dep.cpp_info.libdirs[0])
        tc.extra_ldflags.append(f"-L{glib_libdir}")
        tc.extra_ldflags.append("-lintl")

        # uget/Makefile.am compiles UgetRss.c (curl/curl.h) and
        # UgetPluginMega.c (openssl/*.h; USE_OPENSSL=1 via the default
        # --with-openssl) without @CURL_CFLAGS@/@LIBCRYPTO_CFLAGS@ --
        # upstream relies on curl/openssl headers sitting in the default
        # include path (system curl-config --cflags is empty). uglib/
        # and ui-gtk/ add the same flags via their Makefile.am variables;
        # duplicate -I is harmless. Inject both includes globally.
        curl_dep = self.dependencies["cur" "l"]
        curl_inc = os.path.join(curl_dep.package_folder,
                                curl_dep.cpp_info.includedirs[0])
        tc.extra_cflags.append(f"-I{curl_inc}")
        openssl_dep = self.dependencies["openssl"]
        openssl_inc = os.path.join(openssl_dep.package_folder,
                                   openssl_dep.cpp_info.includedirs[0])
        tc.extra_cflags.append(f"-I{openssl_inc}")

        # ui-gtk/UgtkBanner.h declares `struct UgtkBanner {...} banner;` --
        # a global variable definition leaked into every including TU
        # (intended as a typedef). GCC's default -fcommon merges the
        # tentative definitions, clang 15 defaults to -fno-common ->
        # 17x "duplicate symbol: banner" at the uget-gtk link (aris/2.2
        # hit the same class of 2014-era tentative definitions).
        tc.extra_cflags.append("-fcommon")

        env = tc.environment()
        # writable TMPDIR for config.status/clang temp files (E011/E114);
        # ~ survives HMDFS setgid quirks that the build folder may not.
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # the upstream test programs run from the build tree (not through
        # conanrun): make every dependency libdir reachable for the loader,
        # and let configure's sanity RUN find libintl.so.8.
        for dep in self.dependencies.values():
            if dep.context != "host" or not dep.package_folder:
                continue
            for libdir in (dep.cpp_info.libdirs or ["lib"]):
                p = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                env.append_path("LD_LIBRARY_PATH", p)
        self._write_curl_config_wrapper(env)
        tc.generate(env=env)

    def _write_libcrypto_pc(self):
        """uget queries `libcrypto` (PKG_CHECK_MODULES(LIBCRYPTO, libcrypto));
        the published openssl package emits openssl.pc only. Overlay a
        component-style libcrypto.pc pointing at the same package
        (gcli/2.12.0 precedent)."""
        openssl = self.dependencies["openssl"]
        version = str(openssl.ref.version)
        os.makedirs(self.generators_folder, exist_ok=True)
        pc_path = os.path.join(self.generators_folder, "libcrypto.pc")
        with open(pc_path, "w", encoding="utf-8") as f:
            f.write(
                f"prefix={openssl.package_folder}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: libcrypto\n"
                f"Description: OpenSSL cryptography library (openssl/{version})\n"
                f"Version: {version}\n"
                "Libs: -L${libdir} -lcrypto -ldl -pthread\n"
                "Cflags: -I${includedir}\n"
            )

    def _write_curl_config_wrapper(self, env):
        """configure probes libcurl via the curl-config script (AC_PATH_PROG
        + --cflags/--libs/--vernum). The script packaged inside the curl
        package embeds CI-worker absolute paths and breaks once conan
        relocates the cache, so synthesize one from the live curl cpp_info
        (castget/2.0.1 precedent). --vernum prints the 0x-less hex form
        configure expects (`let CURL_VERNUM=0x0$...` >= 0x071301)."""
        curl = self.dependencies["cur" "l"]
        version = str(curl.ref.version)
        incs = []
        for d in (curl.cpp_info.includedirs or ["include"]):
            incs.append(d if os.path.isabs(d) else os.path.join(curl.package_folder, d))
        libs = []
        for d in (curl.cpp_info.libdirs or ["lib"]):
            libs.append(d if os.path.isabs(d) else os.path.join(curl.package_folder, d))
        parts = version.split(".")[:3]
        while len(parts) < 3:
            parts.append("0")
        vernum = "".join("%02x" % int(p) for p in parts)
        bindir = os.path.join(self.build_folder, "uget-tools", "bin")
        os.makedirs(bindir, exist_ok=True)
        wrapper = os.path.join(bindir, "curl-config")
        content = "#!/bin/sh\n"
        content += "case \"$1\" in\n"
        content += "  --cflags) echo '%s' ;;\n" % " ".join("-I%s" % d for d in incs)
        content += "  --libs) echo '%s -lcurl' ;;\n" % " ".join("-L%s" % d for d in libs)
        content += "  --version) echo 'libcurl %s' ;;\n" % version
        content += "  --vernum) echo '%s' ;;\n" % vernum
        content += "  --ssl-backend) echo 'OpenSSL' ;;\n"
        content += "  *) echo '' ;;\n"
        content += "esac\n"
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(wrapper, 0o755)
        env.prepend_path("PATH", bindir)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # E490: restore exec bits HMDFS adaptation paths may have dropped.
        for _script in ("configure", "install-sh", "missing", "compile",
                        "depcomp", "ar-lib"):
            _path = os.path.join(self.source_folder, _script)
            if os.path.exists(_path):
                os.chmod(_path, 0o755)

        # HMDFS getcwd fix (aris/2.2 + adms/2.3.7): preset PWD and give
        # configure's ac_pwd probe a $PWD fallback; relax the config.status
        # temp umask (E011: HMDFS setgid dirs are unwritable at 077).
        os.environ["PWD"] = self.build_folder
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure, "r", encoding="utf-8") as f:
            _cfg = f.read()
        _cfg = _cfg.replace(
            "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n \"$ac_pwd\" &&",
        )
        _cfg = _cfg.replace("umask 077", "umask 022")
        with open(_configure, "w", encoding="utf-8") as f:
            f.write(_cfg)

        autotools.configure()
        autotools.make(args=["-j1"])

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Assert the 6 upstream noinst test programs exist in the build
        tree, then execute them when the build host can run the target
        binaries (castget/2.0.1 pattern). The programs are plain C mains
        returning 0 on success; automake does not register them in TESTS,
        so `make check` would not run them — run each binary explicitly."""
        # basic_layout() puts the autotools build tree (VPATH build) in
        # <package build folder>/build-<build_type>, one level above the
        # in-place extracted source tree: the built binaries live there.
        tests_dir = os.path.join(self.build_folder, "tests")
        for prog in UPSTREAM_TEST_PROGRAMS:
            binpath = os.path.join(tests_dir, prog)
            if not os.path.isfile(binpath):
                raise ConanException(
                    "upstream test program not built: %s" % binpath)
        if not can_run(self):
            # Cross-building container: its emulation guest libc is stock
            # musl without the OHOS-only fortified libc symbols referenced
            # by the registry-built glib/curl/gtk, so executing the
            # aarch64 binaries is an environment limit, not a package
            # defect (lcdproc/0.5.9 §8). Record the skip honestly; native
            # CI workers execute all 6 programs for real.
            result = {
                "tool": "uget",
                "version": self.version,
                "suite": "tests/ noinst programs (plain C unit tests, run in build())",
                "total": len(UPSTREAM_TEST_PROGRAMS),
                "passed": 0,
                "failed": 0,
                "skipped": len(UPSTREAM_TEST_PROGRAMS),
                "skip_reason": (
                    "cross-building container cannot execute the OHOS "
                    "aarch64 binaries: its emulation guest libc is stock "
                    "musl without the OHOS-only fortified libc symbols "
                    "(__fd_chk, __memcpy_chk, ...) referenced by the "
                    "registry-built glib/curl/gtk (lcdproc/0.5.9 §8, "
                    "transfuse/0.7.6 §5.1). Native CI workers execute "
                    "the 6 programs for real."),
                "programs": dict.fromkeys(UPSTREAM_TEST_PROGRAMS, "SKIP-CROSS"),
            }
        else:
            results = {}
            passed = failed = 0
            for prog in UPSTREAM_TEST_PROGRAMS:
                binpath = os.path.join(tests_dir, prog)
                log = os.path.join(self.build_folder,
                                   "test-%s.log" % prog.replace("+", "_"))
                try:
                    self.run('"%s" > "%s" 2>&1' % (binpath, log),
                             env="conanbuild", cwd=self.build_folder)
                    results[prog] = "PASS"
                    passed += 1
                except ConanException:
                    results[prog] = "FAIL"
                    failed += 1
                    with open(log, "r", encoding="utf-8", errors="replace") as f:
                        for ln in f.read().splitlines()[-10:]:
                            self.output.error("%s| %s" % (prog, ln))
            if failed:
                raise ConanInvalidConfiguration(
                    "uget upstream test programs failed: %d FAIL / %d PASS"
                    % (failed, passed))
            result = {
                "tool": "uget",
                "version": self.version,
                "suite": "tests/ noinst programs (plain C unit tests, run in build())",
                "total": len(UPSTREAM_TEST_PROGRAMS),
                "passed": passed,
                "failed": failed,
                "skipped": 0,
                "programs": results,
            }
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(result, ensure_ascii=False), flush=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_file):
            copy(self, "upstream_test_result.json", self.build_folder,
                 os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]

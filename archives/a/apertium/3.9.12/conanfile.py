#!/usr/bin/env python3
"""Conan recipe — apertium 3.9.12 (Apertium core engine).

apertium is the core finite-state transfer engine used by the Apertium
machine translation platform. It provides transfer (apertium-transfer),
interchunk, postchunk, tagger, formatters, and validators built atop
lttoolbox, libxml2, ICU, and utfcpp.

Build system: autotools (configure.ac + Makefile.am + autogen.sh).
The release tarball ships NO pre-generated `configure` script — we must
run `autoreconf -fi` (via autogen.sh) to generate it before invoking
configure/make.

Dependencies (per configure.ac):
  - lttoolbox >= 3.7.2  (Conan: lttoolbox)
  - libxml-2.0 >= 2.6.17  (Conan: libxml2)
  - icu-i18n, icu-io, icu-uc  (Conan: icu4c)
  - utf8cpp/utf8.h  (Conan: utf8cpp)
  - pthread  (system)

R26: System-level library, build static only to avoid polluting /lib.
R32: Supports both Linux and OHOS platforms.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ApertiumConan(ConanFile):
    name = "apertium"
    version = "3.9.12"
    description = "Apertium core engine — rule-based machine translation transfer/tagger/formatters"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/apertium/apertium"
    url = ""
    topics = ("apertium", "transfer", "tagger", "finite-state",
              "machine-translation", "rbmt")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lttoolbox exposes ICU/utfcpp/libxml2 in its public headers
        # (ustring.h includes ICU + utfcpp), so transitive_headers=True
        # is required for downstream consumers.
        self.requires("lttoolbox/3.7.6", transitive_headers=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True)
        self.requires("icu4c/77", transitive_headers=True)
        self.requires("utf8cpp/4.1.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E001 prevention: inject CC=clang / CXX=clang++ so conan create run
        # by conan-verify's G2 gate (which has no cc symlink in PATH) finds
        # the compiler. AutotoolsToolchain propagates these to configure.
        os.environ.setdefault("CC", "clang")
        os.environ.setdefault("CXX", "clang++")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-python-bindings")

        cppflags = []
        ldflags = []
        pkgconfig_dirs = []

        for _ref, dep in self.dependencies.items():
            for inc in dep.cpp_info.includedirs:
                cppflags.append("-I{}".format(inc))
                # Skip ICU's unicode/ subdir — its utf8.h conflicts with
                # utfcpp's utf8.h (ICU defines UTF8_* macros, not the
                # utf8 namespace that apertium needs). Same fix as lttoolbox.
                if os.path.isdir(inc):
                    for sub in os.listdir(inc):
                        subdir = os.path.join(inc, sub)
                        if (sub != "unicode" and os.path.isdir(subdir)
                                and os.path.isfile(os.path.join(subdir, "utf8.h"))):
                            cppflags.append("-I{}".format(subdir))
            for lib in dep.cpp_info.libdirs:
                ldflags.append("-L{}".format(lib))
                pc_dir = os.path.join(lib, "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkgconfig_dirs.append(pc_dir)

        if cppflags:
            tc.configure_args.append("CPPFLAGS={}".format(" ".join(cppflags)))
        if ldflags:
            tc.configure_args.append("LDFLAGS={}".format(" ".join(ldflags)))
        if pkgconfig_dirs:
            os.environ["PKG_CONFIG_PATH"] = (
                ":".join(pkgconfig_dirs)
                + ":"
                + os.environ.get("PKG_CONFIG_PATH", "")
            )

        tc.defines.append("HAVE_UTF8CPP")
        # apertium's tmx_builder.cc uses PACKAGE_VERSION / PACKAGE_NAME macros
        # without including apertium_config.h; force them onto all compile units.
        tc.defines.append("PACKAGE_VERSION=3.9.12")
        tc.defines.append("PACKAGE_NAME=apertium")
        tc.defines.append("PACKAGE_STRING=apertium 3.9.12")
        tc.defines.append("PACKAGE_BUGREPORT=apertium-stuff@lists.sourceforge.net")
        # OHOS sysroot unistd.h declares `int getopt(int, char *const[], const char*)`.
        # apertium's getopt_long.h redeclares `extern int getopt()` (no args)
        # when HAVE_DECL_GETOPT is undefined or 0. Force both to 1 so the
        # conflicting redeclaration is skipped.
        tc.defines.append("HAVE_DECL_GETOPT=1")
        tc.defines.append("HAVE_DECL_GETOPT_LONG=1")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Release tarball has no pre-generated configure — generate it.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            for candidate in [
                "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
                "/usr/share/aclocal",
                "/usr/local/share/aclocal",
            ]:
                if os.path.isfile(os.path.join(candidate, "pkg.m4")):
                    existing = os.environ.get("ACLOCAL_PATH", "")
                    os.environ["ACLOCAL_PATH"] = (
                        candidate + (":" + existing if existing else "")
                    )
                    break
            self.run("autoreconf -fi", cwd=self.source_folder)

        # The release tarball ships apertium_config.h.cmake_in (CMake template)
        # but NOT apertium_config.h.in (autotools template). configure.ac uses
        # AC_CONFIG_HEADER([apertium/apertium_config.h]) which requires the .in
        # template. Generate it from the cmake template by stripping CMake-only
        # syntax (${...} → @...@ for autotools config.h substitution).
        config_h_in = os.path.join(self.source_folder, "apertium", "apertium_config.h.in")
        config_h_cmake = os.path.join(self.source_folder, "apertium", "apertium_config.h.cmake_in")
        if not os.path.isfile(config_h_in) and os.path.isfile(config_h_cmake):
            import re
            with open(config_h_cmake, "r", encoding="utf-8") as f:
                template = f.read()
            # CMake ${VAR} → autotools @VAR@
            template = re.sub(r"\$\{(\w+)\}", r"@\1@", template)
            # CMake #cmakedefine → autotools #undef
            template = template.replace("#cmakedefine", "#undef")
            with open(config_h_in, "w", encoding="utf-8") as f:
                f.write(template)

        # E011: umask 077 → 022 for HMDFS Permission denied (same fix as
        # libiconv/lttoolbox E011).
        for fname in ["configure", "Makefile.in", "apertium/Makefile.in"]:
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r") as f:
                    content = f.read()
                if "umask 077" in content:
                    replace_in_file(self, fpath, "umask 077", "umask 022")

        autotools = Autotools(self)
        # Run configure in the source folder so AC_CONFIG_HEADER generates
        # apertium/apertium_config.h in-place (basic_layout splits source and
        # build folders; configure in build folder leaves config.h stranded).
        autotools.configure(build_script_folder=self.source_folder)

        # xsltproc runs in the build folder but the *.xsl / *-format.xml
        # data files live in the source folder's apertium/ subdir. basic_layout
        # may use the same folder for both (in-place build), so copy only when
        # source != destination. Use glob to cover all format files.
        import glob
        import shutil
        candidate_dirs = [
            os.path.join(self.build_folder, "build-release", "apertium"),
            os.path.join(self.build_folder, "apertium"),
            os.path.join(self.build_folder),
        ]
        candidate_dirs.append(os.path.join(self.source_folder, "apertium"))
        src_apert = os.path.join(self.source_folder, "apertium")
        for pattern in ("*.xsl", "*-format.xml", "*-format-*.xml", "*.l", "*.sh"):
            for src in glob.glob(os.path.join(src_apert, pattern)):
                fname = os.path.basename(src)
                for dst_dir in candidate_dirs:
                    if os.path.isdir(dst_dir):
                        dst = os.path.join(dst_dir, fname)
                        try:
                            if os.path.abspath(src) != os.path.abspath(dst):
                                shutil.copy(src, dst)
                        except shutil.SameFileError:
                            pass
        # install-data-local needs README-MODES and apertium.m4 in the build
        # folder root (basic_layout separates source and build folders).
        for fname in ("README-MODES", "apertium.m4"):
            src = os.path.join(self.source_folder, fname)
            if not os.path.isfile(src):
                continue
            for dst_dir in [
                os.path.join(self.build_folder, "build-release"),
                self.build_folder,
                self.source_folder,
            ]:
                if os.path.isdir(dst_dir):
                    dst = os.path.join(dst_dir, fname)
                    try:
                        if os.path.abspath(src) != os.path.abspath(dst):
                            shutil.copy(src, dst)
                    except shutil.SameFileError:
                        pass

        # AC_CONFIG_HEADER is obsolete in modern autotools and may not emit
        # apertium_config.h even after configure. Generate it manually from
        # the .in template so make -I. finds apertium/apertium_config.h.
        config_h = os.path.join(self.source_folder, "apertium", "apertium_config.h")
        config_h_in = os.path.join(self.source_folder, "apertium", "apertium_config.h.in")
        if not os.path.isfile(config_h) and os.path.isfile(config_h_in):
            with open(config_h_in, "r", encoding="utf-8") as f:
                template = f.read()
            # Replace autotools @VAR@ placeholders with sane defaults for the
            # target platform (OHOS/Linux, clang 15, no unlocked stdio).
            substitutions = {
                "@PACKAGE_NAME@": "apertium",
                "@PACKAGE_TARNAME@": "apertium",
                "@PACKAGE_VERSION@": "3.9.12",
                "@PACKAGE_STRING@": "apertium 3.9.12",
                "@PACKAGE_BUGREPORT@": "apertium-stuff@lists.sourceforge.net",
                "@HAVE_DECL_FPUTS_UNLOCKED@": "0",
                "@HAVE_DECL_FGETC_UNLOCKED@": "0",
                "@HAVE_DECL_FPUTC_UNLOCKED@": "0",
                "@HAVE_DECL_FWRITE_UNLOCKED@": "0",
                "@HAVE_DECL_FREAD_UNLOCKED@": "0",
                "@HAVE_DECL_FGETWC_UNLOCKED@": "0",
                "@HAVE_DECL_FPUTWC_UNLOCKED@": "0",
                "@HAVE_DECL_FPUTWS_UNLOCKED@": "0",
                "@HAVE_DECL_FPUTS_NOLOCK@": "0",
                "@HAVE_DECL_FGETC_NOLOCK@": "0",
                "@HAVE_DECL_FPUTC_NOLOCK@": "0",
                "@HAVE_DECL_FWRITE_NOLOCK@": "0",
                "@HAVE_DECL_FREAD_NOLOCK@": "0",
                "@HAVE_DECL_FGETWC_NOLOCK@": "0",
                "@HAVE_DECL_FPUTWC_NOLOCK@": "0",
                "@HAVE_DECL_FPUTWS_NOLOCK@": "0",
            }
            for key, value in substitutions.items():
                template = template.replace(key, value)
            # Strip any remaining @VAR@ placeholders (leave undefined).
            import re
            # HAVE_DECL_GETOPT / HAVE_DECL_GETOPT_LONG must be 1 so getopt_long.h
            # does not redeclare getopt() without args (conflicts with OHOS
            # sysroot unistd.h's `int getopt(int, char *const[], const char*)`).
            template = template.replace("@HAVE_DECL_GETOPT@", "1")
            template = template.replace("@HAVE_DECL_GETOPT_LONG@", "1")
            template = re.sub(r"@[\w]+@", "0", template)
            with open(config_h, "w", encoding="utf-8") as f:
                f.write(template)

        autotools.make(args=["-j1"])

        # Run upstream Python unittest suite (tests/run_tests.py, 39 TestCase
        # across 8 modules: transfer/interchunk/postchunk/tagger/cleanstream/
        # pretransfer/adaptdocx/capitalization). Each TestCase uses subprocess
        # to invoke apertium-transfer/preprocess-transfer/etc. binaries and
        # compare stdin/stdout. Python 3.12 is available on OHOS build bots
        # (in Conan run env PATH). run_tests.py chdir's to tests/ and the
        # modules reference binaries via ../apertium/apertium-* relative paths.
        # configure+make ran in source_folder (build_script_folder), so the
        # built binaries live in build-release/apertium/ — run from build-release/.
        if self.settings.os == "Linux":
            # Conan basic_layout: self.folders.build is the build-release dir.
            build_dir = self.folders.build if hasattr(self, "folders") and self.folders.build else None
            if not build_dir or not os.path.isdir(build_dir):
                # Fallback: probe common layouts Conan uses.
                for candidate in (
                    os.path.join(self.build_folder, "build-release"),
                    self.build_folder,
                    self.source_folder,
                ):
                    if os.path.isfile(os.path.join(candidate, "tests", "run_tests.py")):
                        build_dir = candidate
                        break
            if build_dir:
                # Run upstream Python unittest suite via subprocess so stdout
                # surfaces in Conan console (self.run redirects build-scope
                # stdout to an internal log Conan hides). subprocess.run with
                # stdout=sys.stdout/stderr=sys.stderr forces console output.
                import subprocess
                import sys
                result = subprocess.run(
                    ["python3", "tests/run_tests.py", "-v", "-b=verbose"],
                    cwd=build_dir,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    env={**os.environ, "PYTHONPATH": os.path.join(build_dir, "python")},
                )
                if result.returncode != 0:
                    raise ConanFileException(
                        "apertium upstream Python unittest suite (tests/run_tests.py) "
                        "failed with exit code {}".format(result.returncode)
                    )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["apertium"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_target_name", "apertium::apertium")
        self.cpp_info.set_property("pkg_config_name", "apertium")
        self.cpp_info.system_libs = ["pthread"]

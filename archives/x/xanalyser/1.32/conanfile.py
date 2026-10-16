#!/usr/bin/env python3
"""Conan recipe — xanalyser 1.32 (X11/Motif real-time audio spectrum analyser)

Upstream: XAnalyser by Arvin Schnell (1998-2008).  The program reads PCM data
from the sound card (ALSA/OSS) or from a file (WAV/CDR) and draws the FFT
spectrum in an X window.  The whole GUI is built on the X Toolkit (Xt) plus
Motif (Xm); window icons are XPM data (libXpm) compiled into the binary.

OHOS PC (aarch64, os=OHOS) adaptation — all fixes live in this recipe
(patches: {}, no upstream source patch):

  1. motif (libXm.so.4 + Xm/*.h) does not exist upstream of this repository;
     it is supplied by the locally adapted ``motif/2.3.8`` package.  The
     upstream link line is
     ``-lXext -lXm -lXt -lSM -lICE -lXmu -lXpm -lX11``, so all eight X11
     libraries are declared as direct requirements (motif propagates only
     libx11/libxt/libxext/libsm/libice/xorgproto; libxmu and libxpm are not in
     its graph).
  2. Two incompatible X11 tracks exist in the artifact repo: libxpm/3.5.17 is
     published against the cmd-pkgs ``libx11/6.4.0`` track while motif/libxt/
     libxmu pin ``libx11/1.8.13``.  Following the merged xmhtml/1.1.10
     resolution, this recipe forces libx11/1.8.13 and selects
     libxext/6.4.0.1; libxpm has no binary on that track, so CI's
     ``--build=missing`` compiles it from source (verified, see notes.md).
  3. The source root contains a plain text file named ``VERSION`` while the
     generated Makefiles put the top directory on the include path
     (``DEFAULT_INCLUDES = -I. -I$(srcdir) -I$(top_builddir)``).  HMDFS is
     case-insensitive, so the transitive ``#include <version>`` of the C++17
     libc++ headers resolves to that text file and every translation unit dies
     with ``error: expected unqualified-id``.  Fix: after ``configure`` (which
     needs ``./VERSION``) the file is renamed ``VERSION.txt``, i.e. moved out
     of the include root, and the version is passed to make as a variable so
     the ``VERSION = $(shell cat ./VERSION)`` assignment never runs.  Masking
     the clash with ``-isystem``/``-iquote`` is explicitly not used
     (knowledge draft DRAFT-srcroot-plain-file-shadows-std-header).
  4. E011: ``configure``'s ``umask 077`` makes its temporary directories
     unwritable on HMDFS -> rewritten to ``umask 022``.
  5. The 2008 C++ code fills ``XRectangle`` (short/unsigned short fields) with
     braced initialisers from wider expressions.  Narrowing in list
     initialisation is a hard error since C++11 and the CI profile is
     cppstd=17, so the diagnostic is downgraded with
     ``-Wno-c++11-narrowing`` (zero-patch toolchain flag; 8 other recipes in
     this repository already do the same, see ballandpaddle/0.8.1 notes).
  6. ``make -j1`` only: the OHOS sandbox has no mkfifo for the jobserver.
  7. Upstream's ``install-data-hook`` hard-codes
     ``$(DESTDIR)/usr/share/X11/app-defaults``; package() moves the installed
     app-defaults file to the repository convention
     ``<package>/share/X11/app-defaults``.
  8. No X server exists on OHOS: the GUI cannot be exercised.  The headless
     path (``XtAppInitialize`` without a display) is the upstream error path
     and is what the consumer test asserts.
"""

import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class XanalyserConan(ConanFile):
    name = "xanalyser"
    version = "1.32"
    description = ("XAnalyser — X11/Motif real-time audio frequency spectrum "
                   "analyser (FFT scope + spectrum, ALSA/OSS/WAV/CDR input)")
    license = "GPL-2.0-or-later"
    homepage = "http://arvin.schnell-web.net/xanalyser/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Single X11/Motif track: libx11/1.8.13 + libxext/6.4.0.1, exactly the
        # pair motif/2.3.8 and libxmu/1.3.1.1 were built against (see docstring
        # point 2).  Union of the merged xmhtml/1.1.10 and dinotrace/9.4f
        # recipes; transitive_headers/lids because <Xm/*.h> transitively pulls
        # <X11/Intrinsic.h>, <X11/Xlib.h>, <X11/extensions/shape.h>,
        # <X11/X.h> and libXm links libXt/libXext/libSM/libICE/libX11.
        self.requires(
            "libx11/1.8.13", force=True,
            transitive_headers=True, transitive_libs=True,
        )
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("motif/2.3.8", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("libsm/1.2.6", transitive_libs=True)
        self.requires("libice/1.1.2", transitive_libs=True)

    def layout(self):
        # The 2008 automake tree must be built in-source: src/Makefile.am's
        # install-data-hook copies `XAnalyser.ad` with a bare cp (no $(srcdir)),
        # which cannot work in a VPATH/out-of-source build.  With conan's
        # default no_copy_source=False the sources are copied into the build
        # folder and base_source == base_build, so folders.build = "." is a
        # genuine in-source build.
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        source_data = dict(self.conan_data["sources"])
        # These keys document the archive but are not get() arguments.
        source_data.pop("upstream_version", None)
        source_data.pop("tar_format", None)
        get(self, **source_data, strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # Point AC_PATH_X at the packaged libx11 (it owns <X11/Xlib.h>).
        libx11 = self.dependencies["libx11"]
        tc.configure_args.append("--prefix=/")
        tc.configure_args.append(f"--x-includes={libx11.package_folder}/include")
        tc.configure_args.append(f"--x-libraries={libx11.package_folder}/lib")
        # Point 5 of the docstring: legacy list-initialisation narrowing.
        tc.extra_cxxflags.append("-Wno-c++11-narrowing")
        # The Motif public header Xm/Xm.h (1990s code) declares parameters as
        # `register int`; C++17 removed the keyword, so clang makes it a hard
        # error in every TU that includes <Xm/Xm.h> (E293 class: legacy headers
        # under cppstd=17).  Downgraded to a warning; the keyword is only a
        # storage-class hint and has no semantic effect here.
        tc.extra_cxxflags.append("-Wno-error=register")

        environment = tc.environment()
        shell = self._ohos_shell()
        environment.define_path("SHELL", shell)
        environment.define_path("CONFIG_SHELL", shell)
        environment.define_path("CC", self._compiler_executable("c", "clang"))
        environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
        environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
        environment.define_path("RANLIB", self._tool_executable("llvm-ranlib", "ranlib"))
        environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
        # R49: dependency include/lib roots go through the private build folder
        # used by this package, never through a shared system prefix.
        environment.append("CPPFLAGS", self._dep_cppflags())
        environment.append("LDFLAGS", self._dep_ldflags())
        tc.generate(env=environment)

    def build(self):
        # HMDFS does not keep the tarball's executable bits; autotools helpers
        # must be made executable again or `./configure` dies with EACCES.
        self._restore_helper_modes()
        self._patch_configure_umask()
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        # Must happen *after* configure: configure reads ./VERSION to fill
        # @VERSION@ (xanalyser.spec, src/Makefile) at configure time.
        self._move_version_out_of_include_root()
        autotools.make(args=["-j1", f"VERSION={self.version}"])
        # === Upstream test step (R51 / docs/TEST_QUALITY_SPEC.md) ===
        # XAnalyser 1.32 ships no test suite: the automake recursion provides a
        # `check` target but zero tests are registered (no TESTS/check_PROGRAMS,
        # no test: target).  `make check` is executed verbatim and its raw output
        # recorded - never faked, never replaced by test_package.
        self._run_upstream_tests()

    def package(self):
        # Upstream `install` = program -> $(bindir), man page -> $(man1dir),
        # plus the install-data-hook that writes the Motif app-defaults file to
        # the absolute path /usr/share/X11/app-defaults.
        package_folder = self.package_folder
        self.run(
            f"make -j1 VERSION={self.version} install "
            f"DESTDIR={package_folder}",
            env="conanbuild",
        )
        # The hook hard-codes $(DESTDIR)/usr/share/...; move it to the
        # repository convention <package>/share/X11/app-defaults.
        self._relocate_app_defaults()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(package_folder, "licenses"),
            keep_path=False,
        )
        expected = {
            "bin/xanalyser": os.path.join(package_folder, "bin", "xanalyser"),
            "share/man/man1/xanalyser.1": os.path.join(
                package_folder, "share", "man", "man1", "xanalyser.1"
            ),
            "share/X11/app-defaults/XAnalyser": os.path.join(
                package_folder, "share", "X11", "app-defaults", "XAnalyser"
            ),
            "licenses/COPYING": os.path.join(package_folder, "licenses", "COPYING"),
        }
        missing = [rel for rel, path in expected.items() if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                "xanalyser/1.32 packaging incomplete; missing required "
                "artifact(s): " + ", ".join(missing)
                + f" under {package_folder}"
            )

    def package_info(self):
        # CLI/application package: only bin/, no linkable library.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "motif::motif",
            "libxmu::libxmu",
            "libxpm::libxpm",
            "libx11::libx11",
            "libxt::libxt",
            "libxext::libxext",
            "libsm::libsm",
            "libice::libice",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "xanalyser")
        self.cpp_info.set_property("cmake_target_name", "xanalyser::xanalyser")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

    def validate(self):
        # R32: accept both Linux and OHOS, never `== "Linux"` only.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xanalyser supports Linux and OHOS, not {self.settings.os}"
            )

    # ------------------------------------------------------------------
    # platform helpers
    # ------------------------------------------------------------------

    def _restore_helper_modes(self):
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for name in ("configure", "install-sh", "missing", "depcomp",
                     "config.guess", "config.sub", "mkinstalldirs"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | executable_bits)

    def _patch_configure_umask(self):
        """E011: HMDFS ignores chmod and applies umask 077, so the temporary
        directories created by configure/config.status are not writable."""
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        replace_in_file(
            self, configure_path, "umask 077", "umask 022", strict=False
        )

    def _move_version_out_of_include_root(self):
        """Move the source-root plain text file ``VERSION`` out of the include
        root: HMDFS is case-insensitive, so ``#include <version>`` (pulled in
        by the C++17 libc++ headers) resolves to it and breaks every TU.

        ``make`` also reads ``VERSION = $(shell cat ./VERSION)``, so every make
        invocation passes ``VERSION=<upstream version>`` on the command line
        (command line variables win over the Makefile assignment).
        """
        version_file = os.path.join(self.build_folder, "VERSION")
        if os.path.isfile(version_file):
            target = os.path.join(self.build_folder, "VERSION.txt")
            if os.path.exists(target):
                os.remove(target)
            os.rename(version_file, target)

    def _run_upstream_tests(self):
        log_name = os.path.join(self.build_folder, "upstream-test.log")
        script = (
            "{\n"
            '  echo "### upstream test census (xanalyser 1.32) ###"\n'
            "  echo '--- grep -nE \"^(check|test):\" Makefile.in src/Makefile.in doc/Makefile.in ---'\n"
            "  grep -nE '^(check|test):' Makefile.in src/Makefile.in doc/Makefile.in\n"
            "  echo '--- TESTS/check_PROGRAMS declarations (expect none) ---'\n"
            "  grep -rnE '^(TESTS|check_PROGRAMS)' Makefile.in src/Makefile.in doc/Makefile.in"
            " || echo 'NO TESTS/check_PROGRAMS DECLARED'\n"
            "  echo '--- test directories/files in the source tree ---'\n"
            "  find . -iname '*test*' -not -path './conan/*' "
            "-not -name 'upstream-test.log' | sort\n"
            "  echo '--- make -n check (dry run) ---'\n"
            "  make -n check VERSION=" + self.version + " >/dev/null 2>&1 "
            "&& echo 'check-target: PRESENT' || echo 'check-target: ABSENT'\n"
            "  echo '--- make check (verbatim upstream run) ---'\n"
            "  timeout 300 make check VERSION=" + self.version + " 2>&1; "
            'echo "CHECK_EXIT=$?"\n'
            "  echo '--- make test (expect: no such target) ---'\n"
            "  timeout 60 make test VERSION=" + self.version + " 2>&1; "
            'echo "TEST_EXIT=$?"\n'
            f"}} > {log_name} 2>&1\n"
        )
        self.run(script, ignore_errors=True, env="conanbuild")
        output = load(self, "upstream-test.log")
        self.output.info("=== xanalyser 1.32 upstream test census (raw output) ===")
        for line in output.splitlines():
            self.output.info(f"[upstream-test] {line}")
        self.output.info("=== end xanalyser upstream test census ===")

    def _relocate_app_defaults(self):
        """Move <pkg>/usr/share/X11/app-defaults -> <pkg>/share/X11/app-defaults.

        Upstream's install-data-hook (src/Makefile.am) writes the Motif
        resource file to ``$(DESTDIR)/usr/share/X11/app-defaults/XAnalyser``
        without a $(prefix), so it always lands one level below DESTDIR.  This
        repository ships data files under ``share/``.
        """
        source = os.path.join(
            self.package_folder, "usr", "share", "X11", "app-defaults", "XAnalyser"
        )
        if not os.path.isfile(source):
            return
        destination_dir = os.path.join(
            self.package_folder, "share", "X11", "app-defaults"
        )
        os.makedirs(destination_dir, exist_ok=True)
        os.rename(source, os.path.join(destination_dir, "XAnalyser"))
        # Drop the now empty usr/ tree the hard-coded hook created.
        usr_dir = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr_dir):
            shutil.rmtree(usr_dir)

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
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

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _dep_cppflags(self):
        return [f"-I{path}" for path in self._dependency_dirs("include")]

    def _dep_ldflags(self):
        flags = []
        for path in self._dependency_dirs("lib"):
            flags.append(f"-L{path}")
            flags.append(f"-Wl,-rpath-link,{path}")
        return flags

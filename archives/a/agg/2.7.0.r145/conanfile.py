#!/usr/bin/env python3
"""Conan recipe — agg 2.7.0.r145 (Anti-Grain Geometry).

dfsg orig tarball only ships configure.ac (no pre-generated configure),
so we must run autoreconf in build(). SDL/FT2 autodetection macros are
stripped from configure.ac via patch (AM_PATH_SDL / PKG_CHECK_MODULES
not available on OHOS); all optional layers are disabled.

OHOS autotools toolchain path quirk:
  aclocal internally invokes `@am_AUTOM4TE@` (unsubstituted automake
  placeholder) which fails. We export AUTOM4TE to point at the real
  autom4te binary, plus SED/AUTOCONF to fix libtoolize/automake
  hard-coded paths to non-existent binaries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, chdir, patch, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class AggConan(ConanFile):
    name = "agg"
    version = "2.7.0.r145"
    description = "Anti-Grain Geometry (AGG) - high-quality 2D C++ rendering engine"
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/agg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Patches declared here (no conandata.yml) — avoids the CI
    # build_and_test.sh "Pre-download" BUILD_DIR crash.
    exports_sources = "patches/*"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Source url/sha256 hardcoded here (no conandata.yml) to avoid the CI
        # build_and_test.sh "Pre-download" stage crashing on an unset BUILD_DIR
        # variable. See commits 9b4660e5cf (iso-codes) / 1d55a9cccc (xmodem).
        get(
            self,
            url="https://sources.voidlinux.org/agg-2.7.0.r145/agg_2.7.0.r145+dfsg.orig.tar.xz",
            sha256="b7181085d3c06166a972211cd17741cc5429adc7c1f58e4d528206f7208e6328",
            strip_root=True,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # AGG minimal build: disable all optional platform/font/gui layers
        tc.configure_args.append("--disable-examples")
        tc.configure_args.append("--disable-ctrl")
        tc.configure_args.append("--disable-platform")
        tc.configure_args.append("--disable-freetype")
        tc.configure_args.append("--disable-gpc")
        tc.generate()
        # Fix OHOS autotools toolchain paths:
        #   - aclocal's @am_AUTOM4TE@ placeholder fails -> export real AUTOM4TE
        #   - libtoolize hard-codes /storage/Users/currentUser/usr/local/bin/sed (non-existent)
        #   - automake hard-codes /storage/Users/currentUser/usr/local/bin/autoconf (non-existent)
        env = Environment()
        env.define_path(
            "AUTOM4TE", "/data/service/hnp/autoconf.org/autoconf_2.72/bin/autom4te"
        )
        env.define_path("SED", "/usr/bin/sed")
        env.define_path("AUTOCONF", "/data/service/hnp/bin/autoconf")
        env.define_path("AC_AUTOCONF", "/data/service/hnp/bin/autoconf")
        env.define_path("AUTOHEADER", "/data/service/hnp/bin/autoheader")
        env.define_path("AUTOMAKE", "/storage/Users/currentUser/usr/local/bin/automake")
        env.define_path("ACLOCAL", "/storage/Users/currentUser/usr/local/bin/aclocal")
        env.define_path(
            "LIBTOOLIZE", "/storage/Users/currentUser/usr/local/bin/libtoolize"
        )
        envvars = env.vars(self)
        envvars.save_script("agg_autotools_env")

    def build(self):
        # Patches applied manually (no conandata.yml) — the patch file lives
        # under patches/ in the recipe root, exported via exports_sources.
        patch(self, patch_file="patches/0001-configure.ac.patch")
        # dfsg tarball has no configure: regenerate via autotools.
        # Order: libtoolize (ltmain.sh) -> aclocal (AM_* macros) ->
        #        autoheader -> autoconf -> automake (Makefile.in) -> autoconf
        autotools_cmds = (
            "$LIBTOOLIZE --copy --force",
            "$ACLOCAL",
            "$AUTOHEADER -f",
            "$AUTOCONF -f",
            "$AUTOMAKE --foreign --add-missing --copy --force-missing",
            "$AUTOCONF -f",
        )
        with chdir(self, self.source_folder):
            # Use the agg_autotools_env script (saved by generate()) which
            # exports absolute paths for LIBTOOLIZE/AUTOM4TE/SED/AUTOCONF/
            # AUTOMAKE/ACLOCAL. CI workers may not have these on PATH and
            # libtoolize has group-only x perms (file_manager group), so
            # resolving via PATH is unreliable — absolute paths via $VAR
            # from agg_autotools_env are robust.
            self.run(
                " && ".join(autotools_cmds),
                env=["agg_autotools_env"],
            )
        # HMDFS workaround: configure's generated config.status uses
        # `(umask 077 && mktemp -d "./confXXXXXX")` which creates a 700-permission
        # subdir; HMDFS refuses writes inside such dirs.
        # Pre-patch the configure template so the generated config.status uses
        # mkdir with umask 022 (775 perm) instead.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r", encoding="utf-8") as f:
                cfg = f.read()
            # E165: autoreconf-generated configure shebang is #!/bin/bash or
            # #!/bin/sh — neither exists on OHOS. Rewrite to the real paths.
            # Note: autoconf emits "#! /bin/sh" (with a space); handle both.
            cfg = cfg.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
            cfg = cfg.replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
            cfg = cfg.replace("#!/bin/sh", "#!/system/bin/sh")
            cfg = cfg.replace("#! /bin/sh", "#! /system/bin/sh")
            # Also fix SHELL=${CONFIG_SHELL-/bin/sh} fallbacks inside configure
            # (make invokes ${SHELL} which resolves to /bin/sh → exit 127).
            # autoconf emits several nested forms; replace them all.
            cfg = cfg.replace("${CONFIG_SHELL-/bin/sh}", "${CONFIG_SHELL-/system/bin/sh}")
            cfg = cfg.replace("${SHELL-/bin/sh}", "${SHELL-/system/bin/sh}")
            cfg = cfg.replace("${SHELL-${CONFIG_SHELL-/bin/sh}}", "${SHELL-${CONFIG_SHELL-/system/bin/sh}}")
            # Makefile.in templates set `SHELL = /bin/sh` (autoconf's @SHELL@)
            # — catch the literal assignment so make's SHELL doesn't fall back.
            cfg = cfg.replace("SHELL = /bin/sh", "SHELL = /system/bin/sh")
            orig = (
                '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
                '  test -d "$tmp"'
            )
            repl = (
                '  tmp=./conf$$-$RANDOM\n'
                '  (umask 022 && mkdir "$tmp" && chmod 755 "$tmp")'
            )
            cfg = cfg.replace(orig, repl)
            # Also catch the fallback mktemp path
            cfg = cfg.replace(
                '(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
                '(umask 022 && mkdir ./conf$$-$RANDOM && chmod 755 ./conf$$-$RANDOM)',
            )
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(cfg)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["agg"]
        # Headers install to include/agg2/ (upstream convention)
        self.cpp_info.includedirs = ["include"]
        # Conan 2.x: emit CMake config files (aggConfig.cmake + agg::agg
        # target) so test_package's find_package(agg) / agg::agg resolve.
        self.cpp_info.set_property("cmake_file_name", "agg")
        self.cpp_info.set_property("cmake_target_name", "agg::agg")

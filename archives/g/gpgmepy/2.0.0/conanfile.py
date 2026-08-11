#!/usr/bin/env python3
"""Conan recipe — gpgmepy 2.0.0 (GPGME Python bindings, autotools) on HarmonyOS PC (aarch64).

gpgmepy is the Python binding of GPGME (PyPI package name `gpg`). It is built
with autotools + SWIG (generates gpgme_wrap.c from gpgme.i) + setuptools.

OHOS-specific adaptations:
  1. E007 — config.guess/config.sub patched to recognize `linux-ohos`
     (patches/0001, 0002). Native build, no --build/--host.
  2. E011 — configure umask 077 -> 022 for HMDFS temp dirs (patches/0003).
  3. config-overrides: self-contained gpgme-config / gpg-error-config wrapper
     scripts. The packaged gpgme/libgpg-error config scripts and .pc files use
     prefix=/ (wrong absolute paths); the packaged gpgme-config filters out
     its own -I/include and omits its own include dir. gpgrt-config is
     intentionally NOT put on PATH (it hangs under OHOS /bin/sh = mksh);
     a standalone gpg-error-config wrapper replaces it.
  4. setup.py.in patch (patches/0004): os.popen('uname -s').read() crashes on
     HarmonyOS Python 3.12 (returns a binary stream) -> use
     subprocess.check_output(...).decode().
  5. E074 — make -j1 (OHOS SELinux forbids FIFO jobserver).
  6. VPATH build: upstream Makefile `copystamp` does `cp $(srcdir)/f ./` which
     fails on in-tree same-file copies -> configure runs in build_folder.
  7. Tests/ requires a real `gpg` binary (GnuPG runtime, not published on
     OHOS PC) — all upstream tests are blocked (0/28), see notes.md and
     reports/test-report.md.
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GpgmepyConan(ConanFile):
    name = "gpgmepy"
    version = "2.0.0"
    description = "GPGME Python bindings (PyPI package `gpg`)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/gpgme/"
    url = "https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gpgme.git"
    topics = ("gpg", "gpgme", "crypto", "python")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires(
            "gpgme/1.24.0",
            transitive_headers=True,
            transitive_libs=True,
        )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # config-overrides: correct config scripts for the packaged deps       #
    # ------------------------------------------------------------------ #
    def _co_dir(self):
        return os.path.join(self.build_folder, "config-overrides")

    def _create_config_overrides(self):
        gpgme_pkg = self.dependencies["gpgme"].package_folder
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        co = self._co_dir()
        os.makedirs(os.path.join(co, "bin"), exist_ok=True)

        gpgme_inc = os.path.join(gpgme_pkg, "include")
        gpgme_lib = os.path.join(gpgme_pkg, "lib")
        las_inc = os.path.join(las, "include")
        las_lib = os.path.join(las, "lib")
        lgp_inc = os.path.join(lgp, "include")
        lgp_lib = os.path.join(lgp, "lib")

        # gpgme-config wrapper: the packaged gpgme-config filters out
        # -I/include and omits its own include dir; provide full flags here.
        with open(os.path.join(co, "bin", "gpgme-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  --version) echo 1.24.0 ;;\n"
                "  --api-version) echo 1 ;;\n"
                "  --host) echo aarch64-unknown-linux-ohos ;;\n"
                "  --cflags) echo -I{gpgme_inc} -I{las_inc} -I{lgp_inc} ;;\n"
                "  --libs) echo -L{gpgme_lib} -lgpgme -L{las_lib} -lassuan "
                "-L{lgp_lib} -lgpg-error ;;\n"
                "  --print-lang) echo c ;;\n"
                "  *) echo 1.24.0 ;;\n"
                "esac\n".format(gpgme_inc=gpgme_inc, gpgme_lib=gpgme_lib,
                                las_inc=las_inc, las_lib=las_lib,
                                lgp_inc=lgp_inc, lgp_lib=lgp_lib)
            )
        os.chmod(os.path.join(co, "bin", "gpgme-config"), 0o755)

        # gpg-error-config wrapper (gpgrt-config hangs under OHOS /bin/sh=mksh).
        with open(os.path.join(co, "bin", "gpg-error-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  --version) echo 1.55 ;;\n"
                "  --host) echo aarch64-unknown-linux-ohos ;;\n"
                "  --cflags) echo -I{lgp_inc} ;;\n"
                "  --libs) echo -L{lgp_lib} -lgpg-error ;;\n"
                "  --mt) shift; exec \"$0\" \"$@\" ;;\n"
                "  *) echo 1.55 ;;\n"
                "esac\n".format(lgp_inc=lgp_inc, lgp_lib=lgp_lib)
            )
        os.chmod(os.path.join(co, "bin", "gpg-error-config"), 0o755)
        return co

    def _build_env(self, co):
        """Environment for configure/make/install runs (conanbuild env is
        intentionally NOT applied — flags come from the config-overrides)."""
        gpgme_pkg = self.dependencies["gpgme"].package_folder
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        env = Environment()
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("SHELL", "/data/service/hnp/bin/bash")
        env.define("TMPDIR", self.build_folder)
        # Order matters: config-overrides must come FIRST so our gpgme-config /
        # gpg-error-config wrappers win over the packaged config scripts.
        env.prepend_path("PATH", os.path.join(gpgme_pkg, "bin"))
        env.prepend_path("PATH", os.path.join(co, "bin"))
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("CXX", "/data/service/hnp/bin/clang++")
        env.define("CPP", "/data/service/hnp/bin/clang -E")
        env.define(
            "LDFLAGS",
            "-L{} -L{} -L{}".format(
                os.path.join(lgp, "lib"),
                os.path.join(las, "lib"),
                os.path.join(gpgme_pkg, "lib"),
            ),
        )
        return env

    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        co = self._create_config_overrides()
        env = self._build_env(co)
        with env.vars(self).apply():
            # VPATH build: configure from build_folder (upstream `copystamp`
            # fails on in-tree same-file copies).
            self.run(
                "sh {src}/configure --prefix=/ --disable-gpg-test".format(
                    src=shlex.quote(self.source_folder)),
                env=None, cwd=self.build_folder)
            # E074: make -j1 (OHOS SELinux forbids FIFO jobserver).
            self.run("make -j1", env=None, cwd=self.build_folder)

    def package(self):
        co = self._co_dir()
        env = self._build_env(co)
        with env.vars(self).apply():
            self.run(
                "make install DESTDIR={} -j1".format(shlex.quote(self.package_folder)),
                env=None, cwd=self.build_folder)
        # Sanity check: the SWIG extension must be installed.
        pv = "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
        sp = os.path.join(self.package_folder, "lib", pv, "site-packages", "gpg")
        if not os.path.isdir(sp):
            raise Exception("gpg package dir not installed under " + sp)
        ext = [x for x in os.listdir(sp) if x.startswith("_gpgme") and x.endswith(".so")]
        if not ext:
            raise Exception("_gpgme extension not found under " + sp)

    def package_info(self):
        # Python package: no C library/headers exposed to linkers.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        pv = "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", pv, "site-packages"))

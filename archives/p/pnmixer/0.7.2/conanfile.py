#!/usr/bin/env python3
"""Conan recipe for pnmixer 0.7.2 — ALSA volume mixer for the system tray (GTK+3, CMake).

HarmonyOS PC (aarch64) native adaptation.

Upstream facts (verified against the tag archive, 16 .c / 16 .h, single
executable ``bin/pnmixer``)
-------------------------------------------------------------------------
* Build system: **CMake** (``CMakeLists.txt`` + per-directory files).  The
  skill's ``conan-init`` template is autotools-only, so this recipe was
  rewritten for ``CMakeToolchain``/``CMakeDeps``-free pkg-config consumption.
* Dependencies come from ``pkg_check_modules(PNMixer_DEPS REQUIRED ...)`` in
  ``src/CMakeLists.txt``: ``alsa``, ``glib-2.0``, ``x11``, ``gtk+-3.0>=3.12.0``
  and (optionally) ``libnotify``.  ``PkgConfigDeps`` emits exactly those module
  names because the published OHOS recipes set ``pkg_config_name`` accordingly
  (alsa-lib→``alsa``, glib→``glib-2.0``, libx11→``x11``, gtk→``gtk+-3.0``,
  libnotify→``libnotify``); no ``.pc`` aliasing is needed.
* ``cmake_minimum_required(VERSION 3.0)``: the platform's CMake 4.1.2 removed
  compatibility with <3.5, so ``CMAKE_POLICY_VERSION_MINIMUM=3.5`` must be
  injected.  It has to be a **cache** variable (``cache_variables``) — writing
  it into the toolchain file as a normal variable does not reach the policy
  check.
* ``ENABLE_NLS`` is forced **OFF** for two independent, evidence-backed
  reasons (both disclosed in notes.md / PR body):
  1. ``CMakeLists.txt`` does ``FIND_PROGRAM(XGETTEXT_EXECUTABLE xgettext)`` and
     ``MESSAGE(FATAL_ERROR "xgettext not found")``; like the automake precedent
     (cliquer) the clean CI worker has no guaranteed gettext toolchain, so the
     default ``ON`` makes configure fail there while succeeding on a developer
     machine (false green).
  2. With NLS on, ``src/support-intl.h`` includes ``<libintl.h>``; on OHOS that
     header is a stub and the libintl implementation lives in the gettext
     artifact (knowledge entry E660).  Off ⇒ ``#cmakedefine ENABLE_NLS`` stays
     undefined, ``intl_init()`` compiles without any gettext call and the link
     needs no ``-lintl``.
  This matches the repo-wide practice (212 in-tree recipes pass
  ``--disable-nls``/``ENABLE_NLS=OFF``).
* libnotify is **not** required: ``WITH_LIBNOTIFY=OFF``.  The published
  ``libnotify/0.8.3`` artifact cannot be loaded on OHOS at all — its
  ``lib/libnotify.so.4.0.0`` carries a ``.codesign`` section that the loader
  rejects (``dlopen`` → ``Permission denied``), while re-signing the very same
  bytes with ``binary-sign-tool`` makes them load (both readings measured on
  this device).  Any binary linking it therefore dies before ``main()``:
  ``Error loading shared library libnotify.so.4 ... notify_init: symbol not
  found``.  Additionally ``libnotify/0.8.3.1`` adds a hard ``glib/2.88.0.1``
  (``force=True``) conflict against every published gtk3 (``glib/2.84.0.1``)
  whose only resolutions force a meson source rebuild this toolchain cannot do
  (no meson binary and no meson recipe: ``meson: inaccessible or not found`` →
  ``Error 127``).  Turning the upstream-supported option off keeps every
  dependency on its published binary **and** yields a binary that actually
  runs here; desktop notifications would in any case need a freedesktop
  notification daemon on D-Bus, which the OHOS PC environment does not provide.
  See notes.md / README.md for the full before/after evidence.
* The tag archive's ``cmake/scripts/install-git-hook.sh`` runs via
  ``execute_process`` at configure time and only touches ``.git/hooks``; in a
  source export there is no ``.git`` so it is a silent no-op.
* R26 does not apply: the package ships no library, only ``bin/pnmixer`` +
  ``share/`` data, so ``package_type = "application"`` is correct and no
  system-name ``.so`` can leak into ``/lib``.
* R38: the artifact contains an executable ⇒ software-level ``commands.json``
  is provided at ``archives/p/pnmixer/commands.json``.
* R32: ``validate()`` accepts only ``("Linux", "OHOS")``.
* R33: the compiler/toolchain comes from ``CMakeToolchain``/profile conf, never
  from bare ``$CC``/``$CFLAGS``.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class PnmixerConan(ConanFile):
    name = "pnmixer"
    version = "0.7.2"
    description = ("ALSA volume mixer for the system tray (GTK+3 tray icon, "
                   "a fork of OBmixer/AbsVolume)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/nicklan/pnmixer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # ------------------------------------------------------------------ #
    #  metadata / layout                                                  #
    # ------------------------------------------------------------------ #
    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pnmixer supports Linux/OHOS native builds, got %s"
                % self.settings.os)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # No libnotify (WITH_LIBNOTIFY=OFF, see the module docstring): its
        # published shared object is signed in a way the OHOS loader rejects, so
        # linking it would deliver a binary that cannot start, and its recipe
        # family additionally conflicts with gtk's glib/gdk-pixbuf/expat
        # closure.  With libnotify gone this graph is the plain gtk3 closure:
        # every node resolves to a published binary, nothing is rebuilt.
        self.requires("gtk/3.24.43",
                      transitive_headers=True, transitive_libs=True)
        self.requires("alsa-lib/1.2.16.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libx11/1.8.13.1",
                      transitive_headers=True, transitive_libs=True)

    def source(self):
        # conandata.yml carries an explicit filename: the codeload URL ends in
        # the tag name, not in ".tar.gz" (E276/E483).
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    #  generate                                                           #
    # ------------------------------------------------------------------ #
    def generate(self):
        PkgConfigDeps(self).generate()
        build_env = self._build_env()
        build_env.vars(self).save_script("pnmixer_build_env")

        toolchain = CMakeToolchain(self)
        toolchain.user_presets_path = False
        # CMake 4.x dropped compatibility with cmake_minimum_required(<3.5);
        # the value must be a cache variable to reach the policy check.
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.variables["WITH_GTK3"] = "ON"
        toolchain.variables["WITH_LIBNOTIFY"] = "OFF"
        toolchain.variables["ENABLE_NLS"] = "OFF"
        toolchain.generate()

    # ------------------------------------------------------------------ #
    #  build / package                                                    #
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # pkg_check_modules() is driven by the pkg-config *program*, so the
        # generated .pc files must be on PKG_CONFIG_PATH while cmake runs.
        # /tmp is a read-only erofs mount on OHOS (E002), hence the private
        # TMPDIR/TMP/TEMP for cmake and the compiler.
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "bin", "pnmixer"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------ #
    #  helpers                                                            #
    # ------------------------------------------------------------------ #
    def _build_env(self):
        """Environment for configure/build: .pc search path + writable tmp.

        ``PKG_CONFIG_PATH`` must list the PkgConfigDeps generators folder first
        (it mirrors every dependency component as a real ``.pc``) followed by
        the dependency package ``pkgconfig`` folders, so that ``Requires:``
        chains of the generated files resolve as well.
        """
        env = Environment()
        directories = []
        try:
            generators = self.generators_folder
        except Exception:
            generators = None
        if generators and os.path.isdir(generators):
            directories.append(generators)
        for dependency in self.dependencies.values():
            try:
                package_folder = dependency.package_folder
            except Exception:
                continue
            if not package_folder:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                directory = os.path.join(package_folder, sub)
                if os.path.isdir(directory):
                    directories.append(directory)
        seen = set()
        unique = []
        for directory in directories:
            if directory not in seen:
                seen.add(directory)
                unique.append(directory)
        if unique:
            env.define_path("PKG_CONFIG_PATH", os.pathsep.join(unique))

        tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            env.define_path(key, tmpdir)
        return env

    @staticmethod
    def _sign_ohos_elf(path):
        """Sign the packaged executable (OHOS refuses unsigned ELF images).

        Same contract as the merged ``pasystray/0.8.2`` recipe: the signature is
        applied after ``cmake.install()`` and verified through the ``.codesign``
        section count, so a silently unsigned artifact cannot pass.
        """
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        readelf = (shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not os.path.isfile(path):
            raise ConanException("missing packaged executable: %s" % path)
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output,
             "-selfSign", "1"],
            check=True, timeout=120)
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True,
            text=True, timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                "signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

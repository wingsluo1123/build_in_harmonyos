#!/usr/bin/env python3
"""Conan recipe for pasystray 0.8.2 — PulseAudio systray controller (GTK+3, autotools).

HarmonyOS PC (aarch64) native adaptation.

Dependency conflict of platform task 9324 and "option (b)"
----------------------------------------------------------
* pasystray hard-requires ``libpulse-mainloop-glib`` (``configure.ac:51``
  ``PKG_CHECK_MODULES(PULSEAUDIO, [libpulse >= 1.0 libpulse-mainloop-glib >= 1.0])``
  and ``src/pulseaudio.c`` calls ``pa_glib_mainloop_new`` / ``pa_glib_mainloop_get_api``).
  In this registry only ``pulseaudio/17.0.1`` ships that library
  (``pulseaudio/17.0`` is configured with ``glib=disabled``).
* ``pulseaudio/17.0.1`` pins ``glib/2.88.0``, while *every* published gtk3
  (3.24.38 / 3.24.38.1 / 3.24.43) pins ``glib/2.84.0.1`` -> the graph is
  unsatisfiable with the plain recipe.

Option (b) (user-requested): make the gtk3 glib win with a **recipe-level
override** (``self.requires("glib/2.84.0.1", override=True)``) and let
pulseaudio be rebuilt from source against it.  The override travels with this
recipe, so it also applies in CI, where ``--build=missing`` rebuilds
pulseaudio because its ``package_id`` changed.

Source tree notes
-----------------
* The GitHub tag archive ships **no generated autotools files**, so build()
  runs ``autoreconf -fi`` (automake comes from ``tool_requires``; the device
  autoconf 2.72/autoheader are used through the conanbuild environment).
* E007: the automake-shipped ``config.guess`` does not know HarmonyOS; an
  inline, environment-independent patch adds the ``__OHOS__`` LIBC probe and
  the ``*:HarmonyOS:*:*`` case (falling back to the triplet
  ``aarch64-unknown-linux-ohos``).  ``config.sub`` of automake 1.18 already
  lists ``ohos*``/``linux-ohos*``; the ``ohos-linux`` triplet is added when
  missing.
* E011/E114: on the setgid HMDFS volume a 0700 ``config.status`` temp
  directory is unwritable, so ``umask 077`` in the generated ``configure`` is
  lowered to ``umask 022`` (same fix as l3afpad/activity-log/bluefish).
* Optional dependencies are switched off explicitly (avahi, libnotify, X11,
  appindicator) so the dependency surface matches what the registry provides;
  the guarded stubs in ``avahi.c``/``notify.c``/``x11-property.c`` compile
  with ``HAVE_*`` undefined.  ``--disable-statusicon`` is deliberately NOT
  passed: the GTK3 ``GtkStatusIcon`` is the app's actual systray backend.

R32: settings.os is validated against ("Linux", "OHOS").
R38: application package with ``bin/`` -> a software-level ``commands.json``
is provided at ``archives/p/pasystray/commands.json``.
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PasystrayConan(ConanFile):
    name = "pasystray"
    version = "0.8.2"
    description = ("PulseAudio systray controller (GTK+3) — control the "
                   "PulseAudio sound server from a system tray icon")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/christophgysin/pasystray"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # module name expected by configure.ac -> conan component .pc basenames
    # PkgConfigDeps names component .pc files "<dep>-<component>", so the
    # upstream module names (libpulse, libpulse-mainloop-glib, ...) do not
    # exist verbatim and must be aliased.
    _PC_ALIASES = {
        "libpulse": ("pulseaudio-pulse", "pulseaudio"),
        "libpulse-mainloop-glib": ("pulseaudio-pulse-mainloop-glib",),
        "libpulse-simple": ("pulseaudio-pulse-simple",),
        "gdk-3.0": ("gtk+-3.0",),
        "gio-unix-2.0": ("gio-2.0",),
    }

    # ------------------------------------------------------------------ #
    #  metadata / layout                                                  #
    # ------------------------------------------------------------------ #
    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pasystray supports Linux/OHOS native builds, got %s"
                % self.settings.os)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    #  requirements — option (b)                                          #
    # ------------------------------------------------------------------ #
    def requirements(self):
        # Option (b): the gtk3-pinned glib must win over pulseaudio's
        # glib/2.88.0.  A recipe-level override is honoured both locally and
        # by the platform CI (it is part of this recipe), whereas a profile
        # [replace_requires] would not travel with the PR.
        self.requires("glib/2.84.0.1", override=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("pulseaudio/17.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The device has autoconf/autoheader/autoreconf but no aclocal/automake.
        self.tool_requires("automake/1.18")

    # ------------------------------------------------------------------ #
    #  generate                                                           #
    # ------------------------------------------------------------------ #
    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_pc_aliases()

        VirtualBuildEnv(self).generate()
        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()

        # pkg.m4 (PKG_CHECK_MODULES) lives in the pkg-config aclocal dir; the
        # automake package ships the AM_* macros.  ACLOCAL_PATH must cover both.
        for directory in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            environment.append_path("ACLOCAL_PATH", directory)
        automake_root = self.dependencies.build["automake"].package_folder
        for name in ("share/aclocal", "share/aclocal-1.18"):
            directory = os.path.join(automake_root, name)
            if os.path.isdir(directory):
                environment.append_path("ACLOCAL_PATH", directory)

        # OHOS /tmp is read-only; keep autoreconf/configure temporaries inside
        # the isolated build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)

        toolchain.configure_args.extend([
            "--with-gtk=3",
            "--disable-avahi",
            "--disable-notify",
            "--disable-x11",
            "--disable-appindicator",
        ])
        toolchain.generate(env=environment)

    def _write_pc_aliases(self):
        """Alias upstream pkg-config module names to the generated .pc files.

        ``configure.ac`` asks for ``libpulse``/``libpulse-mainloop-glib`` (and
        GTK pulls ``gdk-3.0``/``gio-unix-2.0`` through its Requires), but
        PkgConfigDeps writes component files named ``<dep>-<component>``.  Each
        alias forwards to the real file and copies its Version so the
        ``>= 1.0`` constraints keep working.
        """
        gen = self.generators_folder
        for alias, targets in sorted(self._PC_ALIASES.items()):
            alias_pc = os.path.join(gen, alias + ".pc")
            if os.path.isfile(alias_pc):
                continue
            for target in targets:
                target_pc = os.path.join(gen, target + ".pc")
                if not os.path.isfile(target_pc):
                    continue
                version = "1.0"
                match = re.search(r"^Version:\s*(.+)$", load(self, target_pc),
                                  re.MULTILINE)
                if match:
                    version = match.group(1).strip()
                save(self, alias_pc,
                     "Name: %s\nDescription: %s (conan alias for %s)\n"
                     "Version: %s\nRequires: %s\n"
                     % (alias, alias, target, version, target))
                self.output.info("pkg-config alias %s.pc -> %s.pc" % (alias, target))
                break
            else:
                self.output.warn("no generator .pc found for alias %s" % alias)

    # ------------------------------------------------------------------ #
    #  build                                                              #
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_autotools_ohos()
        self._bootstrap_configure()
        if str(self.settings.os) == "OHOS":
            self._patch_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        # -j1: the HMDFS jobserver fifo raises EPERM (E074).
        # LIBS="..." must stay ONE shell word: an unquoted assignment makes make
        # treat the -L<dir> part as an unknown option.  See _intl_link_flags().
        autotools.make(args=["-j1", 'LIBS="%s"' % self._intl_link_flags()])

    def _intl_link_flags(self):
        """``-lintl`` + glib's libdir for the final link only.

        GLib's gi18n.h maps gettext() to the ``g_libintl_*`` aliases, which are
        exported by the libintl shipped inside the glib package
        (``<glib>/lib/libintl.so``); glib's generated .pc does not list
        ``-lintl``, so pasystray's link fails with undefined
        ``g_libintl_gettext`` (systray.c) — the same defect l3afpad worked
        around.  It must NOT be added to configure's LIBS: an unconditional
        ``-lintl`` makes AC_PROG_CC's conftest fail to link
        ("C compiler cannot create executables").
        """
        flags = []
        if "glib" in self.dependencies:
            for libdir in self.dependencies["glib"].cpp_info.libdirs:
                flags.append("-L%s" % libdir)
        flags.append("-lintl")
        return " ".join(flags)

    def _bootstrap_configure(self):
        """Run ``autoreconf -fi`` (the tag archive ships no configure)."""
        if os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("configure already present, skipping autoreconf")
            return
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")

    def _patch_autotools_ohos(self):
        """E007: teach the bundled config.guess/config.sub about HarmonyOS.

        Implemented inline (no dependency on OHC_SKILL_ROOT) so the platform
        CI produces the same result as a local run.
        """
        for base in (self.source_folder,
                     os.path.join(self.source_folder, "build-aux")):
            guess = os.path.join(base, "config.guess")
            sub = os.path.join(base, "config.sub")
            if os.path.isfile(guess):
                text = load(self, guess)
                if "__OHOS__" not in text:
                    text = text.replace(
                        "\tLIBC=android\n",
                        "\tLIBC=android\n"
                        "\t#elif defined(__OHOS__)\n"
                        "\tLIBC=ohos\n", 1)
                    if "LIBC=ohos" not in text:
                        self.output.warn("config.guess: LIBC=android marker not found")
                if "HarmonyOS" not in text:
                    block = (
                        "    *:HarmonyOS:*:*)\n"
                        "\tcase \"$UNAME_MACHINE\" in\n"
                        "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                        "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                        "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                        "\t    i?86)         MACHINE=i686 ;;\n"
                        "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                        "\tesac\n"
                        "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                        "\t;;\n\n")
                    if "    *:NetBSD:*:*)" in text:
                        text = text.replace("    *:NetBSD:*:*)", block + "    *:NetBSD:*:*)", 1)
                    else:
                        self.output.warn("config.guess: NetBSD anchor not found")
                save(self, guess, text)
                self.output.info("config.guess: HarmonyOS support ensured")
            if os.path.isfile(sub):
                text = load(self, sub)
                if "ohos-linux)" not in text:
                    marker = ("\t\t\tandroid-linux)\n"
                              "\t\t\t\tbasic_machine=$field1-unknown\n"
                              "\t\t\t\tbasic_os=linux-android\n"
                              "\t\t\t\t;;\n")
                    addition = ("\t\t\tohos-linux)\n"
                                "\t\t\t\tbasic_machine=$field1-unknown\n"
                                "\t\t\t\tbasic_os=linux-ohos\n"
                                "\t\t\t\t;;\n")
                    if marker in text:
                        text = text.replace(marker, marker + addition, 1)
                        save(self, sub, text)
                        self.output.info("config.sub: ohos-linux triplet added")
                    else:
                        self.output.warn("config.sub: android-linux anchor not found")

    def _patch_configure_umask(self):
        """E011/E114: HMDFS cannot use the 0700 config.status temp dir."""
        path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(path):
            raise ConanException("configure not found after autoreconf")
        text = load(self, path)
        if "umask 077" not in text:
            self.output.info("configure has no umask 077 (nothing to patch)")
            return
        new, count = re.subn(r"umask 077", "umask 022", text)
        save(self, path, new)
        self.output.info("patched %d umask 077 occurrence(s) in configure" % count)

    # ------------------------------------------------------------------ #
    #  package                                                            #
    # ------------------------------------------------------------------ #
    def package(self):
        with self._runtime_env().vars(self).apply():
            Autotools(self).install(args=["-j1"])
        # The GTK glade file and the desktop/icon data are installed by
        # `make install` under <prefix>/share — keep them (bin/ + share/).
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "pasystray"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------ #
    #  helpers                                                            #
    # ------------------------------------------------------------------ #
    def _runtime_env(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            for dependency in self.dependencies.host.values():
                for libdir in dependency.cpp_info.libdirs:
                    directory = libdir
                    if not os.path.isabs(directory):
                        directory = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(directory):
                        environment.prepend_path("LD_LIBRARY_PATH", directory)
        return environment

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException("missing packaged executable: %s" % path)
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=120)
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True,
            text=True, timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                "signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

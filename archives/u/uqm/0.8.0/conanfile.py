#!/usr/bin/env python3
"""Conan recipe — uqm 0.8.0 (The Ur-Quan Masters, custom ./build.sh system).

The Ur-Quan Masters is the open-source port of the 1992 DOS game
Star Control II, built on SDL2 + libpng + Ogg Vorbis + zlib.

Upstream ships its own non-autotools build system
(``./build.sh uqm config`` / ``./build.sh uqm install``) whose configure step is
an interactive text menu.  For unattended builds this recipe synthesizes the
documented ``config.state`` file and drives the ``reprocess_config`` target
instead — upstream INSTALL states: "for unattended or scripted installs,
consult the config.state file ... builds will then skip the configure step".

OHOS adaptations (all in patches/, see notes.md):
  * upstream hard-codes the compiler driver name ``gcc``; a private gcc -> clang
    wrapper is generated below and prepended to PATH so the Conan toolchain is
    used for every compile/link invocation.
  * upstream puts configure probe files in /tmp, which is read-only on OHOS;
    patches/0001 switches it to ``${TMPDIR:-/tmp}``.
  * fd_set / FD_SETSIZE / select() are not reachable through <sys/types.h> on
    musl; patches/0002 adds the <sys/select.h> include.

Upstream build/install layout (preserved):
  bin/uqm            launcher wrapper (adds --contentdir)
  lib/uqm/uqm        the game binary itself
  share/uqm/content  bundled content index
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UqmConan(ConanFile):
    name = "uqm"
    version = "0.8.0"
    description = ("The Ur-Quan Masters 0.8.0 — open-source port of Star "
                   "Control II (SDL2 based)")
    license = "GPL-2.0-or-later"
    homepage = "http://sc2.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Generates the .pc files that UQM's own configure probes (vorbisfile,
    # zlib, libpng) consume through PKG_CONFIG_PATH.
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL2 is the graphics/input/sound backend. libpng/vorbisfile/zlib are
        # required by the configure step (all four are probed by UQM itself).
        self.requires("sdl2/2.32.10")
        self.requires("libpng/1.6.58.3")
        self.requires("libvorbis/1.3.7")
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        includes, ldflags, bindirs = self._dep_flags()

        # UQM's build system invokes the bare name `gcc`; expose a private
        # wrapper that forwards to the Conan-provided compiler.  R49: the
        # wrapper lives under build_folder, never in a shared system prefix.
        shim_dir = os.path.join(self.build_folder, "toolchain-shim")
        os.makedirs(shim_dir, exist_ok=True)
        gcc_shim = os.path.join(shim_dir, "gcc")
        with open(gcc_shim, "w", encoding="utf-8") as handle:
            handle.write(f'#!{self._shell()}\nexec {self._compiler()} "$@"\n')
        os.chmod(gcc_shim, 0o755)

        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        with open(os.path.join(self.source_folder, "config.state"),
                  "w", encoding="utf-8") as handle:
            handle.write(self._config_state())

        env = Environment()
        for path in reversed(bindirs + [shim_dir]):
            env.prepend_path("PATH", path)
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.define("CFLAGS", " ".join(includes))
        env.define("CXXFLAGS", " ".join(includes))
        env.define("LDFLAGS", " ".join(ldflags))
        env.define("TMPDIR", tmp_dir)
        env.define("CONFIG_SHELL", self._shell())
        env.define("SHELL", self._shell())

        with env.vars(self, scope="build").apply():
            # `reprocess_config` re-reads config.state and skips the menu.
            self.run(f"{self._shell()} ./build.sh uqm reprocess_config",
                     cwd=self.source_folder)
            # R9: deterministic single-job build.
            self.run(f"{self._shell()} ./build.sh uqm -j1", cwd=self.source_folder)
            self.run(f"{self._shell()} ./build.sh uqm install",
                     cwd=self.source_folder)

    def package(self):
        # `build.sh uqm install` writes directly into the configured prefix,
        # which is self.package_folder (bin/ + lib/ + share/).  Assert the
        # expected layout so a silently failed install cannot yield an empty
        # package.
        launcher = os.path.join(self.package_folder, "bin", "uqm")
        binary = os.path.join(self.package_folder, "lib", "uqm", "uqm")
        content = os.path.join(self.package_folder, "share", "uqm", "content")
        for artifact in (launcher, binary):
            if not os.path.isfile(artifact):
                raise ConanException(
                    f"uqm install did not produce {artifact} — upstream "
                    "./build.sh uqm install failed silently")
        if not os.path.isdir(content):
            raise ConanException(
                f"uqm install did not produce the content directory "
                f"{content} — the launcher's --contentdir would be dangling")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── helpers ────────────────────────────────────────────────────────────

    def _shell(self):
        """OHOS has no usable /bin/sh for ELF execution; prefer CONFIG_SHELL."""
        for candidate in (os.environ.get("CONFIG_SHELL", ""),
                          "/data/service/hnp/bin/bash", "/bin/bash", "/bin/sh"):
            if candidate and os.path.exists(candidate):
                return candidate
        return "/bin/sh"

    def _compiler(self):
        # R33: the compiler comes from Conan conf, never from bare shell vars.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("c", "clang")

    def _dep_flags(self):
        """Include dirs, library dirs (with rpath) and bindirs of all deps."""
        includes, ldflags, bindirs = [], [], []
        for dep in self.dependencies.values():
            cpp_info = dep.cpp_info.aggregated_components()
            for inc in cpp_info.includedirs:
                includes.append(f"-I{inc}")
            for libdir in cpp_info.libdirs:
                ldflags.append(f"-L{libdir}")
                # Non-system shared deps (libpng/libogg/libvorbis) live in the
                # Conan cache; an rpath keeps the installed binary runnable
                # without an external LD_LIBRARY_PATH.
                ldflags.append(f"-Wl,-rpath,{libdir}")
            bindirs.extend(cpp_info.bindirs)
        return includes, ldflags, bindirs

    def _config_state(self):
        """Synthesize UQM's documented non-interactive config.state."""
        entries = {
            "CHOICE_debug_VALUE": "nodebug",
            "CHOICE_graphics_VALUE": "sdl2",
            "CHOICE_sound_VALUE": "mixsdl",
            "CHOICE_mikmod_VALUE": "internal",
            "CHOICE_ovcodec_VALUE": "standard",
            "CHOICE_netplay_VALUE": "full",
            "CHOICE_joystick_VALUE": "enabled",
            "CHOICE_ioformat_VALUE": "stdio_zip",
            "CHOICE_accel_VALUE": "asm",
            "CHOICE_threadlib_VALUE": "sdl",
            "INPUT_install_prefix_VALUE": self.package_folder,
            "INPUT_install_bindir_VALUE": "$prefix/bin",
            "INPUT_install_libdir_VALUE": "$prefix/lib",
            "INPUT_install_sharedir_VALUE": "$prefix/share",
        }
        return "".join(f"{key}='{value}'\n" for key, value in entries.items())

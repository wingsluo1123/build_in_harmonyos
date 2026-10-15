#!/usr/bin/env python3
"""Conan recipe — xwax 1.10 (open-source digital vinyl system for DJs).

xwax is a single-binary DJ application: it reads timecode-vinyl signals from
a sound card, decodes them, and plays the corresponding audio tracks. The
upstream build system is a hand-written POSIX Makefile plus a small
`configure` shim that only writes a `.config` fragment.

OHOS adaptation notes (evidence trail in notes.md):
  * Native build/host on OHOS/aarch64 — the worker *is* the target. No
    cross-compilation and no --host/--build/--target is passed to configure
    (SKILL iron rule #0).
  * interface.c / xwax.c / tests/ttf.o need the SDL2 headers, which the
    Makefile obtains by shelling out to `sdl2-config`. The sdl2 package's
    bin/ directory is therefore put on PATH during generate().
  * The Makefile only understands $(SDL_LIBS)/$(ALSA_LIBS); the complete
    static transitive link line (sdl2, sdl2_ttf, freetype, alsa-lib and
    their own dependencies) comes from the AutotoolsDeps `$LIBS` variable,
    which is forwarded to SDL_LIBS on the make command line.
  * VERSION is normally produced by `./mkversion` from `git describe`; the
    release tarball ships no .git, so VERSION=1.10 is passed explicitly.
  * Upstream has *no* `make check` target: `make` builds eight stand-alone
    manual test programs under tests/ (R51). The headless, argument-free
    ones are executed here; the ones that need a font/display, an audio
    device or pathname arguments are documented in test_package/MANIFEST.yml.
  * `install` (coreutils) is not present on OHOS, so package() copies the
    build outputs instead of running `make install`.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (get, copy, rename, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain


class XwaxConan(ConanFile):
    name = "xwax"
    version = "1.10"
    description = "Open-source digital vinyl system (DVS) for DJs"
    license = "GPL-3.0-or-later"
    homepage = "https://www.xwax.co.uk/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-verified against ohpcd (sdl2 2.30.10, sdl2_ttf 2.24.0,
        # alsa-lib 1.2.16.1 are all published).
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_ttf/2.24.0")
        self.requires("alsa-lib/1.2.16.1")

    def validate(self):
        # R32: OHOS/Linux only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xwax is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        # In-source Makefile build: objects and the generated .config live
        # next to the Makefile, so source and build folders coincide.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler/flags come from the Conan toolchain, never from bare
        # shell ${CC}/${CFLAGS}.
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        env = Environment()
        sdl2_bin = os.path.join(self.dependencies["sdl2"].package_folder, "bin")
        if os.path.isdir(sdl2_bin):
            env.prepend_path("PATH", sdl2_bin)
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_xwax")

    def build(self):
        apply_conandata_patches(self)
        shell = os.environ.get("CONFIG_SHELL", "sh")
        # Hand-written configure shim: only writes .config (PREFIX/ALSA).
        # `--prefix` takes a *separate* argument (this is not autoconf);
        # prefix=/ makes the compiled-in EXECDIR /libexec, matching an
        # upstream `make PREFIX=/` install. No --host/--build/--target.
        self.run(f"{shell} ./configure --prefix / --enable-alsa")
        # `$LIBS` is the ordered static link line from AutotoolsDeps; the
        # Makefile routes it through $(SDL_LIBS). R9: keep -j1.
        self.run('make -j1 VERSION=1.10 '
                 'SDL_CFLAGS="$(sdl2-config --cflags)" SDL_LIBS="$LIBS"')

        # ── Upstream tests (R51) ──
        # `make` built the tests/ programs; run the headless, argument-free
        # ones. The remaining tests need a font, a display, an audio device
        # or pathname arguments and are listed as not-run in MANIFEST.yml.
        for test in ("tests/cues", "tests/observer", "tests/status",
                     "tests/timecoder"):
            self.run(f"{test} < /dev/null")
        if os.path.isfile("/usr/bin/find"):
            self.run("tests/external < /dev/null")

    def package(self):
        copy(self, "xwax", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        libexec = os.path.join(self.package_folder, "libexec")
        copy(self, "scan", src=self.source_folder, dst=libexec, keep_path=False)
        copy(self, "import", src=self.source_folder, dst=libexec, keep_path=False)
        # install the helpers under the names xwax expects on its defaults
        rename(self, os.path.join(libexec, "scan"),
               os.path.join(libexec, "xwax-scan"))
        rename(self, os.path.join(libexec, "import"),
               os.path.join(libexec, "xwax-import"))
        copy(self, "xwax.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

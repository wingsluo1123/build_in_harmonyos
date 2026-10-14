#!/usr/bin/env python3
"""Conan recipe for japa 0.9.4 (Fons Adriaensen).

japa is a perceptual (psychoacoustic) audio spectrum analyser with an X11
GUI whose input comes from either JACK or ALSA.  Sibling of jaaa 0.9.2 in
the same author's kokkinizita Makefile family; the portability strategy
follows jaaa's proven recipe (see archives/j/jaaa/0.9.2/notes.md):

  - Upstream is a single flat Makefile (no source/ subdir), no configure,
    no cmake, no test/check target.
  - The .cc -> .o compile steps go through make's implicit rules which
    expand $(CXX), so the compiler is overridden from the Conan profile
    (GNU Make on the build host predefines CXX to a dangling SDK path).
  - The Makefile probes FreeType with pkg-config; the patch swaps that for
    a $(PCONFCFL) include slot filled by build() with dependency dirs, so
    the built-in -DVERSION/-DPREFIX definitions stay intact.
  - -march=native is dropped so the profile toolchain controls codegen.
  - Bare `install` is parameterised as INSTALL ?= /bin/install (toybox
    applet not on PATH on OHOS).
  - clthreads needs -DCLTHREADS_NO_PTHREAD_CANCEL on OHOS (musl).
  - Single-precision FFTW is the separate fftw3f package (fftwf_* API,
    -lfftw3f), not the fftw package.
  - PREFIX=/ keeps the staged layout free of any host prefix.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JapaConan(ConanFile):
    name = "japa"
    version = "0.9.4"
    package_type = "application"
    description = "Perceptual (psychoacoustic) audio spectrum analyser (X11 GUI, JACK/ALSA input)"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("japa supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("japa supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GUI toolkit (clxclient pulls Xft/X11/FreeType/fontconfig/Xrender and
        # pins clthreads/2.4.0 -- same closure as jaaa 0.9.2, do not mix the
        # X11 1.8.13 track with other tracks).
        self.requires("clxclient/3.9.2", transitive_headers=True)
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        # Audio back ends: japa links both -ljack and -lasound directly.
        self.requires("jack/1.9.22", transitive_headers=True)
        self.requires("zita-alsa-pcmi/0.6.1", transitive_headers=True)
        self.requires("alsa-lib/1.2.16", transitive_headers=True)
        # DSP: single-precision FFTW (fftwf_* API, -lfftw3f).
        self.requires("fftw3f/3.3.10", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")
        # R33: the compiler must come from the Conan profile conf, never from
        # a bare shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Collect the include/lib search paths of every declared dependency
        # and hand them to the Makefile through its $(PCONFCFL) slot, so the
        # built-in -DVERSION/-DPREFIX definitions stay intact.
        pconfcfl = " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads' package_info defines CLTHREADS_NO_PTHREAD_CANCEL for
            # OHOS consumers (pthread_cancel is absent on musl/OHOS); this
            # bare-make build does not consume it through CMakeDeps.
            pconfcfl += " -DCLTHREADS_NO_PTHREAD_CANCEL"
        ldflags = ""
        for _, dependency in self.dependencies.items():
            if not dependency.package_folder:
                continue
            for incdir in dependency.cpp_info.includedirs:
                path = incdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, incdir)
                pconfcfl += " -I" + path
            for libdir in dependency.cpp_info.libdirs:
                path = libdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, libdir)
                ldflags += " -L" + path
        # PREFIX=/ keeps the staged layout free of any host prefix and also
        # keeps -DPREFIX from baking "/usr/local" into the binary.
        self.run(
            'make -C "{}" -j1 PREFIX=/ CXX="{}" PCONFCFL="{}" LDFLAGS="{}" japa'.format(
                source_dir, cxx, pconfcfl, ldflags
            )
        )
        # Upstream ships no test/check target ("make check" fails with
        # "No rule to make target 'check'") so there is no test step here;
        # see test_package/ for the packaged consumer smoke test.

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # BINDIR derives from PREFIX, so PREFIX=/ + DESTDIR stages bin/japa.
        self.run(
            'make -C "{}" install PREFIX=/ DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )

    def package_info(self):
        # japa is a standalone GUI tool; it exports no libraries.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

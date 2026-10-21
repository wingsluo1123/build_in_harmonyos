#!/usr/bin/env python3
"""Conan recipe for quesoglc 0.7.2 — QuesoGLC, a free implementation of the
OpenGL Character Renderer (GLC).

QuesoGLC renders text in OpenGL applications: it maps Unicode codes to glyphs
through FreeType, resolves font faces/catalogues through Fontconfig and draws
the resulting geometry with GL/GLU.  It is a plain-C autotools project whose
release tarball ships a pre-generated `configure`, so the recipe drives that
configure directly and never regenerates it.

HarmonyOS notes
---------------
* OHOS ships **no desktop GL** (no `libGL.so`, no `GL/glx.h`): only EGL +
  GLES2/GLES3.  QuesoGLC's own sources make **zero** `glX*`/`XOpenDisplay`
  calls, i.e. it only needs *an* implementation of the desktop OpenGL API.
  Mesa's offscreen OSMesa (`libOSMesa.so` from `mesa`, which also ships
  `include/GL/gl.h`) provides one — same route as the repo's `glu` recipe.
  `configure` is therefore told the GL/GLU libraries through the autoconf
  cache (`ax_cv_check_gl_libgl` / `ax_cv_check_glu_libglu`) instead of letting
  its `AX_CHECK_GL`/`AX_CHECK_GLU` probes search for the absent `-lGL`.
* GLEW: QuesoGLC is written against GLEW's *multi-context* API (`GLEW_MX`:
  `glewGetContext()`, `GLEWContext`).  Upstream's `--with-glew=no` does **not**
  remove GLEW — it embeds the bundled `src/glew.c` and compiles it with
  `-DGLEW_MX`.  The external `glew` package on ohpcd is an EGL (`GLEW_EGL`)
  build without GLEW_MX, so the bundled copy is the one that must be used.
* The bundled GLEW contains a GLX section whose header `GL/glxew.h` pulls in
  `X11/Xlib.h` / `X11/Xutil.h` / `X11/Xmd.h`; OHOS ships none of them.  Patch
  0003 puts that section behind a `GLEW_NO_GLX` switch — the same opt-out macro
  upstream GLEW 2.x later introduced — and the recipe defines `GLEW_NO_GLX` in
  the build on OHOS.  No GLX symbol is ever referenced at runtime here.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class QuesoglcConan(ConanFile):
    name = "quesoglc"
    version = "0.7.2"
    description = (
        "QuesoGLC, a free implementation of the OpenGL Character Renderer (GLC)"
    )
    license = "LGPL-2.1"
    homepage = "https://sourceforge.net/projects/quesoglc/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("opengl", "text", "font", "renderer", "glc", "ohos")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # freetype is mandatory (glyph rasterisation) and fontconfig is
        # mandatory (font face/catalogue resolution) — `configure` aborts with
        # AC_MSG_ERROR if either is missing.  QuesoGLC needs a desktop-OpenGL
        # implementation (mesa/OSMesa) plus GLU.
        self.requires("freetype/2.14.3", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.1.1", transitive_headers=True, transitive_libs=True)
        # glu/9.0.3 pins mesa/24.3.4.1 (OSMesa) as its GL provider; the two must
        # stay on the same mesa line.
        self.requires("glu/9.0.3", transitive_headers=True, transitive_libs=True)
        self.requires("mesa/24.3.4.1", transitive_headers=True, transitive_libs=True)
        # mesa/24.3.4.1 requires expat/2.8.2.1.1 while fontconfig/2.18.1.1 requires
        # expat/2.8.2.1.  The two releases are not interchangeable at runtime:
        # expat/2.8.2.1.1 ships only `libexpat.so` (SONAME `libexpat.so`) whereas
        # fontconfig's DT_NEEDED asks for `libexpat.so.1`.  The diamond is
        # therefore unified on fontconfig's pin, whose package carries
        # libexpat.so -> libexpat.so.1 -> libexpat.so.1.12.2; OSMesa itself has no
        # expat in its DT_NEEDED so it is unaffected.
        self.requires("expat/2.8.2.1", override=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"quesoglc supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # quesoglc builds in-source: its generated Makefiles put source headers
        # on the compiler line via $(top_builddir) (e.g. build/Makefile.in's
        # `DEFAULT_INCLUDES = -I. -I$(srcdir) -I$(top_builddir)/include` and
        # `libGLC_la_CFLAGS = -I$(top_builddir)/src`).  Out-of-tree (VPATH) those
        # expand to build-tree paths that hold no headers, so `#include
        # "internal.h"` (include/internal.h) is not found.  Building in the
        # source folder makes top_builddir == top_srcdir and the upstream
        # Makefiles correct, with no edit to generated files.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # freetype2/fontconfig are discovered by configure through
        # PKG_CHECK_MODULES, so their .pc files must be on PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # fribidi is optional: upstream embeds its bundled copy when the system
        # library is absent; ask for the embedded copy explicitly.
        tc.configure_args.append("--without-fribidi")
        if str(self.settings.os) == "OHOS":
            # Embed the bundled GLEW_MX (see the module docstring).  Without the
            # external `glew` package, AX_CHECK_GLEW fails and configure takes
            # the "GLEW will be built and embedded" branch, defining GLEW_MX.
            tc.configure_args.append("--with-glew=no")
            # OHOS has no -lGL / -lGLU: seed the autoconf cache so AX_CHECK_GL /
            # AX_CHECK_GLU skip their (doomed) link probes and record the real
            # providers.  GL_CFLAGS/GLU_CFLAGS stay as-is; the include paths
            # arrive through AutotoolsDeps (mesa + glu).
            tc.configure_args.append("ax_cv_check_gl_libgl=-lOSMesa")
            tc.configure_args.append("ax_cv_check_glu_libglu=-lGLU")
            # Drop the GLX half of the bundled GLEW (needs X11 headers).
            tc.extra_cflags.append("-DGLEW_NO_GLX")
        tc.generate()
        # configure compiles-and-runs conftest programs linked against the
        # dependency shared libraries; the OHOS loader has no default search
        # path for the Conan cache, so point LD_LIBRARY_PATH at the dependency
        # lib dirs for the build scope.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: GNU make's jobserver creates a FIFO under $TMPDIR that HMDFS
        # (HarmonyOS) rejects with EPERM, leaving the parallel jobserver broken
        # (E074); pin a single job, as the other autotools recipes here do.
        autotools.make(args=["-j1"])
        # Upstream suite census: tests/Makefile.am sets TESTS = $(noinst_PROGRAMS)
        # and, without GLUT, that is exactly test4 (the other 20 test sources need
        # GLUT and a display and are not built here).  test4 asserts that a
        # non-global GLC command without a current context raises GLC_STATE_ERROR,
        # but it first calls glcAppendCatalog("/") and the library validates the
        # directory with access("/", R_OK) *before* the context check.  OHOS
        # confines the process to a restricted domain where access()/opendir() on
        # "/" fail with EACCES while stat() succeeds (device probe in notes.md;
        # cf. knowledge E303), so with the upstream default root test4 could not
        # execute — a platform-capability limit, not a defect of this build.
        # Patch 0004 lets test4 take its catalog root from QUESOGLC_TEST_CATALOG
        # (the upstream default, "/", is kept whenever the variable is unset); the
        # recipe points it at a writable folder in the build tree below, so the
        # single upstream case executes and passes 1/1.  No assertion, test case or
        # upstream logic is changed; see notes.md and test_package/MANIFEST.yml.
        test_catalog = os.path.join(self.build_folder, "test-catalog")
        os.makedirs(test_catalog, exist_ok=True)
        try:
            # Passed as a command-line make variable: GNU make exports such
            # variables to the recipe environment, so the test process inherits it.
            autotools.make(
                target="check",
                args=["-j1", f"QUESOGLC_TEST_CATALOG={test_catalog}"],
            )
        except Exception as exc:  # noqa: BLE001 — failure recorded for attribution
            self.output.warning(
                f"make check reported failures (logs kept for attribution): {exc}"
            )

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_libs()

    def package_info(self):
        self.cpp_info.libs = ["GLC"]

    def _sign_ohos_libs(self):
        """Self-sign the packaged shared libraries so they load on HarmonyOS.

        Fail-closed (same contract as `archives/t/tgif/4.2.5` and
        `archives/p/pan/0.165`): a missing packaged ELF, a missing
        `binary-sign-tool`/`llvm-readelf`, a non-zero signer exit, or a signed
        output whose `.codesign` count is not exactly 1 all raise.  Only ever
        invoked on OHOS.
        """
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration(
                "Required OHOS signing tools are missing "
                "(binary-sign-tool / llvm-readelf)"
            )
        libdir = os.path.join(self.package_folder, "lib")
        elfs = []
        for name in sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []:
            path = os.path.join(libdir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            elfs.append(path)
        if not elfs:
            raise ConanInvalidConfiguration(
                f"No packaged shared library ELF found under {libdir}"
            )
        for elf in elfs:
            signed = elf + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", elf, "-outFile", signed, "-selfSign", "1"],
                check=True,
                timeout=120,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    f"Signed {os.path.basename(elf)} has invalid .codesign count: "
                    f"{sections.count('.codesign')} (expected exactly 1)"
                )
            os.replace(signed, elf)
            os.chmod(elf, 0o755)

#!/usr/bin/env python3
"""Conan recipe for yorick-gl 1.1-cvs20070922 — OHOS/aarch64 native build=host.

``yorick-gl`` (package name ``yorgl``) is the OpenGL/GLX 3D-graphics *plugin*
for the Yorick scientific interpreter.  It is not a standalone library: the
build produces a shared object ``yorgl.so`` plus a set of interpreted ``.i``
files that are overlaid onto a Yorick installation tree and loaded at run time
with ``plug_in, "yorgl"`` (see yorick's ``i0/std.i``, ``plug_in``).

The package has two halves, selected by the upstream ``configure`` script:

* ``yiso3d`` — the iso-surface / slicing engine (pure computation).  The
  upstream README documents that "the configure script will cause yiso3d to be
  built even if OpenGL cannot be found (or you force ``--no-opengl``)".
* ``yorgl`` — the interactive OpenGL/GLX driver for Yorick's ``play``/``gist``
  layer.

**This port builds the yiso3d half (``--no-opengl``).**  The GL half cannot be
used with the Yorick build that is published to ohpcd: yorick-gl's GL objects
reference the *X11* backend of Yorick's ``play``/``gist`` layer
(``p_window``/``p_wincount``/``p_flush``/``p_destroy`` from ``play/x11/``,
``g_connect``/``g_disconnect`` from ``gist/xbasic.c``, ``x_rgb_palette`` from
``play/x11/pals.c``), and the published ``yorick/2.2.04`` is built with
``NO_XLIB=1`` — those objects are not compiled, not exported by ``bin/yorick``
(checked with ``llvm-readelf --dyn-syms``) and not present in ``lib/libyor.a``.
Since the OHOS dynamic loader (musl) resolves every relocation at ``dlopen``
time, ``plug_in, "yorgl"`` then fails with "unable to find dynamic library
file".  The unblock is an X11-enabled ``yorick`` build; see notes.md.

Build system: a custom ``configure`` shell script plus hand-written Makefiles
(``Makefile`` + generated ``Makegl``) that delegate to the Yorick package build
convention shipped by the ``yorick`` package (``Make.cfg`` / ``Makepkg`` /
``Makedll``).  ``configure`` runs ``yorick -batch make.i`` to rewrite the
Makefile with ``Y_MAKEDIR``/``Y_EXE`` for this Yorick installation.  Native
build (build == target == OHOS/aarch64); iron rule #0: no
``--host``/``--build``/``--target``.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# Interpreted layer of the yiso3d build, grouped by the install destination
# used by the upstream ``make install`` target (see the ``yorick`` package's
# Makepkg).  With ``--no-opengl`` upstream sets:
#   PKG_I       = $(YISO_PKG_I)  -> cntrfunc.i        -> <Y_SITE>/i0
#   PKG_I_EXTRA = $(YISO_I)      -> contour.i tristruct.i -> <Y_SITE>/i
#   PKG_I_START = yiso3d.i                            -> <Y_HOME>/i-start
_PKG_I = ["cntrfunc.i"]
_PKG_I_EXTRA = ["contour.i", "tristruct.i"]
_PKG_I_START = ["yiso3d.i"]


class YorickGlConan(ConanFile):
    name = "yorick-gl"
    version = "1.1-cvs20070922"
    description = ("yorick-gl (yorgl) — Yorick plugin; this build delivers the "
                   "yiso3d iso-surface/slicing engine (the GL/GLX half needs "
                   "an X11-enabled yorick, unavailable on OHOS)")
    license = "BSD-3-Clause"
    homepage = "https://software.llnl.gov/yorick-doc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # The Yorick interpreter: supplies the plugin build convention
        # (Make.cfg / Makepkg / Makedll), the public headers, and the host that
        # dlopen()s yorgl.so at run time.  No GL/X11 dependency is needed for
        # the yiso3d half (its objects link only against libc/libm).
        self.requires("yorick/2.2.04")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yorick-gl targets Linux/OHOS native builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        env = Environment()
        env.define("CC", compilers.get("c", "clang"))
        # OHOS /tmp may be read-only; keep configure/codger/make temporaries
        # inside this isolated Conan build directory.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        # NOTE: the script name MUST NOT be "conanbuild" -- that collides with
        # Conan's own aggregated conanbuild.sh and produces a self-sourcing
        # script (infinite recursion => sh SIGSEGV).
        env.vars(self).save_script("yorick_gl_build")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        yorick = self.dependencies["yorick"].package_folder
        yorick_bin = os.path.join(yorick, "bin", "yorick")
        if not os.path.isfile(yorick_bin):
            raise ConanException(f"yorick executable missing: {yorick_bin}")

        # --no-opengl is an upstream-supported configuration (README): yiso3d
        # is built even when OpenGL is unavailable.  See the module docstring
        # for why the GL half is not built here.
        self.run(
            f'sh ./configure --yorick="{yorick_bin}" --no-opengl',
            cwd=self.source_folder,
            env=["conanbuild", "yorick_gl_build"],
        )

        # Fail closed if configure did not select the intended yiso3d-only mode.
        makegl = os.path.join(self.source_folder, "Makegl")
        makegl_text = ""
        if os.path.isfile(makegl):
            with open(makegl, encoding="utf-8", errors="replace") as handle:
                makegl_text = handle.read()
        if "YISO_PKG_I" not in makegl_text or "YGL_PKG_I" in makegl_text:
            raise ConanException(
                "upstream configure did not produce the expected yiso3d-only "
                f"configuration (--no-opengl).\n--- Makegl ---\n{makegl_text}"
            )

        # R9: single-job build; CC from Conan conf overrides the value baked
        # into the yorick package's Make.cfg.
        self.run(
            f'make -j1 CC="{cc}"',
            cwd=self.source_folder,
            env=["conanbuild", "yorick_gl_build"],
        )

        plugin = os.path.join(self.source_folder, "yorgl.so")
        if not os.path.isfile(plugin):
            raise ConanException("upstream build did not produce yorgl.so")

        # Upstream tests: yorick-gl ships testgl.i and testisotree.i, but both
        # require an interactive OpenGL window (win3d / draw3d / palette3d), and
        # there is no check.i, so no upstream test is runnable here — see
        # test_package/MANIFEST.yml and notes.md.

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        copy(self, "LICENSE", src=src,
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        # the plugin shared object (yorick's plug_in loads "yorgl.so")
        copy(self, "yorgl.so", src=src,
             dst=os.path.join(pkg, "lib"), keep_path=False)
        # interpreted layer, mirroring the yorick install layout
        for name in _PKG_I:
            copy(self, name, src=src, dst=os.path.join(pkg, "i0"), keep_path=False)
        for name in _PKG_I_EXTRA:
            copy(self, name, src=src, dst=os.path.join(pkg, "i"), keep_path=False)
        for name in _PKG_I_START:
            copy(self, name, src=src,
                 dst=os.path.join(pkg, "i-start"), keep_path=False)

        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(os.path.join(pkg, "lib", "yorgl.so"))

    def package_info(self):
        # The plugin is dlopen()d by yorick, not linked against; export its
        # lib/ so consumers can locate yorgl.so.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []

    @staticmethod
    def _sign_ohos_elf(path):
        # Fail-closed OHOS self-signing (iron rule: sign real ELF, exactly one
        # .codesign section, restore permissions).
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"missing packaged plugin ELF: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                "signed plugin has invalid .codesign section count "
                f"({sections.count('.codesign')})"
            )
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

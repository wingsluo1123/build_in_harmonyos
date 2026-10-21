#!/usr/bin/env python3
"""Conan test_package — seyon 2.20c.

Two real consumers (R34: both must fail if the package artifacts are removed):

1. ``test_seyon`` — a minimal C program that links the packaged static library
   ``libseyon.a`` and calls seyon's yacc script parser ``ParseThis()``
   (SeParse.c), asserting the parsed function name / argument count / call
   count.  Headless: no X display is required.

2. ``test_seyon.sh`` — runs the packaged ``bin/seyon`` binary with no DISPLAY
   (``-noemulator`` reaches libXt's display-open failure path "Can't open
   display:", exit 1), a full dynamic-link/run smoke test, plus packaged
   artifact checks (static library, headers, help file), a DT_NEEDED check and
   a fail-closed ``.codesign`` section assertion on every packaged ELF.

Runtime X11 shared libraries come from the conan deps (VirtualRunEnv injects
LD_LIBRARY_PATH); the script additionally receives absolute .so paths for an
LD_PRELOAD fallback (loader may ignore LD_LIBRARY_PATH — xcdplayer/xeyes
precedent).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SeyonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # seyon is package_type="application", for which Conan defaults the
        # require traits to headers=False/libs=False (requires.py
        # process_package_type).  This package also ships a linkable static
        # library + headers, so ask for them explicitly.
        self.requires(self.tested_reference_str, headers=True, libs=True)
        # CMakeDeps only emits config files for direct requires of the consumer;
        # the X11 stack is needed to link libseyon.a's object set.
        self.requires("libx11/1.8.13")
        self.requires("libxaw/1.0.14")
        self.requires("libxmu/1.3.1.1")
        self.requires("libxt/1.3.1")
        self.requires("libxext/6.4.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_so(self, dep, soname_prefix):
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in sorted(files):
                if f.startswith(soname_prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        for p in hits:
            if not os.path.islink(p):
                return p
        return hits[0]

    def _runtime_preload(self):
        order = [("libxau", "libXau.so.6"),
                 ("libxdmcp", "libXdmcp.so.6"),
                 ("libxcb", "libxcb.so.1"),
                 ("libice", "libICE.so.6"),
                 ("libsm", "libSM.so.6"),
                 ("libx11", "libX11.so.6"),
                 ("libxext", "libXext.so.6"),
                 ("libxt", "libXt.so.6"),
                 ("libxmu", "libXmu.so.6"),
                 ("libxpm", "libXpm.so.4"),
                 ("libxaw", "libXaw.so.7")]
        found = []
        for name, prefix in order:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        # 1) consumer C program: links libseyon.a and calls ParseThis()
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_seyon")
        self.run(test_bin, env="conanrun")

        # 2) packaged binary + artifact smoke test
        pkg = self.dependencies["seyon"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        lib_dir = os.path.join(pkg, "lib")
        inc_dir = os.path.join(pkg, "include")
        share_dir = os.path.join(pkg, "share", "seyon")
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_seyon.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        self.run(f'"{shell}" "{script}" "{bin_dir}" "{lib_dir}" "{inc_dir}" '
                 f'"{share_dir}" "{preload}"', env="conanrun")

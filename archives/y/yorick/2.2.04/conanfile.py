#!/usr/bin/env python3
"""Conan recipe for yorick 2.2.04 — OHOS/aarch64 native build=host.

Yorick is an interpreted language for scientific computing that ships with a
custom (non-autoconf) ``configure`` shell script plus hand-written Makefiles.
It has no external library dependencies; X11 is optional and disabled here
(``NO_XLIB=1``) because the graphics backend is not required for the
interpreter/compute functionality and libx11 is not published to ohpcd.

Native build (build == target == OHOS/aarch64). Iron rule #0: never pass
``--host=``/``--build=``/``--target=`` to configure.

The produced ``bin/yorick`` locates its interpreted runtime relative to the
executable (``bin/../i0/std.i``), so the package keeps the upstream
relocatable layout: ``bin/`` plus ``i0/ i/ i-start/ g/ lib/ include/``.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    save,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout
from conan.tools.env import Environment

required_conan_version = ">=2.0"


class YorickConan(ConanFile):
    name = "yorick"
    version = "2.2.04"
    description = ("Yorick — an interpreted programming language for scientific "
                   "computing (interpreter + numeric/graphics libraries)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/LLNL/yorick"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # yorick builds in-source with generated Make.cfg (custom configure)
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Makefile projects must not rely on shell env vars; pull the
        # compiler from Conan conf and export it through the conanbuild env
        # script that self.run() applies.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        env = Environment()
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.define("AR", compilers.get("ar", "llvm-ar"))
        env.define("RANLIB", compilers.get("ranlib", "llvm-ranlib"))
        env.define("NO_XLIB", "1")
        # NOTE: the script name MUST NOT be "conanbuild" -- that collides with
        # Conan's own aggregated conanbuild.sh, producing a self-sourcing script
        # (". conanbuild.sh") => infinite recursion => sh dies with SIGSEGV (-11).
        env.vars(self).save_script("yorick_build")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        # Custom configure: NO_XLIB drops the X11 play backend (unix only),
        # CC from Conan conf (iron rule #0: no --host/--build/--target).
        self.run(f"NO_XLIB=1 CC={cc} sh ./configure")

        # R9: single-job build on OHOS; builds executables + static libs.
        self.run("NO_XLIB=1 make -j1")

        # L1 upstream test suite (real execution of upstream scripts).
        #
        # The upstream `make check` runs ./yorick -batch check.i ->
        # i/testfull.i, which mixes interpreter/numeric tests with
        # interactive-graphics tests (testg, demo2, grtest, txtest).  Those
        # graphics tests call `window` and `palette` and therefore require an
        # interactive display or a hardcopy graphics device -- neither exists
        # in this NO_XLIB headless build (X11 is unavailable on the target and
        # libx11 is not published to ohpcd).  Running the full check.i aborts
        # at the first graphics test (`lissajous` -> window -> "No interactive
        # graphics in this Yorick -- hcp only").
        #
        # So we drive the SAME upstream scripts, minus the interactive-graphics
        # ones, via this driver (unit = one upstream test script):
        #   PASS   : testp.i (parser/IO/string/oxy, "0 goofs"), testm (math),
        #            testlp (LINPACK benchmark)
        #   NOT_RUN: testg, demo2, grtest, txtest  (require a graphics device)
        # See notes.md for the per-item accounting.
        driver = (
            "/* OHOS headless: upstream interpreter/numeric tests only.      */\n"
            "/* Interactive-graphics tests need a display; see conanfile.py.  */\n"
            "skip_testb= 0;\n"
            "skip_test1= 0;\n"
            "skip_test2= 0;\n"
            "skip_test3= 0;\n"
            "npass= 20;\n"
            '#include "testp.i"\n'
            '#include "testm.i"\n'
            "testm;\n"
            '#include "testlp.i"\n'
            "testlp, 200;\n"
            'write, "";\n'
        )
        save(self, os.path.join(self.build_folder, "ohos-headless-check.i"), driver)
        # Run from yorick/ so ./yorick resolves and Y_SITE (= its parent) finds
        # the i/ interpreted library, matching `make check`'s working directory.
        self.run("./yorick -batch ../ohos-headless-check.i",
                 cwd=os.path.join(self.build_folder, "yorick"))

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        dst_bin = os.path.join(pkg, "bin")
        dst_lib = os.path.join(pkg, "lib")
        dst_inc = os.path.join(pkg, "include")

        # executables
        copy(self, "yorick/yorick", src=src, dst=dst_bin, keep_path=False)
        copy(self, "gist/gist", src=src, dst=dst_bin, keep_path=False)

        # static libraries + build support for compiled extensions
        copy(self, "yorick/libyor.a", src=src, dst=dst_lib, keep_path=False)
        copy(self, "yorick/main.o", src=src, dst=dst_lib, keep_path=False)
        copy(self, "yorick/codger", src=src, dst=dst_lib, keep_path=False)
        copy(self, "yorick/libdep.sh", src=src, dst=dst_lib, keep_path=False)
        copy(self, "yorick/install.sh", src=src, dst=dst_lib, keep_path=False)

        # public headers for building compiled packages
        copy(self, "play/*.h", src=src, dst=dst_inc, keep_path=False)
        copy(self, "gist/*.h", src=src, dst=dst_inc, keep_path=False)
        copy(self, "yorick/*.h", src=src, dst=dst_inc, keep_path=False)
        copy(self, "play/unix/config.h", src=src, dst=dst_inc, keep_path=False)

        # interpreted runtime: MUST sit in the parent of bin/ (relocatable lookup)
        copy(self, "*.i", src=os.path.join(src, "i0"),
             dst=os.path.join(pkg, "i0"))
        copy(self, "*.i", src=os.path.join(src, "i"),
             dst=os.path.join(pkg, "i"))
        copy(self, "*.i", src=os.path.join(src, "i-start"),
             dst=os.path.join(pkg, "i-start"))
        copy(self, "*.gs", src=os.path.join(src, "g"),
             dst=os.path.join(pkg, "g"))
        copy(self, "*.gp", src=os.path.join(src, "g"),
             dst=os.path.join(pkg, "g"))
        copy(self, "ps.ps", src=os.path.join(src, "g"),
             dst=os.path.join(pkg, "g"))

        # build metadata needed when compiling yorick packages
        copy(self, "Make.cfg", src=src, dst=pkg, keep_path=False)
        copy(self, "Makepkg", src=src, dst=pkg, keep_path=False)
        copy(self, "Makeexe", src=src, dst=pkg, keep_path=False)
        copy(self, "Makedll", src=src, dst=pkg, keep_path=False)
        copy(self, "LICENSE.md", src=src, dst=pkg, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

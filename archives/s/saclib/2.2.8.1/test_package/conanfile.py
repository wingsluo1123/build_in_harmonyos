#!/usr/bin/env python3
"""test_package for saclib/2.2.8 — real API consumer test.

The package is a static C library, so the test has to do two things:

  1. link test.c against the installed archive through the package's own
     cpp_info (include dirs, lib name, system libs), which is what a downstream
     project would do;
  2. run the resulting binary, which asserts on exact big-integer invariants and
     on the garbage collector (see test.c for the individual invariants).

A library that links but computes wrong values, or whose AArch64 register spill
leaves the collector blind, fails step 2.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SaclibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["saclib"]
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"

        incflags = " ".join("-I%s" % d for d in dep.cpp_info.includedirs)
        libflags = " ".join("-L%s" % d for d in dep.cpp_info.libdirs)
        libs = " ".join("-l%s" % lib for lib in dep.cpp_info.libs)
        # system_libs carries libm, which SACLIB's hardware-float routines need
        syslibs = " ".join("-l%s" % lib for lib in dep.cpp_info.system_libs)
        link = "%s %s %s" % (libflags, libs, syslibs)

        # 1. assertion suite (unit-level checks of the arithmetic, the heap and
        #    the collector)
        self.run("%s -O2 -Wall %s test.c -o saclib_test %s"
                 % (cc, incflags, link))

        # 2. a complete consumer workflow: one program that reads a problem
        #    file and does a whole job end to end (exact factorial, exact
        #    rational arithmetic, decimal expansion with cycle detection),
        #    printing results that are checked independently.
        self.run("%s -O2 -Wall %s consumer_flow.c -o consumer_flow %s"
                 % (cc, incflags, link))

        # 3. the upstream sample -- the only runnable artefact SACLIB ships and
        #    the only upstream code that uses the sacMain() hook, so building it
        #    also exercises the weak-symbol handling of patches/0002.  It is a
        #    verbatim copy of saclib2.2.8/doc/user_guide/sample.c, kept beside
        #    the test so the test package stays self-contained (CI only reads
        #    this directory).
        sample = os.path.join(self.recipe_folder, "sample.c")
        if os.path.isfile(sample):
            self.run("%s -O2 -Wall %s %s -o sample_test %s"
                     % (cc, incflags, sample, link))

    def test(self):
        if not can_run(self):
            return
        # OHOS /bin/sh is mksh, which does not execute ELF binaries; drive the
        # compiled test through the bash named by CONFIG_SHELL (profile buildenv).
        bash = os.environ.get("CONFIG_SHELL") or "sh"
        self.run('%s test.sh' % bash, env="conanrun")

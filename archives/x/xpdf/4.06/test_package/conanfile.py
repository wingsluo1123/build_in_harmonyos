#!/usr/bin/env python3
"""xpdf 4.06 consumer test package.

This is a CLI tool package: the product is a set of executables, so the test drives
the installed binaries instead of linking a library. No CMake — the test script is
plain POSIX sh and the toolchain has no reason to be involved.
"""
import os

from conan import ConanFile


class XpdfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.cpp.source.bindirs = ["bin"]

    def test(self):
        # VirtualRunEnv is mandatory: without it the test's own environment lacks the
        # package's bin/ on PATH and the tools are not found, and a bare self.run()
        # also misses LD_LIBRARY_PATH for the runtime .so dependencies — which shows up
        # as a bogus "compile failure". opustags is the precedent.
        # It is declared ONCE, via the `generators` attribute above. Do NOT also
        # instantiate VirtualRunEnv(self).generate() here: Conan raises
        # "VirtualRunEnv is declared in the generators attribute, but was instantiated
        # in the generate() method too" because install_consumer() restores the
        # attribute before test() runs (conan 2.32.0: api/subapi/install.py:141,
        # internal/api/install/generators.py:122, internal/__init__.py:7).
        script = os.path.join(self.source_folder, "test_xpdf.sh")
        self.run("sh {}".format(script), env="conanrun")

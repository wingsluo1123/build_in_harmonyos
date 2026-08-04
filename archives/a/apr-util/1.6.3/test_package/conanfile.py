#!/usr/bin/env python3
"""Conan test_package — apr-util 1.6.3 L1 test.

Uses AutotoolsDeps to get correct include/library paths for APR and expat.
Tests APR-util API: apr_initialize, apr_pool_create, apr_bucket_alloc_create,
apu_version_string, apr_version_string, apr_terminate.
"""
from conan import ConanFile


class AprUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsDeps", "AutotoolsToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.run(
            "$CC -c test.c -o test.o $CFLAGS $CPPFLAGS",
            env="conanbuild",
        )
        self.run(
            "$CC -o test_apr_util test.o $LDFLAGS $LIBS",
            env="conanbuild",
        )

    def test(self):
        self.run("./test_apr_util", env="conanrun")

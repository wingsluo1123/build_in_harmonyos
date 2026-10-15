#!/usr/bin/env python3
"""Conan test_package — pluto L1 test (daemon binary execution, R34).

pluto is an IPsec IKE daemon (an application, not a library), so the L1 test
executes the shipped binaries directly rather than linking a test program:
`pluto --version` must succeed and report the Libreswan version plus the
capability banner (confirming the NSS crypto backend and the XFRM kernel
interface were compiled in); the 5 upstream self-test entry points (3 zero-arg
check tools + algparse --tp/--ta) must exit 0 (real upstream test code
executed in CI); and a HarmonyOS-specific consumer case runs a real
ipsec.conf load on the HongMeng kernel (harmony_consumer_test.sh). A full
daemon startup requires kernel XFRM + control-socket privileges (the R40
runtime boundary) and is therefore out of scope for the L1 smoke test.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PlutoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        pluto = os.path.join(bindir, "pluto")
        if not os.path.isfile(pluto):
            raise ConanException("pluto binary not found: %s" % pluto)
        # R34: substantively exercise the tested package — test.sh runs the
        # pluto daemon binary and asserts the capability banner (NSS + XFRM
        # compiled in). It is invoked through the conanrun env, which prepends
        # the pluto bindir to PATH and sets LD_LIBRARY_PATH for the NSS/NSPR/
        # libevent shared libraries the daemon links against (see the
        # package_info runenv fix in the recipe). self.run() propagates a
        # non-zero exit as a test failure.
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run('sh "%s"' % test_sh, env="conanrun")

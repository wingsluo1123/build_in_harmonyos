#!/usr/bin/env python3
"""test_package — poldi 0.4.2-git20201120.5d67235 (HarmonyOS PAM flow).

The package's only artifact is a PAM module, i.e. a plugin that the PAM stack
loads with ``dlopen(3)``: there is no API for a consumer to link against and
no program to run, so the E345 "ABI-matched private host" pattern is used —
libpam from the Conan linux-pam package is the host, and a small consumer
program (``test_pam_module.c``) drives the packaged module through
``pam_start_confdir()``/``pam_authenticate()``.

Two real end-to-end runs are performed:

1. ``missing`` — the service file points at a non-existent module.  libpam
   must answer ``PAM_MODULE_UNKNOWN``; that control run proves the harness
   genuinely detects a module that cannot be loaded (i.e. case 2 cannot pass
   vacuously).
2. ``poldi`` — the service file points at the packaged
   ``lib/security/pam_poldi.so``.  The module must be found, loaded (its
   libpam/libgcrypt/libgpg-error/libksba closure resolved from the Conan
   packages) and its ``pam_sm_authenticate()`` must return a genuine PAM
   result — never a module-load failure code.  Without a writable
   ``/etc/poldi`` and without an OpenPGP card the module cannot authenticate
   anybody, so the observable criterion is that its entry point ran.

Both cases therefore execute the full consumer chain
``test program -> libpam -> dlopen(module) -> poldi code -> libgcrypt/
libgpg-error/libksba``, which is what the platform-specific linking fix in
patch 0001 is needed for.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, save


class PoldiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def export_sources(self):
        # CI gate L0c requires a test source file inside test_package/.
        copy(self, "test_pam_module.c", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The host side of the flow: the consumer program is a libpam client,
        # and Conan does not forward the tested package's requirements into
        # this graph.
        self.requires("linux-pam/1.7.2")

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this platform; skipping")
            return

        pam = self.dependencies["linux-pam"]
        pam_include = os.path.join(pam.package_folder, "include")
        pam_lib = os.path.join(pam.package_folder, "lib")
        module = os.path.join(self.dependencies["poldi"].package_folder,
                              "lib", "security", "pam_poldi.so")
        if not os.path.isfile(module):
            raise ConanException("packaged module not found: {}".format(module))

        # Build the consumer with the profile's C compiler; it must be a
        # libpam client so that the module is loaded by a real PAM stack.
        conf = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = conf.get("c") or os.environ.get("CC") or "clang"
        consumer = os.path.join(self.build_folder, "test_pam_module")
        self.run('"{}" -o "{}" "{}" -I"{}" -L"{}" -lpam'.format(
            cc, consumer, os.path.join(self.source_folder, "test_pam_module.c"),
            pam_include, pam_lib))

        confdir = os.path.join(self.build_folder, "pam.d")
        os.makedirs(confdir, exist_ok=True)
        save(self, os.path.join(confdir, "missing"),
             "auth required /nonexistent/pam_module.so\n")
        save(self, os.path.join(confdir, "poldi"),
             "auth required {}\n".format(module))

        cases = [("missing", "unknown"), ("poldi", "loaded")]
        for service, expectation in cases:
            self.run('"{}" "{}" "{}" "{}"'.format(consumer, confdir, service,
                                                 expectation),
                     env="conanrun")

        marker = {
            "executed": True,
            "passed": True,
            "command": "test_pam_module <pam.d> <service> <loaded|unknown>",
            "discovered": len(cases),
            "passedCount": len(cases),
            "cases": ["missing -> PAM_MODULE_UNKNOWN",
                      "poldi -> pam_sm_authenticate executed"],
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))

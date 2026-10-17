#!/usr/bin/env python3
"""test_package for pwauth 2.3.11 — end-to-end consumer test of the authenticator.

`test_consumer.c` is compiled and then behaves like Apache mod_authnz_external:
it spawns the packaged `pwauth` binary, writes "<login>\\n<password>\\n" to its
stdin and takes the exit status as the authentication result.  `test.sh` uses it
to verify a complete authentication flow (success through a private PAM service
built on the linux-pam package's pam_permit.so, plus the failure paths) and the
documented status codes.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PwauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        shell = self._find_shell()
        pam_module = self._pam_permit_module()
        prefix = 'PWAUTH_TEST_PAM_MODULE="{}" '.format(pam_module) if pam_module else ""
        self.run("{}{} test.sh".format(prefix, shell), env="conanrun")

    def _pam_permit_module(self):
        """Absolute path of the pam_permit.so shipped by the linux-pam package.

        test.sh falls back to the LINUX_PAM_MODULE_DIR environment variable
        exported by that package when this lookup is not possible.
        """
        try:
            package_folder = self.dependencies["linux-pam"].package_folder
        except Exception:  # dependency not visible: rely on the env fallback
            return ""
        if not package_folder:
            return ""
        return os.path.join(package_folder, "lib", "security", "pam_permit.so")

    @staticmethod
    def _find_shell():
        """Pick a shell able to execute ELF binaries.

        OHOS /system/bin/sh (mksh) cannot launch ELF binaries, so a real bash is
        preferred; CONFIG_SHELL from the OHOS profile may point at mksh (or at a
        path that does not exist on a given device), hence the order below.
        """
        candidates = [shutil.which("bash"), os.environ.get("CONFIG_SHELL"),
                      shutil.which("sh"), "/bin/sh"]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException("no POSIX shell found to run test_package/test.sh")

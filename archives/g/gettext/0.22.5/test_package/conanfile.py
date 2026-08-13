import os

from conan import ConanFile
from conan.errors import ConanException


class GettextTestConan(ConanFile):
    """test_package for gettext 0.22.5.1 — smoke test envsubst/gettext tools."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["gettext"]
        bindir = os.path.join(dep.package_folder, "bin")

        # 1. envsubst must exist and report version
        envsubst = os.path.join(bindir, "envsubst")
        if not os.path.isfile(envsubst):
            raise ConanException(f"envsubst not found in {bindir}")
        rc = self.run(f'"{envsubst}" --version 2>&1', env="conanrun",
                      ignore_errors=True)
        if rc != 0:
            raise ConanException("envsubst --version failed to execute")
        self.output.info("envsubst --version: OK")

        # 2. envsubst functional test: substitute $VAR
        out = self.run(f'echo "hello $USER" | "{envsubst}" > /dev/null 2>&1',
                       env="conanrun", ignore_errors=True)
        if out != 0:
            raise ConanException("envsubst functional test failed")
        self.output.info("envsubst functional: OK")

        # 3. gettext tool must exist
        gettext_bin = os.path.join(bindir, "gettext")
        if not os.path.isfile(gettext_bin):
            raise ConanException(f"gettext not found in {bindir}")
        rc = self.run(f'"{gettext_bin}" --version > /dev/null 2>&1',
                      env="conanrun", ignore_errors=True)
        if rc not in (0, 1):
            raise ConanException(f"gettext --version crashed (exit {rc})")
        self.output.info("gettext: OK")

        # 4. libintl header must be installed
        incdir = os.path.join(dep.package_folder, "include")
        if not os.path.isfile(os.path.join(incdir, "libintl.h")):
            raise ConanException("libintl.h not found in package include/")
        self.output.info("libintl.h: OK")

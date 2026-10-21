import os
import sys

from conan import ConanFile
from conan.tools.build import can_run

# Every runtime dependency whose import path must be attributed to its own
# Conan package folder rather than to some copy the host happens to have.
# certifi/chardet/idna/urllib3 are requests' own import closure; the recipe
# declares them directly precisely so their paths are published to consumers.
_DEPS = ("click", "requests", "tabulate", "pyyaml",
         "certifi", "chardet", "idna", "urllib3")


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        # The Conan sandbox PATH carries no python3, so the absolute OHOS
        # interpreter is used when present.
        py = "/data/service/hnp/bin/python3"
        if not os.path.isfile(py):
            py = sys.executable

        pkg = self.dependencies["synadm"].package_folder
        dep_args = " ".join(
            f'"{name}={self.dependencies[name].package_folder}"'
            for name in _DEPS
        )

        # env="conanrun" gives the test exactly the PYTHONPATH/PATH a consumer
        # of this package sees, and PYTHONNOUSERSITE keeps the user site out of
        # sys.path so the two environments cannot disagree about provenance.
        # Both suites are executed even if the first one fails, so one failure
        # never hides the state of the other.
        here = os.path.dirname(__file__)
        failed = []
        for script in ("test_synadm.py", "test_synadm_ohos.py"):
            path = os.path.join(here, script)
            ret = self.run(
                f'PYTHONNOUSERSITE=1 {py} "{path}" "{pkg}" {dep_args}',
                env="conanrun",
                ignore_errors=True,
            )
            if ret != 0:
                failed.append(f"{script} (exit {ret})")
        if failed:
            raise Exception("test_package failed: " + ", ".join(failed))

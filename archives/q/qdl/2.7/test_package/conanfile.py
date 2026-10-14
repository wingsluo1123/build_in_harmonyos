import os

from conan import ConanFile


class QdlTestConan(ConanFile):
    """test_package for qdl — a *tool* package (no library, no public headers).

    The consumer is whatever user would `conan install` this package for: someone
    who wants the `qdl` / `qdl-ramdump` / `qdl-ks` executables on PATH. There is
    nothing to link against, so the verification runs the installed binaries the
    way a real user does — including one real, device-free workload
    (`--dry-run --create-digests`) over the upstream flat-build fixtures.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

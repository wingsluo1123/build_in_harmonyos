import os

from conan import ConanFile


class InsteadTestConan(ConanFile):
    """test_package for INSTEAD Engine 3.5.2 — executable consumer.

    INSTEAD ships `bin/sdl-instead` (aliased to `instead`). R34 is
    satisfied by executing the binary against a minimal smoke harness
    (--version, --help), which is what upstreams ship. The engine's
    interpreter API is also surfaced for future build-in-hmos consumers
    via the package's `include/instead/instead.h`, but that header is
    declaration-only — its symbols live in `sdl-instead`, not in a
    archive, so we keep the test scope tight to the executable contract.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Wrap binary execution via bash from the toolchain HNP.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

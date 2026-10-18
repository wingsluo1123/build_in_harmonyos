import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout

# OHOS bash locations, in preference order.  $CONFIG_SHELL is checked first
# (the ohos-aarch64 profile declares an absolute path in [buildenv]);
# shutil.which() is deliberately not used, it picks up the invoking runtime's
# bundled bash which conan's spawned shell cannot execute.
_OHOS_BASH_CANDIDATES = (
    "/data/service/hnp/bin/bash",
    "/bin/bash",
    "/usr/bin/bash",
)


class VtableTestConan(ConanFile):
    """test_package for vtable 1.2 — drives the CLI that this package installs.

    vtable is an application package, so the L1 test is a behaviour contract on
    the installed executable: test.sh builds a real C++ shared library, has the
    installed tool dump its virtual tables and asserts the reported class
    names, entry counts and member functions.  See test.sh for the check list
    and test_package/MANIFEST.yml for the upstream inventory (upstream ships no
    automated test suite).
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Resolve the binary from the package folder explicitly: removing the
        # package must make this test fail (CI L1e destructive reverse check).
        tool = os.path.join(
            self.dependencies["vtable"].package_folder, "bin", "vtable-dumper"
        )
        if not os.path.isfile(tool):
            raise ConanException(f"installed binary not found: {tool}")
        script = os.path.join(self.source_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) cannot reliably spawn ELF binaries, so the
        # script runs under a real bash; a missing interpreter must fail loudly
        # instead of being masked by a baked-in default.
        shell = os.environ.get("CONFIG_SHELL")
        if not shell or not os.path.exists(shell):
            shell = next(
                (p for p in _OHOS_BASH_CANDIDATES if os.path.exists(p)), None
            )
        if not shell:
            raise ConanException(
                "no bash found to run test_package/test.sh: set CONFIG_SHELL "
                "(see ci/conan/profiles/ohos-aarch64) or install bash under "
                + " / ".join(_OHOS_BASH_CANDIDATES)
            )
        self.run(f'"{shell}" "{script}" "{tool}"', env="conanrun")

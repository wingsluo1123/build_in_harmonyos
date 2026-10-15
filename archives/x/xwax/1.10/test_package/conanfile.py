import os

from conan import ConanFile


class XwaxTestConan(ConanFile):
    """test_package for the xwax executable — headless consumer smoke test.

    Runs test.sh, which executes the packaged bin/xwax binary with --help and
    asserts the compiled-in version banner and usage text (a real code path:
    locale setup, thread/rig init and the option parser all run before the
    banner is printed). No display, font or audio device is required.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bin_path = os.path.join(dep.package_folder, "bin", "xwax")
        if not os.path.isfile(bin_path):
            raise Exception(f"xwax binary not found in package: {bin_path}")
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries: wrap the
        # smoke run in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh {bin_path} {dep.package_folder}",
                 env="conanrun")

from conan import ConanFile


class TclTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Execute the shell-based smoke test script (satisfies L0c test source check)
        self.run("bash test_tcl.sh", env="conanrun")

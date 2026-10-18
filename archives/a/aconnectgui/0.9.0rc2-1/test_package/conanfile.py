from conan import ConanFile


class AconnectguiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Real consumer smoke: run test.sh against the installed aconnectgui
        # binary. test.sh asserts the loader + NEEDED libs resolve (rc not
        # 126/127); a headless "cannot open display" exit is accepted.
        self.run("sh ./test.sh", env="conanrun")

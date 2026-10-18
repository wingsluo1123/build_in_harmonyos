from conan import ConanFile


class UlogdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Real consumer smoke against the installed ulogd binary (see test.sh).
        # Runs on the real OHOS CI worker (native aarch64) — deliberately NOT
        # gated on cross_building(): a skipped test is judged a fake test by the
        # L1e negative-test gate (R34). test.sh asserts the binary is on PATH and
        # that the dynamic loader + NEEDED libs resolve (rc not 126/127).
        self.run("sh ./test.sh", env="conanrun")

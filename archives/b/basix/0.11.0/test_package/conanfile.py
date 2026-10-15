import os
import shlex
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv

class BasixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        if self.settings.os == "OHOS":
            parent = Path("/data/storage/el2/base/cache")
            if (not parent.is_dir() or parent.resolve() != parent
                    or parent.is_symlink() or parent.stat().st_uid != os.getuid()
                    or not os.access(parent, os.W_OK | os.X_OK)):
                raise RuntimeError("Actual owned POSIX consumer temporary parent required")
            self._temporary_manager = tempfile.TemporaryDirectory(
                prefix="basix-consumer-", dir=str(parent))
            temporary = Path(self._temporary_manager.name)
            if (temporary.resolve() != temporary or temporary.is_symlink()
                    or temporary.stat().st_uid != os.getuid()
                    or stat.S_IMODE(temporary.stat().st_mode) != 0o700):
                raise RuntimeError("Unsafe native consumer temporary directory")
            self._test_tmp = str(temporary)
            self.output.info("ACTUAL_BASIX_CONSUMER_TMPDIR=" + self._test_tmp)
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        with self._environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _environment(self):
        environment = Environment()
        if self.settings.os == "OHOS":
            environment.define("TMPDIR", self._test_tmp)
        return environment

    def test(self):
        with self._environment().vars(self).apply():
            self._test()

    def _test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "basix_consumer")
            if self.settings.os == "OHOS":
                objcopy = shutil.which("llvm-objcopy")
                signer = shutil.which("binary-sign-tool")
                if not objcopy or not signer:
                    raise RuntimeError("Actual target signing tools are required")
                self.run(shlex.join([objcopy, "--remove-section", ".codesign", executable]))
                self.run(shlex.join([signer, "sign", "-inFile", executable, "-outFile", executable, "-selfSign", "1"]))
            self.run(shlex.join([executable]), env="conanrun")
            if self.settings.os == "OHOS":
                source = os.path.join(self.source_folder, "harmony_tests", "private_state.py")
                self.run(shlex.join([sys.executable, source, executable]), env="conanrun")

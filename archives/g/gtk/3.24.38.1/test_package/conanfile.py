import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class Gtk3TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _build_environment(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                # CMake's compiler probe invokes the SDK lld, which needs its
                # ABI-matched libxml2 from the adjacent SDK runtime directory.
                environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
        return environment

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        if not os.path.isfile(path):
            raise ConanException(f"Missing consumer executable: {path}")
        if not signer or not readelf:
            raise ConanException("Required OHOS signing tools are missing from PATH")
        output = path + ".gtk-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executables = [
            os.path.join(self.cpp.build.bindir, name + suffix)
            for name in ("test_gtk3", "gtk_gettext_probe")
        ]
        if str(self.settings.os) == "OHOS":
            for executable in executables:
                self._sign_ohos_elf(executable)
        # 两个用例都由 CTest 判定（与 abiword test_package 同款形态）：
        #   1/2 test_gtk3          —— 原有链接冒烟用例
        #   2/2 gtk_gettext_probe  —— V2 最小验收：exit=0 且输出含 "[gtkprobe] done"
        # 期望 conan 日志出现 "100% tests passed, 0 tests failed out of 2"（2/2 Passed）。
        self.run(
            "ctest --output-on-failure -C {}".format(self.settings.build_type),
            env="conanrun",
            cwd=self.build_folder,
        )

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class LibusbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        includes = []
        libdirs = []
        libs = []
        for _, dependency in self.dependencies.items():
            info = dependency.cpp_info
            includes.extend(info.includedirs)
            libdirs.extend(info.libdirs)
            libs.extend(info.libs)
            libs.extend(info.system_libs)

        def unique(items):
            seen = set()
            result = []
            for item in items:
                if item and item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or os.environ.get("CC")
        if not cc:
            raise ConanException("C compiler not found in tools.build:compiler_executables or CC")

        include_flags = " ".join(f'-I"{path}"' for path in unique(includes))
        libdir_flags = " ".join(f'-L"{path}"' for path in unique(libdirs))
        lib_flags = " ".join(f"-l{name}" for name in unique(libs))
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.run(
            f'TMPDIR="{tmpdir}" {cc} test_libusb.c -o test_libusb '
            f"{include_flags} {libdir_flags} {lib_flags}"
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile and link test completed")
            return
        binary = os.path.join(self.build_folder, "test_libusb")
        self._sign_if_needed(binary)
        self.run(binary, env="conanrun")

    def _sign_if_needed(self, binary):
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=False)
        signed = binary + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, binary)
        os.chmod(binary, 0o755)

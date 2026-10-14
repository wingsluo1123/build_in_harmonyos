#!/usr/bin/env python3
"""Conan recipe for shuffle 1.6 - shuffle the lines of a file (single C source).

HarmonyOS PC adaptation points:
- Upstream is one C file (shuffle.c, $Id: shuffle.c,v 1.6) published on the
  W3C server; no archive, build system or tests exist.  The recipe downloads the
  pinned file and builds it with a tiny CMakeLists.txt so that the compiler and
  flags come from the Conan toolchain.
- patches/0001: `open(outfile, O_WRONLY|O_CREAT)` has no mode argument.  open()
  is variadic and musl reads the mode with va_arg() when O_CREAT is set, so the
  permission bits of the new output file are whatever the caller left in the
  argument register (observed 0155 under qemu-aarch64: no read/write for the
  owner).  An explicit 0666 (filtered by the umask) makes the result defined.
- The .codesign section emitted by the SDK linker is not accepted by the OHOS
  loader (E077/E077B): the packaged executable is re-signed on OHOS builds.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches)


class ShuffleConan(ConanFile):
    name = "shuffle"
    version = "1.6"
    description = "Shuffle the lines of a file or stdin in random order (W3C, Bert Bos)"
    license = "W3C"
    homepage = "https://www.w3.org/People/Bos/Shuffle/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("shuffle", "lines", "random", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain"

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"shuffle supports Linux and OHOS, not {self.settings.os}")

    def source(self):
        info = self.conan_data["sources"][self.version]
        download(self, info["url"], os.path.join(self.source_folder, "shuffle.c"),
                 sha256=info["sha256"])

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "shuffle", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "shuffle"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.warning("binary-sign-tool/llvm-objcopy not found: bin/shuffle left unsigned")
            return
        env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        work = os.path.join(self.build_folder, "codesign")
        os.makedirs(work, exist_ok=True)
        unsigned = os.path.join(work, "shuffle")
        signed = unsigned + ".signed"
        shutil.copy2(path, unsigned)
        subprocess.run([objcopy, "--remove-section", ".codesign", unsigned],
                       check=True, env=env, timeout=60)
        subprocess.run([signer, "sign", "-inFile", unsigned, "-outFile", signed,
                        "-selfSign", "1"], check=True, env=env, timeout=120)
        shutil.copy2(signed, path)
        os.chmod(path, 0o755)

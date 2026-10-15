#!/usr/bin/env python3
"""Consumer tests for sfront 0.99.

Everything runs the packaged ``bin/sfront``:

* ``test_sfront.sh``  - the upstream CLI surface plus every upstream example
  orchestra shipped in ``share/sfront/examples`` that can be translated without
  network or soundcard hardware, including the upstream ``mp4test`` flow
  (encode to an MP4-SA bitstream, decode it again, and require the regenerated C
  program to match the direct ``-orc`` translation).
* the same script then compiles two of the generated C programs with the OHOS
  toolchain and executes the resulting AArch64 binaries (natively on AArch64,
  through ``qemu-aarch64`` elsewhere), asserting the synthesised WAV files are
  well-formed, non-silent PCM of the expected rate and length.  That is the
  HarmonyOS-specific use case: it proves the whole toolchain chain - translator,
  generated program, OHOS libc - works end to end on the platform.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SfrontTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        work = os.path.join(self.build_folder, "sfront-tests")
        script = os.path.join(self.recipe_folder, "test_sfront.sh")
        self.run(shlex.join(["bash", script, package_folder, work, cc]),
                 env="conanrun")

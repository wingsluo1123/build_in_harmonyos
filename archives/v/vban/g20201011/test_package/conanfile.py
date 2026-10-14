#!/usr/bin/env python3
"""Conan test package — vban g20201011 command-line consumers."""

import glob
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class VbanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # application packages do not necessarily propagate their runtime closure.
        self.requires("alsa-lib/1.2.16.1", transitive_libs=True)
        self.requires("pulseaudio/17.0.1", transitive_libs=True)
        self.requires("jack/1.9.22", transitive_libs=True)

    def test(self):
        package_folder = self.dependencies["vban"].package_folder
        if not package_folder:
            raise RuntimeError("vban package folder is unavailable")
        bin_dir = os.path.join(package_folder, "bin")
        for command in ("vban_receptor", "vban_emitter", "vban_sendtext"):
            path = os.path.join(bin_dir, command)
            if not os.path.isfile(path) or not os.access(path, os.X_OK):
                raise RuntimeError(f"missing packaged command: {path}")

        if not can_run(self) or platform.system() != "HarmonyOS":
            self.output.warning(
                "SKIP: runtime assertions require a native HarmonyOS host")
            return
        lib_dirs = []
        for dependency in self.dependencies.values():
            folder = dependency.package_folder
            if not folder:
                continue
            for root, _dirs, files in os.walk(folder):
                if any(name.endswith(".so") or ".so." in name for name in files):
                    lib_dirs.append(root)

        # Some published OHOS dependencies predate mandatory ELF signing.
        # Sign temporary copies for the runtime probe; package contents remain untouched.
        signed = self._sign_private_libraries(lib_dirs)
        if signed:
            lib_dirs.insert(0, signed)
        env = Environment()
        env.define("LD_LIBRARY_PATH", os.pathsep.join(dict.fromkeys(lib_dirs)))
        env.vars(self).save_script("vban_test_runtime")

        script = os.path.join(self.source_folder, "test_vban.py")
        self.run(shlex.join(["python3", script, bin_dir]),
                 env=["conanrun", "vban_test_runtime"])

    def _sign_private_libraries(self, lib_dirs):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        # The signing utility is meaningful only for the native HarmonyOS
        # loader.  Cross-test hosts may provide a compatibility stub that
        # exits successfully without producing an output file.
        if (str(self.settings.os) != "OHOS"
                or platform.system() != "HarmonyOS"
                or not os.path.isfile(signer)):
            return None
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(objcopy):
            objcopy = shutil.which("llvm-objcopy")
        destination = os.path.join(self.build_folder, "signed-runtime")
        shutil.rmtree(destination, ignore_errors=True)
        os.makedirs(destination, exist_ok=True)
        signed = False
        for directory in lib_dirs:
            for source in glob.glob(os.path.join(directory, "*.so*")):
                if not os.path.isfile(source):
                    continue
                try:
                    with open(source, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                target = os.path.join(destination, os.path.basename(source))
                unsigned = target + ".unsigned"
                candidate = target + ".signed"
                try:
                    shutil.copy2(source, unsigned)
                    with open(unsigned, "rb") as handle:
                        has_old_signature = b".codesign" in handle.read()
                    if has_old_signature:
                        if not objcopy:
                            raise RuntimeError(
                                "llvm-objcopy is required to re-sign private OHOS libraries")
                        self.run(shlex.join(
                            [objcopy, "--remove-section", ".codesign", unsigned]))
                    self.run(shlex.join([signer, "sign", "-inFile", unsigned,
                                         "-outFile", candidate, "-selfSign", "1"]))
                    with open(candidate, "rb") as handle:
                        if handle.read().count(b".codesign") != 1:
                            raise RuntimeError(
                                "private OHOS library does not contain one fresh .codesign")
                    os.replace(candidate, target)
                    os.chmod(target, 0o755)
                finally:
                    for temporary in (unsigned, candidate):
                        if os.path.exists(temporary):
                            os.unlink(temporary)
                signed = True
        return destination if signed else None

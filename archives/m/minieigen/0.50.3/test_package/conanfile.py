#!/usr/bin/env python3
"""Consumer and target-ABI tests for minieigen."""

import glob
import hashlib
import os
import runpy
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration


class MinieigenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        minieigen = self.dependencies["minieigen"]
        python = self._dependency("python")
        contract = self._target_python_contract(python)
        site = os.path.join(
            minieigen.package_folder,
            "lib",
            "python{}".format(contract["version"]),
            "site-packages",
        )
        extensions = glob.glob(os.path.join(site, "minieigen*.so"))
        if len(extensions) != 1:
            raise ConanException(
                "expected exactly one minieigen extension, found {}".format(extensions)
            )
        self._verify_elf(extensions[0], contract["suffix"])
        self.run(self._python_command(python, contract, site))
        self._verify_discovery_contract(extensions[0], python, contract)

    def _dependency(self, name):
        for dependency in self.dependencies.values():
            if dependency.ref.name == name:
                return dependency
        raise ConanException("missing dependency: {}".format(name))

    def _target_python_contract(self, python):
        candidates = sorted(
            glob.glob(
                os.path.join(
                    python.package_folder,
                    "lib",
                    "python*",
                    "_sysconfigdata*.py",
                )
            )
        )
        if len(candidates) != 1:
            raise ConanInvalidConfiguration("target Python sysconfigdata not unique")
        variables = runpy.run_path(candidates[0]).get("build_time_vars", {})
        version = ".".join(str(python.ref.version).split(".")[:2])
        executable = os.path.join(
            python.package_folder, "bin", "python{}".format(version)
        )
        return {
            "version": version,
            "suffix": variables.get("EXT_SUFFIX"),
            "executable": executable,
        }

    def _verify_elf(self, extension, suffix):
        if not extension.endswith(suffix):
            raise ConanException("packaged extension does not use target EXT_SUFFIX")
        with open(extension, "rb") as stream:
            header = stream.read(20)
        if header[:4] != b"\x7fELF" or int.from_bytes(header[18:20], "little") != 183:
            raise ConanException("packaged extension is not an AArch64 ELF")
        readelf = self._readelf()
        self.run("{} -d {}".format(shlex.quote(readelf), shlex.quote(extension)))
        dynamic = subprocess.check_output([readelf, "-d", extension], text=True)
        symbols = subprocess.check_output([readelf, "-Ws", extension], text=True)
        for needed in (
            "libboost_python312.so",
            "libpython3.12.so.1.0",
            "libdouble-conversion.so",
        ):
            if needed not in dynamic:
                raise ConanException("missing DT_NEEDED entry: {}".format(needed))
        needed_entries = [
            line.split("[", 1)[1].split("]", 1)[0]
            for line in dynamic.splitlines()
            if "(NEEDED)" in line and "[" in line
        ]
        if any("/" in entry for entry in needed_entries):
            raise ConanException(
                "DT_NEEDED contains an absolute path: {}".format(needed_entries)
            )
        if "RPATH" in dynamic or "RUNPATH" in dynamic:
            raise ConanException("extension contains a build-machine runtime path")
        if "PyInit_minieigen" not in symbols:
            raise ConanException("extension does not export PyInit_minieigen")
        self.output.info("PASS: PyInit_minieigen is exported")
        if self.settings.os == "OHOS":
            self.run("{} -S {}".format(shlex.quote(readelf), shlex.quote(extension)))
            sections = subprocess.check_output([readelf, "-S", extension], text=True)
            if sections.count(".codesign") != 1:
                raise ConanException("extension must contain exactly one .codesign")

    def _verify_discovery_contract(self, extension, python, contract):
        """Prove that target import discovery is controlled by target EXT_SUFFIX."""
        probe_root = os.path.join(self.build_folder, "abi-contract-probe")
        wrong_dir = os.path.join(probe_root, "wrong-suffix")
        correct_dir = os.path.join(probe_root, "target-suffix")
        shutil.rmtree(probe_root, ignore_errors=True)
        os.makedirs(wrong_dir)
        os.makedirs(correct_dir)
        # This is the exact suffix observed from the Python 3.14 build
        # interpreter used by the upstream setup.py in Arm A.  Keep the
        # evidence stable across CI workers instead of deriving a different
        # foreign suffix from whichever interpreter happens to run Conan.
        wrong_suffix = ".cpython-314-x86_64-linux-gnu.so"
        wrong_extension = os.path.join(wrong_dir, "minieigen" + wrong_suffix)
        correct_extension = os.path.join(
            correct_dir, "minieigen" + contract["suffix"]
        )
        shutil.copy2(extension, wrong_extension)
        shutil.copy2(extension, correct_extension)
        wrong_digest = self._sha256(wrong_extension)
        correct_digest = self._sha256(correct_extension)
        if wrong_digest != correct_digest:
            raise ConanException("Arm B and Arm C must contain identical ELF bytes")
        probe = os.path.join(self.source_folder, "probe_import.py")
        wrong_result = self.run(
            self._python_command(python, contract, wrong_dir, probe),
            ignore_errors=True,
        )
        if wrong_result == 0:
            raise ConanException(
                "target Python unexpectedly discovered a foreign-ABI suffix"
            )
        self.run(self._python_command(python, contract, correct_dir, probe))
        self.output.info(
            "PASS: foreign build-interpreter suffix rejected; target EXT_SUFFIX loaded"
        )
        shutil.rmtree(probe_root, ignore_errors=True)

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _readelf(self):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise ConanInvalidConfiguration("readelf is required")
        return readelf

    def _runtime_libdirs(self):
        result = []
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                if libdir and libdir not in result:
                    result.append(libdir)
        extra = os.environ.get("MINIEIGEN_EXTRA_LD_LIBRARY_PATH", "")
        for path in extra.split(os.pathsep):
            if path and path not in result:
                result.append(path)
        return result

    def _python_command(self, python, contract, site, script=None):
        ld_library_path = os.pathsep.join(self._runtime_libdirs())
        script = script or os.path.join(self.source_folder, "test_minieigen.py")
        runner = os.environ.get("MINIEIGEN_TARGET_RUNNER", "").strip()
        if runner:
            return (
                "{} -E LD_LIBRARY_PATH={} -E PYTHONHOME={} -E PYTHONPATH={} {} {}"
            ).format(
                runner,
                shlex.quote(ld_library_path),
                shlex.quote(python.package_folder),
                shlex.quote(site),
                shlex.quote(contract["executable"]),
                shlex.quote(script),
            )
        return "LD_LIBRARY_PATH={} PYTHONHOME={} PYTHONPATH={} {} {}".format(
            shlex.quote(ld_library_path),
            shlex.quote(python.package_folder),
            shlex.quote(site),
            shlex.quote(contract["executable"]),
            shlex.quote(script),
        )

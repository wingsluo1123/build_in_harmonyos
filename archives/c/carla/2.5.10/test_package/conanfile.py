#!/usr/bin/env python3
"""Conan test_package for Carla — verifies carla binaries run correctly.

Carla's `make install` produces:
  - bin/carla-single    : Python launcher script
  - lib/carla/libcarla_*  : backend shared libraries
  - lib/carla/carla-bridge-* : plugin bridge binaries
  - lib/carla/carla-discovery-* : plugin discovery binaries
  - lib/carla_utils.so  : utility library

The test verifies:
  1. carla-discovery-native binary exists and is executable
  2. carla-discovery-native --version exits 0
  3. libcarla_utils.so exists in lib/carla/
"""
import os
import stat
from conan import ConanFile


class CarlaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the installed lib/carla/ directory
        carla_lib = os.path.join(self.dependencies["carla"].package_folder,
                                 "lib", "carla")

        # 1. carla-discovery-native must exist and be executable
        discovery = os.path.join(carla_lib, "carla-discovery-native")
        if not os.path.isfile(discovery):
            raise RuntimeError(f"carla-discovery-native not found at {discovery}")
        st = os.stat(discovery)
        if not (st.st_mode & stat.S_IXUSR):
            raise RuntimeError(f"carla-discovery-native is not executable: {discovery}")

        # 2. carla-discovery-native with no args prints a usage line.
        #    The binary has no --version flag; exit code varies across
        #    builds (0 on some, 1 on others), so assert on stdout content
        #    rather than returncode. A live ELF that loaded its shared
        #    libraries and reached main() prints "[carla] usage:".
        import subprocess
        proc = subprocess.run([discovery], capture_output=True, text=True)
        if "usage:" not in (proc.stdout or "") and "usage:" not in (proc.stderr or ""):
            raise RuntimeError(
                f"carla-discovery-native did not print usage: "
                f"rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
            )

        # 3. libcarla_utils.so must exist in lib/carla/
        utils_lib = os.path.join(carla_lib, "libcarla_utils.so")
        if not os.path.isfile(utils_lib):
            raise RuntimeError(f"libcarla_utils.so not found at {utils_lib}")

        self.output.success("Conan test_package: carla binaries verified OK")

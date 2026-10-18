#!/usr/bin/env python3
"""test_package — freerdp 3.26.0 on HarmonyOS PC (OHOS / arm64).

Two layers:

  1. a real consumer: test.cpp links against the packaged libraries and drives
     the WinPR event/unicode wrappers plus the FreeRDP context lifecycle.  The
     binary is run through Conan's VirtualRunEnv, which is what puts the
     package lib/ directory on LD_LIBRARY_PATH — with soname-carrying
     libraries that is enough for the OHOS loader to resolve them;
  2. a HarmonyOS-specific ELF gate that the recipe's soname adaptation exists
     for: every shared library shipped in lib/ must carry a relative
     DT_SONAME, and no DT_NEEDED entry may be an absolute path or a
     `../`-relative one.  Without the soname flag the OHOS build produces
     libwinpr3.so with no DT_SONAME and DT_NEEDED entries such as
     "winpr/libwinpr/libwinpr3.so", which this test rejects.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import load


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _tool(self, name):
        """Locate a binutils tool.

        Conan runs test_package with the profile buildenv, which on this device
        does not carry the SDK bin directory, so shutil.which() alone finds
        nothing even though `readelf' is installed; fall back to the known
        locations.
        """
        found = shutil.which(name)
        if found:
            return found
        for candidate in (f"/data/service/hnp/bin/{name}", f"/usr/bin/{name}",
                          f"/bin/{name}", f"/system/bin/{name}",
                          "/data/service/hnp/bin/llvm-" + name):
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(f"{name} not found; it is required for the ELF soname check")

    def _elf_report(self, so_file):
        out = subprocess.run([self._tool("readelf"), "-d", so_file],
                             capture_output=True, text=True)
        if out.returncode != 0:
            raise ConanException(f"readelf -d failed for {so_file}: {out.stderr}")
        return out.stdout

    def test(self):
        package_folder = self.dependencies["freerdp"].package_folder

        if can_run(self):
            binary = os.path.join(self.build_folder, "freerdp_consumer")
            stdout_file = os.path.join(self.build_folder, "consumer.out")
            self.run(f'"{binary}" > "{stdout_file}" 2>&1', env="conanrun")
            output = load(self, stdout_file)
            self.output.info(output)
            for marker in ("winpr event ok", "winpr unicode ok", "freerdp context ok",
                           "freerdp settings ok", "OK"):
                if marker not in output:
                    raise ConanException(f"consumer test output misses {marker!r}")
        else:
            self.output.info("cross build: running the consumer test is skipped")

        libdir = os.path.join(package_folder, "lib")
        shared = sorted(name for name in os.listdir(libdir)
                        if ".so" in name and os.path.isfile(os.path.join(libdir, name)))
        if not shared:
            raise ConanException(f"no shared library found in {libdir}")

        for name in shared:
            elf = self._elf_report(os.path.join(libdir, name))
            soname = re.search(r"\(SONAME\).*\[(.*)\]", elf)
            if not soname:
                raise ConanException(f"{name}: missing DT_SONAME (OHOS soname flag not injected)")
            if soname.group(1).startswith("/"):
                raise ConanException(f"{name}: DT_SONAME is absolute: {soname.group(1)}")
            for needed in re.findall(r"\(NEEDED\).*\[(.*)\]", elf):
                if needed.startswith("/") or needed.startswith("../") or "/" in needed:
                    raise ConanException(f"{name}: DT_NEEDED carries a path: {needed}")
            self.output.info(f"{name}: SONAME={soname.group(1)}")

        # musl has no pthread_cancel: libwinpr3 must not carry the symbol
        winpr = os.path.join(libdir, "libwinpr3.so")
        symbols = subprocess.run([self._tool("nm"), "-D", "--undefined-only", winpr],
                                 capture_output=True, text=True)
        if "pthread_cancel" in symbols.stdout:
            raise ConanException("libwinpr3.so still references pthread_cancel (musl has none)")

        for tool in ("winpr-makecert", "winpr-hash"):
            if not os.path.isfile(os.path.join(package_folder, "bin", tool)):
                raise ConanException(f"{tool} is missing from the package")

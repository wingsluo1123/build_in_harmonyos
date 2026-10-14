#!/usr/bin/env python3
"""Installed-package test for sxiv.

The test intentionally exercises the installed executable instead of a
library-only API.  `sxiv -v` follows the normal startup path far enough to
print the version and exit without opening an X display.  On OHOS the runtime
shared-library closure is staged and re-signed because prebuilt dependency
libraries may carry a signature that the target device does not trust.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class SxivTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = (
        "CMakeLists.txt",
        "test_sxiv.c",
        "test_sxiv_scaling.c",
        "ohos_x11_scaling.h",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("sxiv target consumers are not runnable")

        package = self.dependencies["sxiv"]
        binary = self._package_binary(package)
        test_binary = os.path.join(self.cpp.build.bindir, "test_sxiv")
        scaling_test = os.path.join(
            self.cpp.build.bindir, "test_sxiv_scaling"
        )
        version_output = os.path.join(self.build_folder, "sxiv-version.txt")

        if str(self.settings.os) == "OHOS":
            runtime_root = str(self._prepare_ohos_runtime())
            self._sign_ohos_elf(test_binary, force=True)
            self._sign_ohos_elf(scaling_test, force=True)
            self._sign_ohos_elf(binary, force=True)
            prefix = f'LD_LIBRARY_PATH="{runtime_root}" '
            self.run(
                f'{prefix}"{test_binary}" "{binary}"',
                env="conanrun",
            )
            self.run(f'"{scaling_test}"', env="conanrun")
            self.run(
                f'{prefix}"{binary}" -v > "{version_output}" 2>&1',
                env="conanrun",
            )
        else:
            self.run(f'"{test_binary}" "{binary}"', env="conanrun")
            self.run(f'"{scaling_test}"', env="conanrun")
            self.run(
                f'"{binary}" -v > "{version_output}" 2>&1',
                env="conanrun",
            )

        version = Path(version_output).read_text(
            encoding="utf-8", errors="replace"
        ).strip()
        if version != "sxiv 26":
            raise ConanException(f"unexpected sxiv version output: {version!r}")

    @staticmethod
    def _package_binary(package):
        bindirs = list(package.cpp_info.bindirs)
        if not bindirs:
            raise ConanException("sxiv package has no bindir")
        bindir = Path(bindirs[0])
        if not bindir.is_absolute():
            bindir = Path(package.package_folder, bindir)
        return str(bindir / "sxiv")

    def _prepare_ohos_runtime(self):
        """Materialize all dependency shared libraries into one staged tree."""
        runtime_root = Path(self.build_folder, "runtime-libs")
        if runtime_root.exists():
            shutil.rmtree(runtime_root)
        runtime_root.mkdir(parents=True, exist_ok=False)

        copied = 0
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            package_root = Path(dependency.package_folder).resolve(strict=True)
            lib_dirs = []
            for libdir in dependency.cpp_info.libdirs:
                candidate = Path(libdir)
                if not candidate.is_absolute():
                    candidate = Path(dependency.package_folder, libdir)
                if candidate.is_dir():
                    lib_dirs.append(candidate)
            # Several OHPCD packages expose their libraries without declaring
            # cpp_info.libdirs, so include the conventional locations too.
            for name in ("lib", "lib64"):
                candidate = package_root / name
                if candidate.is_dir() and candidate not in lib_dirs:
                    lib_dirs.append(candidate)

            for source_dir in lib_dirs:
                for entry in sorted(source_dir.iterdir(), key=lambda item: item.name):
                    if not (entry.name.endswith(".so") or ".so." in entry.name):
                        continue
                    source = entry.resolve(strict=True)
                    if not source.is_file() or source.is_symlink():
                        raise ConanException(
                            f"runtime library is not a regular file: {entry}"
                        )
                    try:
                        source.relative_to(package_root)
                    except ValueError as error:
                        raise ConanException(
                            f"runtime library escapes its package: {entry}"
                        ) from error
                    destination = runtime_root / entry.name
                    if destination.exists():
                        if not self._same_bytes(destination, source):
                            raise ConanException(
                                f"runtime library basename collision: {entry.name}"
                            )
                        continue
                    shutil.copy2(source, destination)
                    shutil.copymode(source, destination)
                    copied += 1

        if copied == 0:
            raise ConanException("OHOS runtime library closure is empty")
        for library in sorted(runtime_root.iterdir(), key=lambda item: item.name):
            self._sign_ohos_elf(str(library), force=True)
        return runtime_root

    @staticmethod
    def _same_bytes(left, right):
        if left.stat().st_size != right.stat().st_size:
            return False
        with left.open("rb") as left_stream, right.open("rb") as right_stream:
            while True:
                left_block = left_stream.read(1024 * 1024)
                right_block = right_stream.read(1024 * 1024)
                if left_block != right_block:
                    return False
                if not left_block:
                    return True

    @staticmethod
    def _tool(name, fallback):
        executable = shutil.which(name) or fallback
        if not os.path.isfile(executable):
            raise ConanException(f"required OHOS tool is missing: {name}")
        return executable

    def _sign_ohos_elf(self, path, force=False):
        """Replace the target-side signature of one ELF file."""
        signer = self._tool(
            "binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = self._tool("llvm-readelf", "/data/service/hnp/bin/llvm-readelf")
        objcopy = self._tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")

        sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        existing = sections.count(".codesign")
        if existing not in (0, 1):
            raise ConanException(f"ELF has an invalid .codesign count: {path}")
        if existing == 1 and not force:
            os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o755)
            return

        unsigned = f"{path}.unsigned"
        signed = f"{path}.signed"
        for candidate in (unsigned, signed):
            if os.path.lexists(candidate):
                raise ConanException(f"stale signing output exists: {candidate}")
        sign_input = path
        try:
            if existing == 1:
                shutil.copy2(path, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    check=True,
                    timeout=30,
                )
                sign_input = unsigned
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    sign_input,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                stdout=sys.stderr,
                timeout=60,
            )
            verified = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if verified.count(".codesign") != 1:
                raise ConanException(f"signed ELF has invalid .codesign: {path}")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(signed, path)
        finally:
            for candidate in (signed, unsigned):
                if os.path.lexists(candidate):
                    os.unlink(candidate)

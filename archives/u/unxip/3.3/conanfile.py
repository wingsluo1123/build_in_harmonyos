#!/usr/bin/env python3
"""Conan recipe for unxip 3.3.

unxip is a Swift command-line tool for extracting Xcode .xip archives.
Linux/OHOS builds use SwiftPM plus system-library module maps for zlib and
liblzma. The recipe records the currently blocking prerequisite explicitly:
the OHOS build worker needs a Swift 6 toolchain on PATH.
"""
import hashlib
import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class UnxipConan(ConanFile):
    name = "unxip"
    version = "3.3"
    description = "Fast Xcode XIP unarchiver"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/saagarjha/unxip"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("xz/5.6.2")
        self.requires("zlib-ng-compat/2.3.3")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        local_tarball = os.environ.get("UNXIP_TARBALL")
        expected_sha256 = self.conan_data["sources"]["sha256"]
        if local_tarball and os.path.isfile(local_tarball):
            with open(local_tarball, "rb") as f:
                actual_sha256 = hashlib.sha256(f.read()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ConanException(
                    f"UNXIP_TARBALL sha256 mismatch: expected {expected_sha256}, got {actual_sha256}"
                )
            with tarfile.open(local_tarball, "r:gz") as tf:
                try:
                    tf.extractall(self.source_folder, filter="data")
                except TypeError:
                    tf.extractall(self.source_folder)
            self._strip_single_root()
            return

        get(self, **self.conan_data["sources"], strip_root=True)

    def _strip_single_root(self):
        entries = [
            e for e in os.listdir(self.source_folder)
            if e not in ("conandata.yml", "conanfile.py")
        ]
        if len(entries) != 1:
            return
        root = os.path.join(self.source_folder, entries[0])
        if not os.path.isdir(root):
            return
        for name in os.listdir(root):
            os.replace(os.path.join(root, name), os.path.join(self.source_folder, name))
        os.rmdir(root)

    def _dependency_flags(self):
        swift_flags = []
        lib_flags = []
        for rel in ("Sources/GNUSource", "Sources/getopt", "Sources/lzma", "Sources/zlib"):
            include_dir = os.path.join(self.source_folder, rel)
            swift_flags.extend(["-Xswiftc", "-Xcc", "-Xswiftc", f"-I{include_dir}"])
        for dep_name in ("libxml2", "xz", "zlib-ng-compat"):
            cpp_info = self.dependencies[dep_name].cpp_info
            for include_dir in cpp_info.includedirs:
                swift_flags.extend(["-Xswiftc", "-Xcc", "-Xswiftc", f"-I{include_dir}"])
            for lib_dir in cpp_info.libdirs:
                lib_flags.extend(["-Xlinker", f"-L{lib_dir}"])
        return swift_flags + lib_flags

    def _prepare_swift_sources(self):
        lib_source = os.path.join(self.source_folder, "Sources", "libunxip", "libunxip.swift")
        top_source = os.path.join(self.source_folder, "unxip.swift")
        if (os.path.islink(lib_source) or not os.path.isfile(lib_source)) and os.path.isfile(top_source):
            os.makedirs(os.path.dirname(lib_source), exist_ok=True)
            if os.path.lexists(lib_source):
                os.remove(lib_source)
            shutil.copyfile(top_source, lib_source)

        for rel in (
            os.path.join("Sources", "getopt", "getopt.h"),
            os.path.join("Sources", "lzma", "lzma.h"),
            os.path.join("Sources", "zlib", "zlib.h"),
        ):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                self._replace_once(path, "#include <", "#include_next <")

        for path in (top_source, lib_source):
            if os.path.isfile(path):
                self._patch_swift6_continuations(path)

    def _replace_once(self, path, old, new):
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        patched = data.replace(old, new, 1)
        if patched != data:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(patched)

    def _patch_swift6_continuations(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        patched = data
        patched = patched.replace(
            "await withCheckedContinuation {\n\t\t\t\t\tstate = .waiting($0)",
            "await withCheckedContinuation(isolation: self) {\n\t\t\t\t\tstate = .waiting($0)",
            1,
        )
        patched = patched.replace(
            "try await withCheckedThrowingContinuation { continuation in\n\t\t\t\t\tqueued.append(continuation)",
            "try await withCheckedThrowingContinuation(isolation: self) { continuation in\n\t\t\t\t\tqueued.append(continuation)",
            1,
        )
        patched = patched.replace(
            "try await withCheckedThrowingContinuation { continuation in\n\t\t\t\tqueued.append(continuation)",
            "try await withCheckedThrowingContinuation(isolation: self) { continuation in\n\t\t\t\tqueued.append(continuation)",
            1,
        )
        if patched != data:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(patched)

    def build(self):
        swift = shutil.which("swift")
        if not swift:
            raise ConanException(
                "Swift 6 toolchain not found on PATH; unxip cannot be built before "
                "a Swift toolchain is installed/provided for the OHOS worker."
            )

        self._prepare_swift_sources()

        cmd = [
            swift,
            "build",
            "--configuration",
            "release",
        ]
        if self.settings.os == "OHOS":
            cmd.extend([
                "--triple",
                self._ohos_swift_triple(),
                "--disable-index-store",
                "-j",
                os.environ.get("UNXIP_SWIFTPM_JOBS", "1"),
            ])
        else:
            cmd.extend([
                "--static-swift-stdlib",
                "-Xswiftc",
                "-use-ld=ld",
            ])
        cmd += ["-Xswiftc", "-parse-as-library"] + self._dependency_flags()
        cmd += shlex.split(os.environ.get("UNXIP_SWIFT_BUILD_EXTRA_FLAGS", ""))
        self.run(" ".join(f'"{arg}"' if " " in arg else arg for arg in cmd), cwd=self.source_folder)

    def _ohos_swift_triple(self):
        override = os.environ.get("UNXIP_SWIFT_TRIPLE")
        if override:
            return override
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.3", "armv8.4", "aarch64"):
            return "aarch64-unknown-linux-ohos"
        raise ConanInvalidConfiguration(f"Unsupported OHOS Swift arch: {arch}")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        built = self._find_unxip_binary()
        if not built:
            raise ConanException("Built unxip binary not found under .build")
        copy(self, "unxip", src=os.path.dirname(built), dst=bin_dir)
        self._sign_elf(os.path.join(bin_dir, "unxip"))

    def _find_unxip_binary(self):
        build_root = os.path.join(self.source_folder, ".build")
        for root, _, files in os.walk(build_root):
            if "unxip" in files and root.endswith("release"):
                candidate = os.path.join(root, "unxip")
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _sign_elf(self, path):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.warning("ELF signing tools not found; skipping local signing.")
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False, timeout=10)
        tmp = path + ".signed.tmp"
        result = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0 or not os.path.exists(tmp):
            raise ConanException(f"ELF signing failed for {path}")
        os.replace(tmp, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

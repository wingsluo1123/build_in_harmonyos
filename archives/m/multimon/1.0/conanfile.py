#!/usr/bin/env python3
"""Conan recipe for multimon 1.0 on HarmonyOS PC."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MultimonConan(ConanFile):
    name = "multimon"
    version = "1.0"
    description = "Decoder and signal generator for radio transmission formats"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/multimon/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("radio", "decoder", "dtmf", "pcm")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("This multimon recipe targets OHOS only")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _compiler(self):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return configured.get("c", "clang")

    def _dependency_flags(self):
        includes = []
        libdirs = []
        libs = []
        for dependency in self.dependencies.host.values():
            includes.extend(dependency.cpp_info.includedirs)
            libdirs.extend(dependency.cpp_info.libdirs)
            libs.extend(dependency.cpp_info.libs)
        cflags = [f"-I{path}" for path in dict.fromkeys(includes)]
        ldflags = [f"-L{path}" for path in dict.fromkeys(libdirs)]
        ldflags.extend(f"-l{name}" for name in dict.fromkeys(libs))
        return cflags, ldflags

    def build(self):
        apply_conandata_patches(self)
        cflags, x11_flags = self._dependency_flags()
        mapped_root = "/usr/src/multimon-1.0"
        cflags.extend(
            [
                "-O2",
                "-Wall",
                "-Wstrict-prototypes",
                "-std=gnu11",
                f"-ffile-prefix-map={self.source_folder}={mapped_root}",
                f"-fmacro-prefix-map={self.source_folder}={mapped_root}",
                f"-ffile-prefix-map={self.build_folder}={mapped_root}",
                f"-fmacro-prefix-map={self.build_folder}={mapped_root}",
            ]
        )
        compiler = self._compiler()
        host_compiler = shutil.which("cc") if cross_building(self) else compiler
        if not host_compiler:
            raise ConanException("build-machine C compiler not found")
        command = [
            "make",
            "-j1",
            f"CC={compiler}",
            f"AS={compiler}",
            f"HOSTCC={host_compiler}",
            "HOSTCFLAGS=-O2",
            "BINDIR=bin-ohos",
            "CFLAGS=" + " ".join(cflags),
            "LDFLAGS=-lm",
            "LDFLAGSX=" + " ".join(x11_flags),
        ]
        with VirtualBuildEnv(self).vars().apply():
            self.run(shlex.join(command), cwd=self.source_folder)

    def package(self):
        binary_dir = os.path.join(self.source_folder, "bin-ohos")
        for name in ("multimon", "gen"):
            destination = os.path.join(self.package_folder, "bin", name)
            copy(self, name, src=binary_dir, dst=os.path.dirname(destination), keep_path=False)
            self._sign_elf(destination)

    def _tool_candidates(self, name):
        executable = shutil.which(name)
        if executable:
            yield executable
        compiler = Path(self._compiler()).resolve()
        yield str(compiler.parent / name)
        if len(compiler.parents) >= 4:
            yield str(compiler.parents[3] / "toolchains" / "lib" / name)

    def _find_tool(self, name):
        for candidate in self._tool_candidates(name):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanException(f"required OHOS tool not found: {name}")

    def _sign_elf(self, binary):
        objcopy = self._find_tool("llvm-objcopy")
        strip = self._find_tool("llvm-strip")
        readelf = self._find_tool("llvm-readelf")
        signer = self._find_tool("binary-sign-tool")
        subprocess.run([strip, "--strip-debug", binary], check=True)
        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=True)
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
            capture_output=True,
            text=True,
        )
        sections = subprocess.run(
            [readelf, "-SW", binary], capture_output=True, text=True, check=True
        ).stdout
        dynamic = subprocess.run(
            [readelf, "-d", binary], capture_output=True, text=True, check=True
        ).stdout
        data = Path(binary).read_bytes()
        forbidden = (b".conan2", b"/storage/Users/", b"/home/")
        if result.returncode != 0 or sections.count(".codesign") != 1:
            raise ConanException("failed to sign packaged ELF: " + (result.stderr or result.stdout))
        if "RPATH" in dynamic or "RUNPATH" in dynamic:
            raise ConanException(f"packaged ELF contains RPATH/RUNPATH: {binary}")
        if any(marker in data for marker in forbidden):
            raise ConanException(f"packaged ELF contains a build-host path: {binary}")
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

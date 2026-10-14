#!/usr/bin/env python3
"""Conan test_package — sng 1.1.1 (consumer flow).

1. build(): compile ``check_png.c`` against libpng (the consumer program).
2. test():  run the packaged ``sng`` to compile ``sample.sng`` into a PNG,
            let the consumer program decode that PNG with libpng and verify
            geometry / palette / pixels / tEXt, then decompile the PNG again,
            recompile the text and verify the round trip.  The palette uses
            X11 colour *names*, so the run also proves the packaged
            ``share/X11/rgb.txt`` is found by the baked-in RGBTXT path.
"""
import os
import platform
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv

_HERE = os.path.dirname(os.path.abspath(__file__))


class SngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libpng/1.6.58.3")

    def layout(self):
        # keep build products (consumer binary, PNGs) out of the recipe folder
        self.folders.build = "build"
        self.folders.generators = "build/generators"

    def generate(self):
        VirtualRunEnv(self).generate()

    # ------------------------------------------------------------------ #
    def _c_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        compiler = executables.get("c") or shutil.which("cc")
        resolved = shutil.which(compiler) if compiler else None
        if not resolved:
            raise ConanInvalidConfiguration("No C compiler is configured")
        return resolved

    def _sign_elf(self, path):
        """OHOS kernel refuses to execute unsigned ELF files."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            subprocess.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true',
                           shell=True, check=False)
            subprocess.run([sign_tool, "sign", "-inFile", path, "-outFile", path,
                            "-selfSign", "1"], check=True)

    def build(self):
        incs, libdirs, libs = [], [], []
        for name in ("libpng", "zlib"):
            dep = self.dependencies[name].cpp_info
            incs += ["-I" + p for p in dep.includedirs]
            libdirs += ["-L" + p for p in dep.libdirs]
            libs += ["-l" + lib for lib in dep.libs]
            libs += ["-l" + lib for lib in dep.system_libs]
        rpath = "-Wl,-rpath," + self.dependencies["libpng"].cpp_info.libdirs[0]
        src = os.path.join(_HERE, "check_png.c")
        out = os.path.join(self.build_folder, "check_png")
        command = [self._c_compiler(), src, "-o", out,
                   *dict.fromkeys(incs + libdirs + libs), rpath]
        self.run(shlex.join(command))
        self._sign_elf(out)

    # ------------------------------------------------------------------ #
    def _sng(self, bindir, stdin, stdout):
        return self.run(f'"{os.path.join(bindir, "sng")}" < "{stdin}" > "{stdout}"',
                        env="conanrun", ignore_errors=True)

    def test(self):
        dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        bindir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        sng = os.path.join(bindir, "sng")
        rgb = os.path.join(dep.package_folder, "share", "X11", "rgb.txt")
        # L1e negative check: fails if the package under test is sabotaged.
        assert os.path.isfile(sng), f"sng not found at {sng}"
        assert os.path.isfile(rgb), f"packaged rgb.txt not found at {rgb}"

        work = self.build_folder
        sample = os.path.join(_HERE, "sample.sng")
        png1 = os.path.join(work, "out1.png")
        txt = os.path.join(work, "back.sng")
        png2 = os.path.join(work, "out2.png")
        check = os.path.join(work, "check_png")

        # 1. sng compiles sample.sng -> PNG
        if self._sng(bindir, sample, png1) != 0:
            machine = platform.machine().lower()
            native = {"armv8": ("aarch64", "arm64"),
                      "x86_64": ("x86_64", "amd64")}.get(str(self.settings.arch), ())
            if machine in native:
                raise ConanException("sng failed to compile sample.sng on a native machine")
            self.output.warning(
                f"[SKIP] runtime checks: this {machine} build machine cannot execute "
                f"the {self.settings.arch} target binaries (consumer program was "
                "compiled and linked).")
            return
        with open(png1, "rb") as fh:
            assert fh.read(8) == b"\x89PNG\r\n\x1a\n", "sng output is not a PNG"

        # 2. consumer program (libpng) validates what sng wrote
        self.run(f'"{check}" "{png1}"', env="conanrun")

        # 3. decompile again: palette from rgb.txt names, geometry, tEXt
        assert self._sng(bindir, png1, txt) == 0, "sng failed to decompile its own PNG"
        with open(txt, encoding="utf-8") as fh:
            flat = re.sub(r"\s+", "", fh.read())
        for needle in ("(255,0,0)", "(47,79,79)", "(255,215,0)", "(0,0,255)",
                       "width:4;height:2;", 'keyword:"Title"', 'text:"ohos-consumer"'):
            assert needle in flat, f"decompiled text lacks {needle}"

        # 4. recompile the decompiled text: the round trip still validates
        assert self._sng(bindir, txt, png2) == 0, "sng failed to recompile text"
        self.run(f'"{check}" "{png2}"', env="conanrun")

        # 5. error path: a non-SNG, non-PNG input is rejected
        junk = os.path.join(work, "junk.bin")
        with open(junk, "wb") as fh:
            fh.write(b"this is not an image\n")
        assert self._sng(bindir, junk, os.path.join(work, "junk.out")) != 0, \
            "sng accepted garbage input"

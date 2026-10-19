#!/usr/bin/env python3
"""Installed-package consumer test for libwraster 0.96.0.

Two layers run against the installed package:

* ``libwraster_test`` (test.c) -- API level checks of the X11-free core.
* ``libwraster_consumer`` (consumer.c) -- an end-to-end consumer that runs the
  real dockapp icon flow (construct -> scale -> shape) and writes a genuine
  XPM artefact with the library's own writer plus a pixel report.

``test()`` then reads that artefact back with the independent XPM reader below,
compares it with the in-memory image the consumer read through RGetPixel, and
checks both against the deterministic input specification of the consumer.  The
consumer is run twice so a non-deterministic pipeline cannot pass.
"""

import hashlib
import os
import pathlib
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

# Input specification of the consumer (see test_package/consumer.c).
ICON_SIZE = 8
# Interior blocks of the four quadrants of the scaled icon: the flat colour of
# each master quadrant must survive the 4x4 -> 8x8 scaling in its own quadrant.
QUADRANT_CORES = (
    ((1, 2), (1, 2), (255, 0, 0, 255)),      # red   -- top left
    ((5, 6), (1, 2), (0, 255, 0, 255)),      # green -- top right
    ((1, 2), (5, 6), (0, 0, 255, 255)),      # blue  -- bottom left
    ((5, 6), (5, 6), (255, 255, 255, 255)),  # white -- bottom right
)
TRANSPARENT_WINDOW = ((3, 3), (3, 4), (4, 3), (4, 4))
PALETTE = {
    (255, 0, 0, 255),
    (0, 255, 0, 255),
    (0, 0, 255, 255),
    (255, 255, 255, 255),
    (0, 0, 0, 0),
}
XPM_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_xpm(path):
    """Read an XPM file produced by libwraster (independent implementation).

    Returns ``(width, height, grid)`` with ``grid[y][x]`` a ``(r, g, b, a)``
    tuple; transparent pixels of a ``None`` entry decode to alpha 0.
    """
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    strings = re.findall(r'"([^"]*)"', re.sub(r"/\*.*?\*/", "", text, flags=re.S))
    fields = strings[0].split() if strings else []
    if len(fields) != 4 or not all(field.isdigit() for field in fields):
        raise ConanException(f"{path}: not a usable XPM artefact (header: {strings[:1]})")
    width, height, ncolors, cpp = (int(field) for field in fields)
    if len(strings) < 1 + ncolors + height:
        raise ConanException(
            f"{path}: truncated XPM ({len(strings)} strings, expected {1 + ncolors + height})"
        )

    symbols = {}
    for entry in strings[1:1 + ncolors]:
        tokens = entry[cpp:].split()
        if len(tokens) != 2 or tokens[0] != "c":
            raise ConanException(f"{path}: malformed colour entry {entry!r}")
        value = tokens[1]
        if value.lower() == "none":
            symbols[entry[:cpp]] = (0, 0, 0, 0)
        elif XPM_COLOR.match(value):
            symbols[entry[:cpp]] = (
                int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 255,
            )
        else:
            raise ConanException(f"{path}: unsupported colour value {value!r}")

    grid = []
    for y, row in enumerate(strings[1 + ncolors:1 + ncolors + height]):
        if len(row) != width * cpp:
            raise ConanException(f"{path}: row {y} has {len(row)} chars, expected {width * cpp}")
        grid.append([symbols[row[x * cpp:(x + 1) * cpp]] for x in range(width)])
    return width, height, grid


def decode_report(path):
    """Parse the pixel report the consumer wrote out of RGetPixel()."""
    width = height = None
    rows = {}
    for line in pathlib.Path(path).read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "icon-size" and len(fields) == 3:
            width, height = int(fields[1]), int(fields[2])
        elif fields[0] == "row" and len(fields) >= 2:
            pixels = fields[2:]
            if any(len(pixel) != 8 for pixel in pixels):
                raise ConanException(f"{path}: malformed pixel dump in {line!r}")
            rows[int(fields[1])] = [
                tuple(int(pixel[i:i + 2], 16) for i in (0, 2, 4, 6)) for pixel in pixels
            ]
    if width is None or height is None:
        raise ConanException(f"{path}: missing icon-size line")
    if sorted(rows) != list(range(height)):
        raise ConanException(f"{path}: expected rows 0..{height - 1}, got {sorted(rows)}")
    grid = [rows[y] for y in range(height)]
    for y, row in enumerate(grid):
        if len(row) != width:
            raise ConanException(f"{path}: row {y} has {len(row)} pixels, expected {width}")
    return width, height, grid


class LibwrasterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test.c", "consumer.c"

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
            raise ConanException("libwraster target consumer is not runnable")

        checks = os.path.join(self.cpp.build.bindir, "libwraster_test")
        consumer = os.path.join(self.cpp.build.bindir, "libwraster_consumer")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(checks)
            self._sign_ohos_elf(consumer)

        self.run(checks, env="conanrun")
        self._run_consumer_end_to_end(consumer)

    def _run_consumer_end_to_end(self, consumer):
        """Run the consumer twice, then check artefact, memory image and spec."""
        outputs = []
        for tag in ("a", "b"):
            outdir = os.path.join(self.build_folder, f"consumer-out-{tag}")
            os.makedirs(outdir, exist_ok=True)
            self.run(f'"{consumer}" "{outdir}"', env="conanrun")
            outputs.append(outdir)

        artefact = os.path.join(outputs[0], "dockapp-icon.xpm")
        repeat = os.path.join(outputs[1], "dockapp-icon.xpm")
        report = os.path.join(outputs[0], "consumer-report.txt")

        digest = sha256_of(artefact)
        size = os.path.getsize(artefact)
        self.output.info(f"consumer artefact: {artefact} ({size} bytes, sha256 {digest})")

        memory_width, memory_height, memory = decode_report(report)
        xpm_width, xpm_height, xpm = decode_xpm(artefact)

        if (memory_width, memory_height) != (ICON_SIZE, ICON_SIZE):
            raise ConanException(
                f"consumer built a {memory_width}x{memory_height} icon, expected "
                f"{ICON_SIZE}x{ICON_SIZE}"
            )
        if (xpm_width, xpm_height) != (memory_width, memory_height):
            raise ConanException(
                f"artefact is {xpm_width}x{xpm_height} but the in-memory image is "
                f"{memory_width}x{memory_height}"
            )
        if xpm != memory:
            for y, (from_xpm, from_memory) in enumerate(zip(xpm, memory)):
                if from_xpm != from_memory:
                    raise ConanException(
                        f"artefact row {y} disagrees with the in-memory image:\n"
                        f"  xpm    {from_xpm}\n  memory {from_memory}"
                    )
            raise ConanException("artefact and in-memory image differ")

        for xs, ys, colour in QUADRANT_CORES:
            for x in xs:
                for y in ys:
                    if xpm[y][x] != colour:
                        raise ConanException(
                            f"quadrant core pixel ({x},{y}) is {xpm[y][x]}, expected {colour}"
                        )
        for x, y in TRANSPARENT_WINDOW:
            if xpm[y][x] != (0, 0, 0, 0):
                raise ConanException(
                    f"shaped window pixel ({x},{y}) is {xpm[y][x]}, expected transparency"
                )
        for y, row in enumerate(xpm):
            for x, pixel in enumerate(row):
                if pixel not in PALETTE:
                    raise ConanException(
                        f"unexpected colour {pixel} at ({x},{y}): the consumer only draws "
                        f"the four specification colours and transparency"
                    )

        repeat_digest = sha256_of(repeat)
        if repeat_digest != digest:
            raise ConanException(
                f"consumer pipeline is not deterministic: {digest} vs {repeat_digest}"
            )

        self.output.info(
            "end-to-end consumer OK: 8x8 shaped dock icon, "
            f"{len(PALETTE) - 1} colours + transparent window, artefact matches the "
            "in-memory image and is byte identical across 2 runs"
        )

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        signed = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", signed],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(signed, path)

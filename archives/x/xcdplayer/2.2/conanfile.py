#!/usr/bin/env python3
"""Conan recipe for xcdplayer 2.2 - X11 CD player (X11R5 contrib, 1993).

xcdplayer is a small X11/Xaw (Athena widgets) CD player.  Upstream ships an
Imakefile (imake-based, Sun/SGI CD-ROM backends only); this recipe builds it
with a generated POSIX Makefile against Conan-provided X11 libraries.

Porting notes (see patches/xcdplayer-2.2-ohos.patch)
---------------------------------------------------
- Upstream only has cdrom_sun.c / cdrom_sgi.c backends.  A Linux CD-ROM backend
  (cdrom_linux.c/.h, linux/cdrom.h ioctls) is added, adapted from the same
  author's later upstream release xcdplayer 2.3a (its cdrom_linux.c), reworked
  to 2.2's interfaces (char *disc_title, no cdInfoDir struct changes).
- The K&R-era `(Cardinal) &global` XtResource offsets cannot be folded into
  static initializers by modern compilers; the resource table is now built at
  run time inside top_setup() (behaviour unchanged: base=NULL, offsets are the
  absolute addresses of the target globals).
- <varargs.h> debug_printf() rewritten with <stdarg.h>.
- The X11/bitmaps/gray stipple is vendored as gray.bm (xbitmaps is not
  published on the ohpcd artifact remote); the 2x2 canonical bitmap is copied
  verbatim from xbitmaps 1.1.3.
- cdgrab.c is a Sun-only raw-SCSI diagnostic (upstream never ported it to
  Linux either, even in 2.3a); it is not built.  cdinfo.c is ported and built.

Source note
-----------
Upstream only publishes ``xcdplayer-2.2.tar.Z`` (compress(1) LZW container,
mirrored on ftp.gwdg.de's ftp.x.org tree -- sha256 matches the FreeBSD ports
distinfo for audio/xcdplayer).  The legacy ``.Z`` stream is decoded with a
small pure-Python LZW decoder (see :func:`unlzw`); Conan's ``unzip`` helper
does not understand the ``.Z`` format.
"""
import io
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


def unlzw(inp) -> bytes:
    """Decompress a ``compress(1)`` (``.Z``) LZW stream.

    Adapted for Python from Mark Adler's C implementation
    (https://github.com/umeat/unlzw, via scivision/unlzw3).  Python's standard
    library has no ``.Z`` support and Conan's ``unzip`` helper only understands
    gzip/bzip2/xz/zip, so the legacy LZW container is decoded here.

    Copyright (C) 2014, 2015 Mark Adler
    This software is provided 'as-is', without any express or implied warranty.
    In no event will the authors be held liable for any damages arising from the
    use of this software.  Permission is granted to anyone to use this software
    for any purpose, including commercial applications, and to alter it and
    redistribute it freely, subject to the following restrictions:
    1. The origin of this software must not be misrepresented; you must not
       claim that you wrote the original software.
    2. Altered source versions must be plainly marked as such, and must not be
       misrepresented as being the original software.
    3. This notice may not be removed or altered from any source distribution.
    Mark Adler <madler@alumni.caltech.edu>
    """
    if isinstance(inp, bytes):
        data = inp
    else:
        data = inp

    ba_in = bytearray(data)
    inlen = len(ba_in)
    prefix = [0] * 65536
    suffix = [0] * 65536

    if inlen < 3:
        raise ValueError("Invalid Input: Length of input too short for processing")
    if (ba_in[0] != 0x1F) or (ba_in[1] != 0x9D):
        raise ValueError("Invalid Header Flags Byte: Incorrect magic bytes")

    flags = ba_in[2]
    if flags & 0x60:
        raise ValueError("Invalid Header Flags Byte: Flag byte contains invalid data")
    max_ = flags & 0x1F
    if (max_ < 9) or (max_ > 16):
        raise ValueError("Invalid Header Flags Byte: Max code size bits out of range")
    if max_ == 9:
        max_ = 10

    flags &= 0x80
    bits = 9
    mask = 0x1FF
    end = 256 if flags else 255

    if inlen == 3:
        return b""
    if inlen == 4:
        raise ValueError("Invalid Data: Stream ended in the middle of a code")

    buf = ba_in[3]
    buf += ba_in[4] << 8
    final = prev = buf & mask
    buf >>= bits
    left = 16 - bits
    if prev > 255:
        raise ValueError("Invalid Data: First code must be a literal")

    put = [final]
    mark = 3
    nxt = 5
    while nxt < inlen:
        if (end >= mask) and (bits < max_):
            rem = (nxt - mark) % bits
            if rem:
                rem = bits - rem
                if rem >= inlen - nxt:
                    break
                nxt += rem
            buf = 0
            left = 0
            mark = nxt
            bits += 1
            mask <<= 1
            mask += 1

        buf += ba_in[nxt] << left
        nxt += 1
        left += 8
        if left < bits:
            if nxt == inlen:
                raise ValueError("Invalid Data: Stream ended in the middle of a code")
            buf += ba_in[nxt] << left
            nxt += 1
            left += 8
        code = buf & mask
        buf >>= bits
        left -= bits

        if (code == 256) and flags:
            rem = (nxt - mark) % bits
            if rem:
                rem = bits - rem
                if rem > inlen - nxt:
                    break
                nxt += rem
            buf = 0
            left = 0
            mark = nxt
            bits = 9
            mask = 0x1FF
            end = 255
            continue

        temp = code
        stack = []
        if code > end:
            if (code != end + 1) or (prev > end):
                raise ValueError("Invalid Data: Invalid code detected")
            stack.append(final)
            code = prev
        while code >= 256:
            stack.append(suffix[code])
            code = prefix[code]
        stack.append(code)
        final = code
        if end < mask:
            end += 1
            prefix[end] = prev
            suffix[end] = final
        prev = temp
        put += stack[::-1]

    return bytes(bytearray(put))


# explicit link order, most specific first (mirrors upstream XawClientLibs)
LINK_LIBS = ["Xaw", "Xmu", "Xt", "Xpm", "Xext", "X11", "SM", "ICE",
             "X11-xcb", "xcb", "Xau", "Xdmcp"]

# SONAME prefixes needed at run time by the prebuilt X11 stack, in dependency
# order (used by the test_package LD_PRELOAD fallback; see xeyes precedent)
RUNTIME_SOS = [("libxau", "libXau.so.6"),
               ("libxdmcp", "libXdmcp.so.6"),
               ("libxcb", "libxcb.so.1"),
               ("libice", "libICE.so.6"),
               ("libsm", "libSM.so.6"),
               ("libx11", "libX11.so.6"),
               ("libxext", "libXext.so.6"),
               ("libxt", "libXt.so.6"),
               ("libxmu", "libXmu.so.6"),
               ("libxpm", "libXpm.so.4"),
               ("libxaw", "libXaw.so.7")]


class XcdplayerConan(ConanFile):
    name = "xcdplayer"
    version = "2.2"
    description = ("xcdplayer: X11/Athena CD player from the X11R5 contrib "
                   "distribution, with a Linux CD-ROM backend")
    license = "LicenseRef-XCdplayer-Berkeley"
    homepage = "https://www.x.org/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # libXaw pulls in libXmu/libXt/libX11/libXext/libxcb/... transitively
        # (libxaw/1.0.14 pins libx11/1.8.13 on the ohpcd remote)
        self.requires("libxaw/1.0.14")
        self.requires("libxpm/3.5.17")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xcdplayer OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        src = self.conan_data["sources"]
        filename = "xcdplayer-2.2.tar.Z"
        download(self, src["url"], filename, sha256=src["sha256"])
        try:
            with open(os.path.join(self.source_folder, filename), "rb") as fh:
                raw = fh.read()
            tar_bytes = unlzw(raw)
        finally:
            path = os.path.join(self.source_folder, filename)
            if os.path.isfile(path):
                os.unlink(path)
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tf:
            tf.extractall(self.source_folder)
        top = os.path.join(self.source_folder, "xcdplayer-2.2")
        for name in os.listdir(top):
            shutil.move(os.path.join(top, name),
                        os.path.join(self.source_folder, name))
        os.rmdir(top)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _dep_dirs(self):
        """Collect -I and -L paths from all host dependencies."""
        incs, libs = [], []
        for dep in self.dependencies.values():
            cpp = dep.cpp_info.aggregated_components()
            for d in cpp.includedirs:
                if d not in incs:
                    incs.append(d)
            for d in cpp.libdirs:
                if d not in libs:
                    libs.append(d)
            for d in cpp.srcdirs:
                pass
        return incs, libs

    def build(self):
        apply_conandata_patches(self)
        for f in ("main.c", "cdrom_linux.c", "logo_setup.c"):
            if not os.path.isfile(os.path.join(self.source_folder, f)):
                raise ConanInvalidConfiguration(
                    "source tree is missing %s" % f)
        cc = self._compiler("c", "clang")
        incs, libdirs = self._dep_dirs()
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        cflags = "-Wall " + opt + "".join(" -I%s" % d for d in incs)
        ldflags = "".join(" -L%s" % d for d in libdirs) + \
            "".join(" -l%s" % l for l in LINK_LIBS)
        makefile = """# Generated by conanfile.py (OHOS port); upstream uses Imakefile.
CC = {cc}
CFLAGS = {cflags}
LDFLAGS = {ldflags}
OBJS = main.o top_setup.o logo_setup.o button_setup.o cdrom_callb.o \\
       cdrom_linux.o internals.o shuffle.o program.o leds.o debug.o

all: xcdplayer cdinfo

xcdplayer: $(OBJS)
\t$(CC) -o $@ $(OBJS) $(LDFLAGS)

cdinfo: cdinfo.o
\t$(CC) -o $@ cdinfo.o

%.o: %.c
\t$(CC) $(CFLAGS) -c $<

clean:
\trm -f $(OBJS) xcdplayer cdinfo
""".format(cc=cc, cflags=cflags, ldflags=ldflags)
        with open(os.path.join(self.source_folder, "Makefile.ohos"), "w") as fh:
            fh.write(makefile)
        self.run("make -f Makefile.ohos -j1", cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "xcdplayer")):
            raise ConanInvalidConfiguration(
                "build did not produce the 'xcdplayer' program")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        appdefs = os.path.join(self.package_folder, "share", "X11", "app-defaults")
        copy(self, "xcdplayer", self.source_folder, bindir)
        os.chmod(os.path.join(bindir, "xcdplayer"), 0o755)
        copy(self, "cdinfo", self.source_folder, bindir)
        os.chmod(os.path.join(bindir, "cdinfo"), 0o755)
        copy(self, "xcdplayer.1", self.source_folder, mandir)
        copy(self, "XCdplayer.ad", self.source_folder, appdefs)
        os.rename(os.path.join(appdefs, "XCdplayer.ad"),
                  os.path.join(appdefs, "XCdplayer"))
        copy(self, "copyright.h", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

#!/usr/bin/env python3
"""Conan recipe for qpage 3.3 - QuickPage SNPP/IXO paging client and server.

QuickPage (by Thomas Dwyer III) sends messages to alpha-numeric pagers over the
SNPP protocol (RFC 1861) and IXO/TAP.  It is a small, dependency-free C program
(~10 translation units) built by an autoconf-2.12 generated ``configure`` plus a
hand-written ``Makefile``.

Source note
-----------
Upstream only publishes ``qpage-3.3.tar.Z`` (plain-HTTP qpage.org / tomiii.com),
which the repository rules forbid.  This recipe fetches the byte-identical
distfile from the NetBSD pkgsrc distfiles mirror (``ftp.jaist.ac.jp``, an
allow-listed HTTPS host) and decompresses the legacy ``compress(1)`` LZW stream
with a small pure-Python decoder (see :func:`unlzw`); Conan's ``unzip`` helper
does not understand the ``.Z`` format.

There is no upstream test suite, so ``test_package/`` runs the installed client
against a local mock SNPP server and checks the on-the-wire command sequence.
"""
import io
import os
import shutil
import tarfile
from pathlib import Path

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
    if isinstance(inp, Path):
        data = inp.read_bytes()
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


class QpageConan(ConanFile):
    name = "qpage"
    version = "3.3"
    description = "QuickPage: SNPP/IXO paging client and server for alpha-numeric pagers"
    license = "LicenseRef-Qpage-NonCommercial"
    homepage = "http://www.qpage.org/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qpage OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        src = self.conan_data["sources"]
        filename = "qpage-3.3.tar.Z"
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
        top = os.path.join(self.source_folder, "qpage-3.3")
        for name in os.listdir(top):
            shutil.move(os.path.join(top, name), os.path.join(self.source_folder, name))
        os.rmdir(top)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isfile(os.path.join(self.source_folder, "qpage.c")):
            raise ConanInvalidConfiguration("source tree is missing qpage.c")
        cc = self._compiler("c", "clang")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        self.run('CC="{}" CFLAGS="-Wall {}" sh ./configure --prefix="{}"'.format(
            cc, opt, self.package_folder), cwd=self.source_folder)
        self.run('make CC="{}" CFLAGS="-Wall {}" -j1'.format(cc, opt),
                 cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "qpage")):
            raise ConanInvalidConfiguration("build did not produce the 'qpage' program")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        etcdir = os.path.join(self.package_folder, "etc")
        copy(self, "qpage", self.source_folder, bindir)
        os.chmod(os.path.join(bindir, "qpage"), 0o755)
        copy(self, "qpage.man", self.source_folder, mandir)
        os.rename(os.path.join(mandir, "qpage.man"), os.path.join(mandir, "qpage.1"))
        copy(self, "example.cf", self.source_folder, etcdir)
        os.rename(os.path.join(etcdir, "example.cf"), os.path.join(etcdir, "qpage.conf.sample"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

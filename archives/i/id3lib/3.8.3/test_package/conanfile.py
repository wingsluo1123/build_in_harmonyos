#!/usr/bin/env python3
"""Conan test_package for id3lib 3.8.3 — L1 consumer test (R34/R53).

Builds a real consumer against the packaged static libid3.a and runs an
ID3v2 tag round-trip (create -> write -> re-open -> assert -> modify ->
re-read). Additionally asserts HarmonyOS-specific properties of the
produced binary: AArch64 ELF, musl program interpreter and no dangerous
RPATH/RUNPATH entries.
"""
import os
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class Id3LibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ---------- HarmonyOS ELF checks (task R53) ----------

    @staticmethod
    def _read_elf(path):
        with open(path, "rb") as stream:
            header = stream.read(64)
            if len(header) != 64 or header[:4] != b"\x7fELF":
                raise ConanException(f"not an ELF file: {path}")
            if header[4] != 2 or header[5] != 1:
                raise ConanException(f"expected little-endian ELF64: {path}")
            machine = struct.unpack_from("<H", header, 18)[0]
            phoff = struct.unpack_from("<Q", header, 32)[0]
            phentsize = struct.unpack_from("<H", header, 54)[0]
            phnum = struct.unpack_from("<H", header, 56)[0]
            interpreter = None
            for index in range(phnum):
                stream.seek(phoff + index * phentsize)
                ph = stream.read(phentsize)
                if len(ph) < 40:
                    raise ConanException(f"truncated ELF program header: {path}")
                if struct.unpack_from("<I", ph, 0)[0] != 3:  # PT_INTERP
                    continue
                offset = struct.unpack_from("<Q", ph, 8)[0]
                size = struct.unpack_from("<Q", ph, 32)[0]
                stream.seek(offset)
                interpreter = stream.read(size).rstrip(b"\0").decode("ascii")
                break
        return machine, interpreter

    def _assert_harmonyos_elf(self, path):
        machine, interpreter = self._read_elf(path)
        if machine != 183:
            raise ConanException(
                f"expected AArch64 ELF (EM_AARCH64=183), got {machine}: {path}")
        if not (interpreter and interpreter.endswith("/ld-musl-aarch64.so.1")):
            raise ConanException(
                f"unexpected HarmonyOS program interpreter {interpreter!r}: {path}")
        self.output.info(
            f"HarmonyOS ELF verified: e_machine={machine}, "
            f"interpreter={interpreter}: {path}")

    @staticmethod
    def _read_rpaths(path):
        """Return RPATH/RUNPATH strings from the dynamic section (pure Python)."""
        with open(path, "rb") as stream:
            data = stream.read()
        if data[:4] != b"\x7fELF":
            return []
        e_phoff = struct.unpack_from("<Q", data, 32)[0]
        e_phentsize = struct.unpack_from("<H", data, 54)[0]
        e_phnum = struct.unpack_from("<H", data, 56)[0]
        loads = []
        dyn = None
        for index in range(e_phnum):
            off = e_phoff + index * e_phentsize
            p_type = struct.unpack_from("<I", data, off)[0]
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_vaddr = struct.unpack_from("<Q", data, off + 16)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            if p_type == 1:  # PT_LOAD
                loads.append((p_vaddr, p_offset, p_filesz))
            elif p_type == 2:  # PT_DYNAMIC
                dyn = (p_offset, p_filesz)
        if dyn is None:
            return []
        d_off, d_size = dyn
        strtab_vaddr = None
        entries = []
        for i in range(0, d_size - d_size % 16, 16):
            d_tag = struct.unpack_from("<q", data, d_off + i)[0]
            d_val = struct.unpack_from("<Q", data, d_off + i + 8)[0]
            if d_tag == 5:  # DT_STRTAB
                strtab_vaddr = d_val
            entries.append((d_tag, d_val))

        def vaddr_to_off(vaddr):
            for base_vaddr, base_off, size in loads:
                if base_vaddr <= vaddr < base_vaddr + size:
                    return base_off + (vaddr - base_vaddr)
            return None

        result = []
        for d_tag, d_val in entries:
            if d_tag in (15, 29):  # DT_RPATH / DT_RUNPATH
                off = vaddr_to_off(d_val)
                if off is not None:
                    end = data.find(b"\0", off)
                    if end > off:
                        result.append(data[off:end].decode("utf-8", "replace"))
        return result

    def _assert_no_dangerous_rpath(self, path):
        dangerous = ("/.conan2/", "/usr/local", "/storage/", "/tmp/")
        for rpath in self._read_rpaths(path):
            for bad in dangerous:
                if bad in rpath:
                    raise ConanException(
                        f"dangerous RPATH/RUNPATH entry {rpath!r} in {path}")
        self.output.info(
            f"RPATH check OK (entries: {self._read_rpaths(path) or 'none'}): {path}")

    # ----------------------------------------------------------

    def test(self):
        binary = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "test_id3lib" in files:
                binary = os.path.join(root, "test_id3lib")
                break
        if binary is None:
            raise ConanException("test_id3lib binary not found under build folder")

        self._assert_harmonyos_elf(binary)
        self._assert_no_dangerous_rpath(binary)
        self.run(f'"{binary}"', env="conanrun", cwd=self.build_folder)
        self.output.info(
            "id3lib test_package PASSED: ID3 write/re-read round-trip + "
            "AArch64/musl ELF checks")

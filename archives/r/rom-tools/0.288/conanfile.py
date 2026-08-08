#!/usr/bin/env python3
"""
Conan recipe for rom-tools 0.288 (MAME CLI tools: chdman, romcmp)

This is a custom build that bypasses MAME's genie build system (which requires SDL2).
Only the standalone CLI tools (chdman, romcmp) are built, using:
- Embedded LZMA SDK (3rdparty/lzma/C/) for 7z support
- Embedded utf8proc (3rdparty/utf8proc/) for Unicode processing
- Embedded zstd (3rdparty/zstd/lib/) for Zstandard compression
- Embedded FLAC (3rdparty/flac/src/libFLAC/) for FLAC audio support
- Conan dependencies for zlib, expat (available as OHOS binaries)
- Stubbed SDL clipboard functions (osdlib_unix.cpp patch)
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, save, copy, apply_conandata_patches, export_conandata_patches


class RomToolsConan(ConanFile):
    name = "rom-tools"
    version = "0.288"
    description = "MAME ROM tools (chdman, romcmp) - CLI utilities for CHD and ROM management"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mamedev/mame"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("expat/2.8.2.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        src = self.source_folder
        build = self.build_folder

        # Collect include paths from conan dependencies
        dep_includes = []
        dep_lib_dirs = []
        dep_libs = []
        for dep_name in ["zlib", "expat"]:
            dep = self.dependencies[dep_name]
            cpp = dep.cpp_info
            # Handle both simple and component-based packages
            if hasattr(cpp, "components") and cpp.components:
                for comp in cpp.components.values():
                    for incdir in (comp.includedirs or []):
                        dep_includes.append(f"-I{incdir}")
                    for libdir in (comp.libdirs or []):
                        dep_lib_dirs.append(f"-L{libdir}")
                    dep_libs.extend([f"-l{l}" for l in (comp.libs or [])])
            else:
                for incdir in (cpp.includedirs or []):
                    dep_includes.append(f"-I{incdir}")
                for libdir in (cpp.libdirs or []):
                    dep_lib_dirs.append(f"-L{libdir}")
                dep_libs.extend([f"-l{l}" for l in (cpp.libs or [])])

        dep_flags = " ".join(dep_includes)
        dep_ldflags = " ".join(dep_lib_dirs)
        dep_ldlibs = " ".join(dep_libs)

        # Common defines for MAME
        defines = (
            "-DLSB_FIRST -DCRLF=2 -DUTF8PROC_STATIC "
            "-DZ7_PPMD_SUPPORT -DZ7_ST -DSDLMAME_UNIX -DSDLMAME_LINUX -DSDLMAME_NO_SDL"
        )

        # FLAC-specific defines (from genie 3rdparty.lua)
        flac_defines = (
            "-DNDEBUG -DHAVE_CONFIG_H -DENABLE_64_BIT_WORDS=1 "
            "-DOGG_FOUND=0 -DFLAC__HAS_OGG=0 -DHAVE_LROUND=1 "
            "-DHAVE_INTTYPES_H -DHAVE_STDBOOL_H -DHAVE_STDINT_H "
            "-DHAVE_STDIO_H -DHAVE_STDLIB_H -DHAVE_STRING_H "
            "-D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE "
            "-DHAVE_BSWAP16 -DHAVE_BSWAP32 "
            "-DCPU_IS_BIG_ENDIAN=0 -DCPU_IS_LITTLE_ENDIAN=1 "
            "-DWORDS_BIGENDIAN=0 -DFLAC__NO_DLL"
        )

        # Include paths (src + 3rdparty)
        includes = (
            f"-I{src}/src/osd -I{src}/src/osd/modules/file "
            f"-I{src}/src/lib -I{src}/src/lib/util "
            f"-I{src}/3rdparty -I{src}/3rdparty/utf8proc "
            f"-I{src}/3rdparty/zstd/lib -I{src}/3rdparty/zstd/lib/common "
            f"-I{src}/3rdparty/flac/include {dep_flags}"
        )

        # Compiler flags
        cxx = "clang++"
        cc = "clang"
        cxx_flags = f"-std=c++20 -O2 -fPIC -Wno-error {defines} {includes}"
        c_flags = f"-std=gnu99 -O2 -fPIC -Wno-error {defines} {includes}"
        # LZMA-specific C flags (extra warning suppression)
        lzma_c_flags = f"{c_flags} -Wno-error=undef -Wno-error=strict-prototypes"
        # zstd-specific C flags
        zstd_defines = "-DXXH_NAMESPACE=ZSTD_ -DDEBUGLEVEL=0 -DZSTD_DISABLE_ASM"
        zstd_c_flags = f"-std=gnu99 -O2 -fPIC -Wno-error {zstd_defines} {includes}"
        # FLAC-specific C flags (extra include for config.h)
        flac_includes = f"-I{src}/3rdparty/flac/src/libFLAC/include -I{src}/3rdparty/flac/include {dep_flags}"
        flac_c_flags = f"-std=gnu99 -O2 -fPIC -Wno-error {flac_defines} {flac_includes}"

        # System link libraries
        sys_libs = "-ldl -lrt -lpthread -lm -lutil"

        # Utils library source files (all .cpp from src/lib/util/)
        util_src = sorted(glob.glob(f"{src}/src/lib/util/*.cpp"))
        util_objs = [f"{build}/util/{os.path.basename(f).replace('.cpp', '.o')}" for f in util_src]

        # OSD core source files (skip osdmodule.cpp which requires emucore.h)
        osd_src = [
            f"{src}/src/osd/osdcore.cpp",
            f"{src}/src/osd/strconv.cpp",
            f"{src}/src/osd/osdsync.cpp",
            f"{src}/src/osd/modules/lib/osdlib_unix.cpp",
            f"{src}/src/osd/modules/file/posixfile.cpp",
            f"{src}/src/osd/modules/file/posixdir.cpp",
            f"{src}/src/osd/modules/file/posixptty.cpp",
            f"{src}/src/osd/modules/file/posixsocket.cpp",
        ]
        osd_objs = [f"{build}/osd/{os.path.basename(f).replace('.cpp', '.o')}" for f in osd_src]

        # LZMA (7z) source files - exact list from genie 3rdparty.lua
        # Excluded: AesOpt.c, Sha256Opt.c (ARM crypto intrinsics not available)
        lzma_active = [
            "7zAlloc.c", "7zArcIn.c", "7zBuf.c", "7zBuf2.c", "7zCrc.c",
            "7zCrcOpt.c", "7zDec.c", "7zFile.c", "7zStream.c", "Aes.c",
            "Alloc.c", "Bcj2.c", "Bra.c", "Bra86.c", "BraIA64.c",
            "CpuArch.c", "Delta.c", "LzFind.c", "LzFindOpt.c", "Lzma2Dec.c",
            "LzmaDec.c", "LzmaEnc.c", "Ppmd7.c", "Ppmd7Dec.c", "Sha256.c",
            "Sort.c",
        ]
        lzma_src = [f"{src}/3rdparty/lzma/C/{f}" for f in lzma_active]
        lzma_objs = [f"{build}/lzma/{f.replace('.c', '.o')}" for f in lzma_active]

        # zstd source files (embedded, skip .S assembly files)
        zstd_all = sorted(glob.glob(f"{src}/3rdparty/zstd/lib/common/*.c") +
                          glob.glob(f"{src}/3rdparty/zstd/lib/compress/*.c") +
                          glob.glob(f"{src}/3rdparty/zstd/lib/decompress/*.c"))
        zstd_skip = {"huf_decompress_amd64.S"}  # not .c anyway
        zstd_src = [f for f in zstd_all if os.path.basename(f) not in zstd_skip]
        zstd_objs = [f"{build}/zstd/{os.path.basename(f).replace('.c', '.o')}" for f in zstd_src]

        # FLAC source files (embedded, from genie 3rdparty.lua)
        flac_active = [
            "bitmath.c", "bitreader.c", "bitwriter.c", "cpu.c", "crc.c",
            "fixed.c", "fixed_intrin_avx2.c", "fixed_intrin_sse2.c",
            "fixed_intrin_sse42.c", "fixed_intrin_ssse3.c", "float.c",
            "format.c", "lpc.c", "lpc_intrin_avx2.c", "lpc_intrin_fma.c",
            "lpc_intrin_neon.c", "lpc_intrin_sse2.c", "lpc_intrin_sse41.c",
            "md5.c", "memory.c", "stream_decoder.c", "stream_encoder.c",
            "stream_encoder_framing.c", "stream_encoder_intrin_avx2.c",
            "stream_encoder_intrin_sse2.c", "stream_encoder_intrin_ssse3.c",
            "window.c",
        ]
        flac_src = [f"{src}/3rdparty/flac/src/libFLAC/{f}" for f in flac_active]
        flac_objs = [f"{build}/flac/{f.replace('.c', '.o')}" for f in flac_active]

        # utf8proc source
        utf8_src = f"{src}/3rdparty/utf8proc/utf8proc.c"
        utf8_obj = f"{build}/utf8proc/utf8proc.o"

        # version.cpp (generated)
        version_src = f"{build}/version.cpp"
        version_obj = f"{build}/version.o"

        # Tool sources
        chdman_src = f"{src}/src/tools/chdman.cpp"
        chdman_obj = f"{build}/chdman.o"
        romcmp_src = f"{src}/src/tools/romcmp.cpp"
        romcmp_obj = f"{build}/romcmp.o"

        all_objs = " ".join(util_objs + osd_objs + lzma_objs + zstd_objs + flac_objs + [utf8_obj, version_obj])
        link_flags = f"{dep_ldflags} {dep_ldlibs} {sys_libs}"

        # Build Makefile content
        makefile_lines = [
            "# Auto-generated Makefile for rom-tools 0.288 (MAME CLI tools)",
            f"CXX = {cxx}",
            f"CC = {cc}",
            f"CXXFLAGS = {cxx_flags}",
            f"CFLAGS = {c_flags}",
            f"LZMA_CFLAGS = {lzma_c_flags}",
            f"ZSTD_CFLAGS = {zstd_c_flags}",
            f"FLAC_CFLAGS = {flac_c_flags}",
            f"UTIL_OBJS = {' '.join(util_objs)}",
            f"OSD_OBJS = {' '.join(osd_objs)}",
            f"LZMA_OBJS = {' '.join(lzma_objs)}",
            f"ZSTD_OBJS = {' '.join(zstd_objs)}",
            f"FLAC_OBJS = {' '.join(flac_objs)}",
            f"UTF8_OBJ = {utf8_obj}",
            f"VERSION_OBJ = {version_obj}",
            f"ALL_OBJS = $(UTIL_OBJS) $(OSD_OBJS) $(LZMA_OBJS) $(ZSTD_OBJS) $(FLAC_OBJS) $(UTF8_OBJ) $(VERSION_OBJ)",
            f"LINK_FLAGS = {link_flags}",
            ".PHONY: all clean",
            "all: chdman romcmp",
            "",
        ]

        # Utils pattern rule
        makefile_lines.extend([
            f"# Utils library",
            f"{build}/util/%.o: {src}/src/lib/util/%.cpp | {build}/util",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            "",
        ])

        # OSD pattern rules (multiple source dirs)
        makefile_lines.extend([
            f"# OSD core",
            f"{build}/osd/%.o: {src}/src/osd/%.cpp | {build}/osd",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            f"{build}/osd/%.o: {src}/src/osd/modules/lib/%.cpp | {build}/osd",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            f"{build}/osd/%.o: {src}/src/osd/modules/file/%.cpp | {build}/osd",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            "",
        ])

        # LZMA pattern rule
        makefile_lines.extend([
            f"# LZMA (7z)",
            f"{build}/lzma/%.o: {src}/3rdparty/lzma/C/%.c | {build}/lzma",
            "\t$(CC) $(LZMA_CFLAGS) -c $< -o $@",
            "",
        ])

        # zstd pattern rules (multiple source dirs)
        makefile_lines.extend([
            f"# zstd (embedded)",
            f"{build}/zstd/%.o: {src}/3rdparty/zstd/lib/common/%.c | {build}/zstd",
            "\t$(CC) $(ZSTD_CFLAGS) -c $< -o $@",
            f"{build}/zstd/%.o: {src}/3rdparty/zstd/lib/compress/%.c | {build}/zstd",
            "\t$(CC) $(ZSTD_CFLAGS) -c $< -o $@",
            f"{build}/zstd/%.o: {src}/3rdparty/zstd/lib/decompress/%.c | {build}/zstd",
            "\t$(CC) $(ZSTD_CFLAGS) -c $< -o $@",
            "",
        ])

        # FLAC pattern rule
        makefile_lines.extend([
            f"# FLAC (embedded)",
            f"{build}/flac/%.o: {src}/3rdparty/flac/src/libFLAC/%.c | {build}/flac",
            "\t$(CC) $(FLAC_CFLAGS) -c $< -o $@",
            "",
        ])

        # utf8proc
        makefile_lines.extend([
            f"# utf8proc",
            f"{utf8_obj}: {utf8_src} | {build}/utf8proc",
            "\t$(CC) $(CFLAGS) -c $< -o $@",
            "",
        ])

        # version.cpp (generated)
        makefile_lines.extend([
            f"# version.cpp (generated)",
            f"{version_obj}: {version_src}",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            "",
        ])

        # chdman
        makefile_lines.extend([
            f"# chdman",
            f"{chdman_obj}: {chdman_src}",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            f"chdman: {chdman_obj} $(ALL_OBJS)",
            f"\t$(CXX) $(CXXFLAGS) {chdman_obj} $(ALL_OBJS) $(LINK_FLAGS) -o {build}/chdman",
            "",
        ])

        # romcmp
        makefile_lines.extend([
            f"# romcmp",
            f"{romcmp_obj}: {romcmp_src}",
            "\t$(CXX) $(CXXFLAGS) -c $< -o $@",
            f"romcmp: {romcmp_obj} $(ALL_OBJS)",
            f"\t$(CXX) $(CXXFLAGS) {romcmp_obj} $(ALL_OBJS) $(LINK_FLAGS) -o {build}/romcmp",
            "",
        ])

        # Directory creation
        makefile_lines.extend([
            f"{build}/util {build}/osd {build}/lzma {build}/zstd {build}/flac {build}/utf8proc:",
            "\tmkdir -p $@",
            "",
            "clean:",
            f"\trm -rf {build}/util {build}/osd {build}/lzma {build}/zstd {build}/flac {build}/utf8proc *.o chdman romcmp",
        ])

        save(self, "Makefile", "\n".join(makefile_lines) + "\n")

    def build(self):
        # Generate version.cpp
        save(self, "version.cpp",
             'extern const char build_version[];\n'
             'const char build_version[] = "0.288 (harmonyos)";\n')

        # Build using generated Makefile
        self.run("make -j2")

    def package(self):
        copy(self, "chdman", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "romcmp", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

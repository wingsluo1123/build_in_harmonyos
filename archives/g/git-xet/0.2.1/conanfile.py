#!/usr/bin/env python3
"""Conan recipe — git-xet 0.2.1 (pre-compiled binary with musl adaptation)

git-xet is a Rust-based Git extension for large file storage (XetHub/HuggingFace).
The source is Rust, which cannot be compiled natively on HarmonyOS (rustc SIGSEGV on musl).
This recipe packages the upstream pre-compiled aarch64 Linux binary, adapting it
for musl-based HarmonyOS using patchelf + Alpine gcompat compatibility layer.

Adaptation approach:
  1. Download pre-compiled git-xet binary from GitHub releases (glibc-dynamic)
  2. patchelf --replace-needed: libc.so.6 → libgcompat.so.0 (Alpine gcompat)
  3. patchelf --replace-needed: libm.so.6 → libgcompat.so.0
  4. patchelf --replace-needed: ld-linux-aarch64.so.1 → libglibc-shim.so (custom stub)
  5. patchelf --set-interpreter /lib/ld-musl-aarch64.so.1 (musl dynamic linker)
  6. Add .note.ohos.ident section + PT_NOTE program header (HarmonyOS requirement)
  7. Build libglibc-shim.so from glibc-shim.c (provides missing glibc symbols)
  8. Bundle Alpine gcompat/libucontext/libobstack/libgcc_s compatibility libraries

R32: settings.os check in ("Linux", "OHOS")
R38: Command-line tool — commands.json required at software level
"""
import os
import shutil
import struct
import subprocess
import tarfile
import zipfile
import urllib.request
import socket

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


# OHOS note section data (28 bytes)
OHOS_NOTE_DATA = bytes([
    0x0c, 0x00, 0x00, 0x00,  # namesz = 12
    0x04, 0x00, 0x00, 0x00,  # descsz = 4
    0x01, 0x00, 0x00, 0x00,  # type = 1
    0x4f, 0x48, 0x4f, 0x53,  # "OHOS"
    0x00, 0x00, 0x00, 0x00,  # padding
    0x00, 0x00, 0x00, 0x00,  # padding
    0x01, 0x00, 0x00, 0x00,  # desc data
])

SECTION_NAME = b".note.ohos.ident\x00"

# glibc-shim.c source code (inline fallback if patches/ not exported)
GLIBC_SHIM_SOURCE = r"""
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/types.h>

struct __res_state_shim { char _padding[512]; };
static struct __res_state_shim _res_shim;
struct __res_state_shim *__res_state(void) { return &_res_shim; }
int __res_init(void) { return 0; }
const char *gnu_get_libc_version(void) { return "2.31"; }
int pthread_mutexattr_setrobust(pthread_mutexattr_t *attr, int r) { return 0; }
int pthread_mutex_consistent(pthread_mutex_t *mutex) { return 0; }
"""


def _add_ohos_note(data):
    """Add .note.ohos.ident section + PT_NOTE program header to ELF binary data.

    Places note data in free space between program headers and first section,
    adds a PT_NOTE program header entry, and extends the section header table.
    """
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3a)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3c)[0]
    e_shstrndx = struct.unpack_from("<H", data, 0x3e)[0]

    ph_end = e_phoff + e_phnum * e_phentsize

    # Find first non-null section
    first_sec = None
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_type = struct.unpack_from("<I", data, off + 4)[0]
        sh_offset = struct.unpack_from("<Q", data, off + 24)[0]
        if sh_type != 0 and sh_offset > 0 and (first_sec is None or sh_offset < first_sec):
            first_sec = sh_offset

    free_end = first_sec if first_sec else ph_end + 0x1000
    if free_end - ph_end < e_phentsize + len(OHOS_NOTE_DATA) + 8:
        return data  # Not enough space, skip

    # New PT_NOTE entry at ph_end
    note_offset = (ph_end + e_phentsize + 7) & ~7
    note_addr = note_offset

    # Write PT_NOTE program header
    pt_note = struct.pack("<IIQQQQQQ",
        4, 4, note_offset, note_addr, note_addr,
        len(OHOS_NOTE_DATA), len(OHOS_NOTE_DATA), 8)
    data[ph_end:ph_end + len(pt_note)] = pt_note

    # Write note data
    data[note_offset:note_offset + len(OHOS_NOTE_DATA)] = OHOS_NOTE_DATA

    # Update e_phnum
    struct.pack_into("<H", data, 0x38, e_phnum + 1)

    # Get shstrtab
    shstr_hdr = e_shoff + e_shstrndx * e_shentsize
    shstr_off = struct.unpack_from("<Q", data, shstr_hdr + 24)[0]
    shstr_size = struct.unpack_from("<Q", data, shstr_hdr + 32)[0]
    shstrtab = bytes(data[shstr_off:shstr_off + shstr_size])

    new_name_idx = len(shstrtab)
    new_shstrtab = shstrtab + SECTION_NAME

    orig_len = len(data)
    new_shstr_off = orig_len + (8 - orig_len % 8) % 8
    new_shoff = new_shstr_off + len(new_shstrtab)
    new_shoff += (8 - new_shoff % 8) % 8

    out = bytearray(data)
    out.extend(b'\x00' * (new_shstr_off - orig_len))
    out.extend(new_shstrtab)
    out.extend(b'\x00' * (new_shoff - new_shstr_off - len(new_shstrtab)))

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sections.append(list(struct.unpack_from("<IIQQQQIIQQ", data, off)))

    sections[e_shstrndx][4] = new_shstr_off
    sections[e_shstrndx][5] = len(new_shstrtab)
    sections.append([new_name_idx, 7, 0x2, note_addr, note_offset,
                     len(OHOS_NOTE_DATA), 0, 0, 8, 0])

    for s in sections:
        out.extend(struct.pack("<IIQQQQIIQQ", *s))

    struct.pack_into("<Q", out, 0x28, new_shoff)
    struct.pack_into("<H", out, 0x3c, len(sections))

    return bytes(out)


class GitXetConan(ConanFile):
    name = "git-xet"
    version = "0.2.1"
    description = "Git extension for large file storage (XetHub/HuggingFace xet-core)"
    license = "Apache-2.0"
    homepage = "https://github.com/huggingface/xet-core"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    ALPINE_BASE = "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/aarch64"
    ALPINE_PACKAGES = {
        "gcompat-1.1.0-r4.apk": "gcompat",
        "libucontext-1.3.2-r0.apk": "libucontext",
        "musl-obstack-1.2.3-r2.apk": "musl-obstack",
        "libgcc-14.2.0-r4.apk": "libgcc",
    }

    BINARY_URL = (
        "https://github.com/huggingface/xet-core/releases/download/"
        "git-xet-v0.2.1/git-xet-linux-aarch64.zip"
    )
    BINARY_MIRROR_URL = (
        "https://gh-proxy.com/https://github.com/huggingface/xet-core/"
        "releases/download/git-xet-v0.2.1/git-xet-linux-aarch64.zip"
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "git-xet is only supported on Linux/OHOS, not " + str(self.settings.os))
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "git-xet pre-compiled binary only supports aarch64 (armv8), not "
                + str(self.settings.arch))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # Export glibc-shim.c source file (not a standard patch)
        copy(self, "glibc-shim.c", self.recipe_folder,
             os.path.join(self.export_sources_folder, "patches"))

    def source(self):
        # Source tarball is Rust source code, not used in build (pre-compiled binary).
        # Skip download - source is reference only.
        pass

    def _download_binary(self):
        zip_path = os.path.join(self.build_folder, "git-xet-linux-aarch64.zip")
        if not os.path.exists(zip_path):
            # Check for pre-downloaded local copy
            local_paths = [
                os.path.expanduser("~/git-xet-work/git-xet-linux-aarch64.zip"),
                os.path.join(os.environ.get("HOME", ""), "git-xet-work", "git-xet-linux-aarch64.zip"),
            ]
            for lp in local_paths:
                if os.path.exists(lp) and os.path.getsize(lp) == 17285954:
                    self.output.info(f"Using pre-downloaded binary from {lp}")
                    shutil.copy2(lp, zip_path)
                    return zip_path

            self.output.info("Downloading pre-compiled git-xet binary...")
            socket.setdefaulttimeout(120)
            for url in [self.BINARY_MIRROR_URL, self.BINARY_URL]:
                try:
                    self.output.info(f"  Trying: {url}")
                    urllib.request.urlretrieve(url, zip_path)
                    self.output.info(f"  Downloaded: {os.path.getsize(zip_path)} bytes")
                    break
                except Exception as e:
                    self.output.warning(f"  Failed: {e}")
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
            if not os.path.exists(zip_path):
                raise Exception("Failed to download git-xet binary from all URLs")
        return zip_path

    def _download_alpine_packages(self, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        # Check for pre-downloaded local copies
        local_alpine = os.path.expanduser("~/git-xet-work/alpine-libs")
        for apk_name, pkg_name in self.ALPINE_PACKAGES.items():
            apk_path = os.path.join(dest_dir, apk_name)
            if not os.path.exists(apk_path):
                # Try local copy first
                local_apk = os.path.join(local_alpine, apk_name)
                if os.path.exists(local_apk):
                    shutil.copy2(local_apk, apk_path)
                else:
                    url = f"{self.ALPINE_BASE}/{apk_name}"
                    self.output.info(f"Downloading Alpine package: {apk_name}")
                    urllib.request.urlretrieve(url, apk_path)
            extract_dir = os.path.join(dest_dir, pkg_name)
            if not os.path.exists(extract_dir):
                with tarfile.open(apk_path, "r:gz") as tar:
                    tar.extractall(extract_dir)

    def _build_glibc_shim(self, build_dir):
        shim_out = os.path.join(build_dir, "libglibc-shim.so")
        # Try multiple possible locations for glibc-shim.c
        possible_paths = [
            os.path.join(self.source_folder, "patches", "glibc-shim.c"),
            os.path.join(self.recipe_folder, "patches", "glibc-shim.c") if hasattr(self, 'recipe_folder') and self.recipe_folder else None,
            os.path.join(self.export_sources_folder, "patches", "glibc-shim.c") if hasattr(self, 'export_sources_folder') else None,
        ]
        shim_src = None
        for p in possible_paths:
            if p and os.path.exists(p):
                shim_src = p
                break
        if not shim_src:
            # Write inline as fallback
            shim_src = os.path.join(build_dir, "glibc-shim.c")
            with open(shim_src, "w") as f:
                f.write(GLIBC_SHIM_SOURCE)
        self.output.info(f"Building glibc-shim.so from {shim_src}...")
        self.run(f"clang -shared -fPIC -o {shim_out} {shim_src} -lpthread")
        return shim_out
        self.output.info("Building glibc-shim.so...")
        self.run(f"clang -shared -fPIC -o {shim_out} {shim_src} -lpthread")
        return shim_out

    def _apply_patchelf(self, binary_path):
        self.output.info("Applying patchelf modifications...")
        self.run(f'patchelf --replace-needed libc.so.6 libgcompat.so.0 "{binary_path}"')
        self.run(f'patchelf --replace-needed libm.so.6 libgcompat.so.0 "{binary_path}"')
        self.run(f'patchelf --replace-needed ld-linux-aarch64.so.1 libglibc-shim.so "{binary_path}"')
        self.run(f'patchelf --set-interpreter /lib/ld-musl-aarch64.so.1 "{binary_path}"')
        self.run(f'patchelf --set-rpath "$ORIGIN/../lib" "{binary_path}"')

    def _add_ohos_ident(self, binary_path):
        """Add .note.ohos.ident section to the binary for HarmonyOS execution."""
        self.output.info("Adding .note.ohos.ident section...")
        with open(binary_path, "rb") as f:
            data = bytearray(f.read())
        result = _add_ohos_note(data)
        with open(binary_path, "wb") as f:
            f.write(result)
        os.chmod(binary_path, 0o755)

    def build(self):
        build_dir = self.build_folder

        # Step 1: Download and extract pre-compiled binary
        zip_path = self._download_binary()
        self.output.info("Extracting pre-compiled binary...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(build_dir)

        binary_path = os.path.join(build_dir, "git-xet")
        if not os.path.exists(binary_path):
            for root, dirs, files in os.walk(build_dir):
                if "git-xet" in files:
                    binary_path = os.path.join(root, "git-xet")
                    break
        if not os.path.exists(binary_path):
            raise Exception("git-xet binary not found in extracted zip")

        # Step 2: Download Alpine compatibility packages
        alpine_dir = os.path.join(build_dir, "alpine")
        self._download_alpine_packages(alpine_dir)

        # Step 3: Build glibc-shim
        self._build_glibc_shim(build_dir)

        # Step 4: Apply patchelf
        self._apply_patchelf(binary_path)

        # Step 5: Add .note.ohos.ident section (HarmonyOS requirement)
        self._add_ohos_ident(binary_path)

        # Step 6: Verify binary (may fail on HMDFS, non-blocking)
        self.output.info("Verifying git-xet binary...")
        self.run(f'"{binary_path}" --version', ignore_errors=True)

    def package(self):
        # Copy git-xet binary
        copy(self, "git-xet", self.build_folder, os.path.join(self.package_folder, "bin"))

        # Copy glibc-shim library
        copy(self, "libglibc-shim.so", self.build_folder, os.path.join(self.package_folder, "lib"))

        # Copy Alpine compatibility libraries
        alpine_dir = os.path.join(self.build_folder, "alpine")
        for pkg_name in self.ALPINE_PACKAGES.values():
            pkg_dir = os.path.join(alpine_dir, pkg_name)
            for root, dirs, files in os.walk(pkg_dir):
                for f in files:
                    src = os.path.join(root, f)
                    if os.path.islink(src):
                        continue
                    if f.endswith(".so") or ".so." in f:
                        dst = os.path.join(self.package_folder, "lib", f)
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)

        # Make binary executable
        bin_path = os.path.join(self.package_folder, "bin", "git-xet")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)

        # Create symlinks for gcompat compatibility
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        for link, target in [("libc.so.6", "libgcompat.so.0"), ("libm.so.6", "libgcompat.so.0")]:
            link_path = os.path.join(lib_dir, link)
            if not os.path.exists(link_path):
                os.symlink(target, link_path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

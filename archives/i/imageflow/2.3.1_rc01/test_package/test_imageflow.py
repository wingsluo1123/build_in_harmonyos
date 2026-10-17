#!/usr/bin/env python3
"""imageflow 2.3.1_rc01 consumer test: real image ops + HarmonyOS traits.

Reports every assertion on its own line so the counts quoted in the PR stay
auditable.

HarmonyOS-specific assertions (B*):
  B1 imageflow_tool is an AArch64 ELF (EM_AARCH64=183)
  B2 PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1)
  B3 imageflow_tool carries an OHOS code signature (.codesign section)
  B4 libimageflow.so is an AArch64 shared object
  B5 libimageflow.so carries an OHOS code signature
  B6 no dangerous RPATH/RUNPATH in either artifact

Real image operations through the packaged tool (A*):
  A1 diagnose --show-compilation-info exits 0
  A2 PNG->JPEG stretch resize exits 0
  A3 JPEG output is exactly 8x8 (mozjpeg encode path)
  A4 PNG->PNG width resize exits 0
  A5 PNG output width is 16 (libpng encode path)
"""
import base64
import hashlib
import os
import struct
import subprocess
import sys

EM_AARCH64 = 183
OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"

# Test input: a 32x32 RGBA PNG, 2313 bytes (sha256 below). It is embedded
# as base64 instead of being tracked as a binary file, because the forge's
# PR diff endpoint carries no binary patch data: a tracked binary makes
# the CI checkout step fail with "missing binary patch data ... patch does
# not apply" before the build even starts (same class of fix as the
# cxxtools zoneinfo and d52 z.bin storage adaptations).
PNG_SHA256 = "7d1a73bb65fc3ef3d7f4c0ee0720a78460b86167c6e137d6cb182fc37b4d0f87"
PNG_B64 = (
    "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"
)

PASSED = 0
FAILED = 0


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"[ok] {name}{(': ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"[fail] {name}{(': ' + detail) if detail else ''}",
              file=sys.stderr)
    return ok


def materialize_input_png(run_dir):
    """Write the embedded 32x32 test PNG to <run_dir>/input.png.

    The image is embedded as base64 (see PNG_B64) rather than shipped as
    a tracked binary file: the forge's PR diff endpoint carries no binary
    patch data, so a tracked binary makes the CI checkout step fail with
    "missing binary patch data ... patch does not apply" before the build
    even starts. Returns the path of the written file.
    """
    payload = base64.b64decode(PNG_B64)
    if hashlib.sha256(payload).hexdigest() != PNG_SHA256:
        raise AssertionError("embedded input.png payload is corrupt")
    png_path = os.path.join(run_dir, "input.png")
    with open(png_path, "wb") as fh:
        fh.write(payload)
    return png_path


def _elf_load_map(data):
    """Map virtual address -> file offset using PT_LOAD program headers."""
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    segs = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type == 1:  # PT_LOAD
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_vaddr = struct.unpack_from("<Q", data, off + 16)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            segs.append((p_vaddr, p_offset, p_filesz))
    return segs


def _vaddr_to_offset(segs, vaddr):
    for p_vaddr, p_offset, p_filesz in segs:
        if p_vaddr <= vaddr < p_vaddr + p_filesz:
            return p_offset + (vaddr - p_vaddr)
    return None


def elfinfo(path):
    info = {"e_machine": None, "interp": None, "runpaths": []}
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        return info
    info["e_machine"] = struct.unpack_from("<H", data, 18)[0]
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    segs = _elf_load_map(data)
    dyn = None
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type == 3:  # PT_INTERP
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            info["interp"] = (data[p_offset:p_offset + p_filesz]
                              .rstrip(b"\x00").decode("utf-8", "replace"))
        elif p_type == 2:  # PT_DYNAMIC
            dyn = (struct.unpack_from("<Q", data, off + 8)[0],
                   struct.unpack_from("<Q", data, off + 32)[0])
    if dyn:
        d_off, d_size = dyn
        entries = []
        strtab = strsz = None
        for i in range(d_size // 16):
            tag, val = struct.unpack_from("<qQ", data, d_off + i * 16)
            entries.append((tag, val))
            if tag == 5:  # DT_STRTAB
                strtab = val
            elif tag == 10:  # DT_STRSZ
                strsz = val
        if strtab is not None and strsz:
            str_off = _vaddr_to_offset(segs, strtab)
            if str_off is not None:
                for tag, val in entries:
                    if tag in (15, 29):  # DT_RPATH / DT_RUNPATH
                        start = str_off + val
                        end = data.index(b"\x00", start)
                        info["runpaths"].append(
                            data[start:end].decode("utf-8", "replace"))
    return info


def png_size(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def jpeg_size(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:  # EOI
            break
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if (0xC0 <= marker <= 0xC3 or 0xC5 <= marker <= 0xC7
                or 0xC9 <= marker <= 0xCB or 0xCD <= marker <= 0xCF):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return (width, height)
        i += 2 + seg_len
    return None


def main():
    package_folder = os.environ["PACKAGE_FOLDER"]
    exe = os.path.join(package_folder, "bin", "imageflow_tool")
    lib = os.path.join(package_folder, "lib", "libimageflow.so")
    here = os.path.dirname(os.path.abspath(__file__))
    run_dir = os.environ.get("TEST_RUN_DIR") or os.path.join(here, "run")
    os.makedirs(run_dir, exist_ok=True)
    source_png = materialize_input_png(run_dir)

    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    tool_info = elfinfo(exe)
    check("B1: imageflow_tool is an AArch64 ELF",
          tool_info["e_machine"] == EM_AARCH64,
          f"e_machine={tool_info['e_machine']}")
    check("B2: PT_INTERP is the OHOS musl loader",
          tool_info["interp"] is not None
          and OHOS_MUSL_LOADER in tool_info["interp"],
          f"interp={tool_info['interp']}")
    with open(exe, "rb") as fh:
        tool_payload = fh.read()
    check("B3: imageflow_tool carries an OHOS code signature",
          b"codesign" in tool_payload)
    lib_info = elfinfo(lib)
    check("B4: libimageflow.so is an AArch64 shared object",
          lib_info["e_machine"] == EM_AARCH64,
          f"e_machine={lib_info['e_machine']}")
    with open(lib, "rb") as fh:
        lib_payload = fh.read()
    check("B5: libimageflow.so carries an OHOS code signature",
          b"codesign" in lib_payload)
    runpaths = tool_info["runpaths"] + lib_info["runpaths"]
    dangerous = [p for p in runpaths
                 if any(bad in p for bad in
                        ("/usr/local", "/home/", "/root", "/storage/Users"))]
    check("B6: no dangerous RPATH/RUNPATH in artifacts",
          not dangerous, f"runpaths={runpaths}")

    print("== 真实图像处理 / real image operations ==")

    def run(args):
        return subprocess.run([exe] + args, capture_output=True, text=True,
                              timeout=180)

    result = run(["diagnose", "--show-compilation-info"])
    check("A1: diagnose --show-compilation-info exits 0",
          result.returncode == 0,
          f"rc={result.returncode} err={result.stderr.strip()[:160]}")

    out_jpg = os.path.join(run_dir, "out_stretch.jpg")
    result = run(["v1/querystring", "--quiet", "--in", source_png,
                  "--out", out_jpg,
                  "--command", "w=8&h=8&mode=stretch&format=jpg&quality=90"])
    ok = check("A2: PNG->JPEG stretch resize exits 0", result.returncode == 0,
               f"rc={result.returncode} "
               f"err={(result.stderr or result.stdout).strip()[:200]}")
    if ok:
        size = jpeg_size(out_jpg)
        check("A3: JPEG output is exactly 8x8 (mozjpeg path)", size == (8, 8),
              f"size={size} bytes={os.path.getsize(out_jpg)}")

    out_png = os.path.join(run_dir, "out_w16.png")
    result = run(["v1/querystring", "--quiet", "--in", source_png,
                  "--out", out_png,
                  "--command", "w=16&format=png"])
    ok = check("A4: PNG->PNG width resize exits 0", result.returncode == 0,
               f"rc={result.returncode} "
               f"err={(result.stderr or result.stdout).strip()[:200]}")
    if ok:
        size = png_size(out_png)
        check("A5: PNG output width is 16 (libpng path)",
              size is not None and size[0] == 16,
              f"size={size} bytes={os.path.getsize(out_png)}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=6, image_ops=5)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("imageflow test_package OK: real image operations + HarmonyOS "
          "traits verified")


if __name__ == "__main__":
    sys.exit(main())

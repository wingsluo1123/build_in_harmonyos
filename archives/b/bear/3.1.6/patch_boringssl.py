#!/usr/bin/env python3
"""Patch boringssl CMakeLists.txt for HarmonyOS compatibility."""
import os
import sys

cmake_file = os.path.join(
    os.environ.get("TP_DIR", os.getcwd() + "/third_party"),
    "boringssl-with-bazel",
    "CMakeLists.txt"
)

if not os.path.exists(cmake_file):
    # Try relative path
    cmake_file = os.path.join("third_party", "boringssl-with-bazel", "CMakeLists.txt")

if not os.path.exists(cmake_file):
    print("ERROR: boringssl CMakeLists.txt not found", file=sys.stderr)
    sys.exit(1)

with open(cmake_file, "r") as f:
    content = f.read()

patches_applied = 0

# Fix 1: Replace FATAL_ERROR "Unknown processor" with aarch64 fallback
old1 = 'message(FATAL_ERROR "Unknown processor:" ${CMAKE_SYSTEM_PROCESSOR})'
new1 = 'set(ARCH "aarch64")'
if old1 in content:
    content = content.replace(old1, new1)
    patches_applied += 1
    print("  Patched: Unknown processor -> aarch64 fallback")

# Fix 2: HarmonyOS is not detected as UNIX by CMake, so boringssl falls
# through to the Windows ASM_NASM branch. Add HarmonyOS to the UNIX check.
old2 = "if(NOT OPENSSL_NO_ASM)\n  if(UNIX)"
new2 = 'if(NOT OPENSSL_NO_ASM)\n  if(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")'
if old2 in content:
    content = content.replace(old2, new2)
    patches_applied += 1
    print("  Patched: Added HarmonyOS to UNIX check for ASM")

if patches_applied == 0:
    print("  No patches needed (already patched or pattern not found)")
else:
    with open(cmake_file, "w") as f:
        f.write(content)
    print(f"Boringssl patched ({patches_applied} fixes applied).")

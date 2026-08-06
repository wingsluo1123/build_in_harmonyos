#!/usr/bin/env python3
"""Test script for extract-dtb — creates a dummy kernel image with DTB header and verifies extraction.

This test creates a minimal file containing a DTB header (0xD00DFEED) and verifies
that extract-dtb can find and extract the appended DTB.
"""
import os
import sys
import tempfile
import subprocess
import shutil

# DTB magic header
DTB_HEADER = b"\xd0\x0d\xfe\xed"


def main():
    # Create a dummy "kernel image" with an appended DTB header
    # The file consists of: some kernel bytes + DTB header + DTB content
    kernel_data = b"\x00" * 1024  # dummy kernel data
    dtb_data = DTB_HEADER + b"\x00" * 512  # dummy DTB with header

    with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
        f.write(kernel_data)
        f.write(dtb_data)
        img_path = f.name

    output_dir = tempfile.mkdtemp()

    try:
        # Test: extract-dtb -n (info only, no extraction)
        result = subprocess.run(
            [sys.executable, "-m", "extract_dtb.extract_dtb", "-n", img_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"FAIL: extract-dtb -n failed: {result.stderr}")
            sys.exit(1)
        if "appended dtbs" not in result.stdout:
            print(f"FAIL: expected 'appended dtbs' in output, got: {result.stdout}")
            sys.exit(1)
        print(f"INFO: {result.stdout.strip()}")

        # Test: extract-dtb (actual extraction)
        result = subprocess.run(
            [sys.executable, "-m", "extract_dtb.extract_dtb", img_path, "-o", output_dir],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"FAIL: extract-dtb extraction failed: {result.stderr}")
            sys.exit(1)
        if "Extracted" not in result.stdout:
            print(f"FAIL: expected 'Extracted' in output, got: {result.stdout}")
            sys.exit(1)
        print(f"INFO: {result.stdout.strip()}")

        # Verify extracted files exist
        extracted_files = os.listdir(output_dir)
        if not extracted_files:
            print("FAIL: no files extracted")
            sys.exit(1)
        print(f"INFO: Extracted files: {extracted_files}")

        print("ALL TESTS PASSED")
    finally:
        os.unlink(img_path)
        shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

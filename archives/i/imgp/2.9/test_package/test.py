#!/usr/bin/env python3
"""test_package/test.py — imgp smoke test for CI L0c compliance.

Tests that imgp can be imported and its CLI command works.
Includes a real image processing test to verify functionality.
"""
import os
import sys
import tempfile
import shutil


def test_import():
    """Test 1: Verify imgp can be imported as a Python module."""
    import imgp  # noqa: F401
    print(f"imgp version: {imgp._VERSION_}")
    print("✅ imgp import OK")


def test_cli():
    """Test 2: Verify imgp CLI works (--help)."""
    rc = os.system("imgp --help")
    assert rc == 0, "imgp --help failed"
    print("✅ imgp CLI --help OK")


def test_image_processing():
    """Test 3: Create a test PNG and verify imgp can process it (in-place)."""
    from PIL import Image

    tmpdir = tempfile.mkdtemp()
    try:
        src = os.path.join(tmpdir, "test.png")

        img = Image.new("RGB", (100, 100), color="red")
        img.save(src)

        # Verify the file was created
        assert os.path.getsize(src) > 0, "Source PNG not created"
        print(f"Test PNG created: {src} ({os.path.getsize(src)} bytes)")

        # Run imgp to resize the image in-place (imgp has no -o output flag)
        rc = os.system(f"imgp -x 50% {src}")
        assert rc == 0, "imgp resize failed"
        assert os.path.isfile(src), "Resized image not found"
        print(f"Resized image size: {os.path.getsize(src)} bytes")
        print("✅ imgp image processing OK")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    test_import()
    test_cli()
    test_image_processing()
    print("\n✅ All imgp tests passed")
# Test Report — extract-dtb 1.2

**Date**: 2026-08-06
**Status**: PASS

## Test Environment
- OS: HarmonyOS (OHOS 6.0)
- Arch: armv8 (aarch64)
- Python: 3.12.9
- Build system: setuptools (pip install)

## Test Results

### 1. extract-dtb --version
```
$ extract-dtb --version
1.2
```
✅ PASS

### 2. extract-dtb --help
```
$ extract-dtb --help
usage: extract-dtb [-h] [-o OUTPUT_DIR] [-n] [-V] filename

Extract dtbs from kernel images.

positional arguments:
  filename       Android kernel image

options:
  -h, --help     show this help message and exit
  -o OUTPUT_DIR  Output directory
  -n             Do not extract, just output information
  -V, --version  show program's version number and exit
```
✅ PASS

### 3. Conan create (G2 verification)
- conan create with ohos-aarch64 profile: PASS
- Package built and test_package passed

### 4. Local CI simulation (W3)
- setup.sh: PASS
- build_and_test.sh: PASS

## Patch Applied
- `0001-extract_dtb-extract_dtb.py.patch`: Adds `__version__ = "1.2"` to fix --version/--help crash

## Notes
- Pure Python package, no C/C++ compilation required
- `file` command not available on OHOS (platform limitation, non-blocking)
- Source bug: `__version__` variable was undefined in `extract_dtb.py`, causing NameError when using --version/--help

---
**Conclusion**: All tests passed. Package is ready for submission.

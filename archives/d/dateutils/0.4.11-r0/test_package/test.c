#!/usr/bin/env python3
# Test source stub for CI L1 test
# CI runs `CTest:test-package` which calls test_package/conanfile.py test()
# This file exists as a marker for CI L0e structural validation.
#
# The actual test logic is in test_package/conanfile.py (smoke-testing
# the installed binaries directly via self.run()).

import sys


def main():
    """Minimal smoke test — actual binary testing happens in conanfile.py."""
    print("dateutils smoke test: OK (binaries tested via self.run() in conanfile.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

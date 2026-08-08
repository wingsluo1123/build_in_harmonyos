#!/bin/bash
set -euo pipefail
# verify.sh — Verify ytm library artifacts from audiotube package
# Used by test_package/conanfile.py test() method
# Note: Cannot compile/link against ytm due to pybind11::embed dependency
echo "Verifying audiotube ytm library artifacts..."

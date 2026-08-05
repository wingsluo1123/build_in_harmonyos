#!/bin/bash
# Fetch gRPC v1.49.2 submodules (which are not included in the release tarball)
# This script runs in the gRPC source directory (working dir = extracted grpc source)
set -e
export TP_DIR="${PWD}/third_party"

fetch() {
    local name="$1" url="$2" sha="$3" dir="$4"
    local archive="${TMPDIR:-/storage/Users/currentUser/tmp}/grpc-sub-${name}.tar.gz"
    echo "Fetching submodule: $name ($sha)"
    for i in 1 2 3; do
        if curl -fsSL -o "$archive" "https://github.com/${url}/archive/${sha}.tar.gz"; then
            break
        fi
        echo "  Retry $i..."
        sleep 3
    done
    if [ ! -s "$archive" ]; then
        echo "ERROR: Failed to download $name" >&2
        return 1
    fi
    mkdir -p "$dir"
    rm -rf "$dir"/*
    tar xzf "$archive" -C "$dir" --strip-components=1
    rm -f "$archive"
}

fetch "abseil-cpp" "abseil/abseil-cpp" "273292d1cfc0a94a65082ee350509af1d113344d" "${TP_DIR}/abseil-cpp"
fetch "boringssl" "google/boringssl" "b9232f9e27e5668bc0414879dcdedb2a59ea75f2" "${TP_DIR}/boringssl-with-bazel"
fetch "protobuf" "protocolbuffers/protobuf" "24487dd1045c7f3d64a21f38a3f0c06cc4cf2edb" "${TP_DIR}/protobuf"
fetch "re2" "google/re2" "8e08f47b11b413302749c0d8b17a1c94777495d5" "${TP_DIR}/re2"
fetch "zlib" "madler/zlib" "04f42ceca40f73e2978b50e93806c2a18c1281fc" "${TP_DIR}/zlib"
fetch "cares" "c-ares/c-ares" "6654436a307a5a686b008c1d4c93b0085da6e6d8" "${TP_DIR}/cares/cares"

# Patch boringssl for HarmonyOS compatibility
echo "Patching boringssl for HarmonyOS..."
# The patch script is located in the bear source tree's third_party/grpc/ directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/patch_boringssl.py"

echo "All submodules fetched and patched successfully."

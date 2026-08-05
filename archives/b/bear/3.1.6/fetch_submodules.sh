#!/bin/sh
# fetch_submodules.sh - Download and extract grpc v1.49.2 submodules
# Run from the grpc source directory (extracted by ExternalProject)
# Uses codeload.github.com mirror (accessible from OHOS)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMPDIR="${TMPDIR:-/tmp}/grpc-submodules"
mkdir -p "$TMPDIR"

fetch_and_extract() {
    name="$1"
    url="$2"
    destdir="$3"

    if [ -f "$destdir/CMakeLists.txt" ]; then
        echo "[skip] $name already populated"
        return 0
    fi

    echo "[fetch] $name from $url"
    curl -sL --connect-timeout 30 -o "$TMPDIR/$name.tar.gz" "$url"

    echo "[extract] $name to $destdir"
    mkdir -p "$destdir"
    tar xzf "$TMPDIR/$name.tar.gz" -C "$destdir" --strip-components=1
    rm -f "$TMPDIR/$name.tar.gz"
    echo "[done] $name: $(find "$destdir" -type f | wc -l) files"
}

GRPC_SRC="$(pwd)"

fetch_and_extract abseil-cpp \
    "https://codeload.github.com/abseil/abseil-cpp/tar.gz/refs/tags/20220623.0" \
    "$GRPC_SRC/third_party/abseil-cpp"

fetch_and_extract boringssl \
    "https://codeload.github.com/google/boringssl/tar.gz/b9232f9e27e5668bc0414879dcdedb2a59ea75f2" \
    "$GRPC_SRC/third_party/boringssl-with-bazel"

fetch_and_extract c-ares \
    "https://codeload.github.com/c-ares/c-ares/tar.gz/6654436a307a5a686b008c1d4c93b0085da6e6d8" \
    "$GRPC_SRC/third_party/cares/cares"

fetch_and_extract protobuf \
    "https://codeload.github.com/protocolbuffers/protobuf/tar.gz/24487dd1045c7f3d64a21f38a3f0c06cc4cf2edb" \
    "$GRPC_SRC/third_party/protobuf"

fetch_and_extract re2 \
    "https://codeload.github.com/google/re2/tar.gz/8e08f47b11b413302749c0d8b17a1c94777495d5" \
    "$GRPC_SRC/third_party/re2"

fetch_and_extract zlib \
    "https://codeload.github.com/madler/zlib/tar.gz/04f42ceca40f73e2978b50e93806c2a18c1281fc" \
    "$GRPC_SRC/third_party/zlib"

echo "All submodules fetched successfully"

# Fix: Force CMAKE_CROSSCOMPILING=OFF so protoc generator expression is used
PROTOBUF_CMAKE="$GRPC_SRC/cmake/protobuf.cmake"
if [ -f "$PROTOBUF_CMAKE" ]; then
    sed -i 's/if(CMAKE_CROSSCOMPILING)/if(FALSE)/g' "$PROTOBUF_CMAKE"
    echo "Patched protobuf.cmake for cross-compilation protoc fix"
fi

# Fix: Same CMAKE_CROSSCOMPILING issue in grpc CMakeLists.txt for grpc_cpp_plugin
# The grpc_cpp_plugin target is defined at line 10864, but the if check is at line 499
# (inside a proto processing function that runs before the target is defined).
# So TARGET check won't work. Use if(FALSE) to always use the generator expression.
GRPC_CMAKELISTS="$GRPC_SRC/CMakeLists.txt"
if [ -f "$GRPC_CMAKELISTS" ]; then
    sed -i 's/if(CMAKE_CROSSCOMPILING)/if(FALSE)/g' "$GRPC_CMAKELISTS"
    echo "Patched CMakeLists.txt for cross-compilation grpc_cpp_plugin fix"
fi

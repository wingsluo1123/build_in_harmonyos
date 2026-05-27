#!/bin/bash
# cmake configure wrapper for libcbor 0.11.0
# This file is used by clean-verify G0 process
# Fixes CMake 4.x compatibility issue

cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DBUILD_SHARED_LIBS=OFF \
      -DWITH_TESTS=OFF \
      -DWITH_EXAMPLES=OFF \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_C_FLAGS="-fPIC -O2" \
      -B build \
      .

# cmake projects don't have separate configure step
# return success to continue build
exit 0

# Custom toolchain for OHOS local builds
# Sets CMAKE_SYSTEM_NAME=Linux so CMake recognizes the platform,
# and CMAKE_CROSSCOMPILING_EMULATOR so try_run() can execute binaries
# natively (since we're not actually cross-compiling on a DevBox).
set(CMAKE_SYSTEM_NAME "Linux")
set(CMAKE_SYSTEM_PROCESSOR "aarch64")
# We are on the target machine, so binaries can run directly.
# Using "env" as emulator prefix allows try_run() to execute test binaries.
set(CMAKE_CROSSCOMPILING_EMULATOR "/storage/Users/currentUser/.harmonybrew/bin/env")

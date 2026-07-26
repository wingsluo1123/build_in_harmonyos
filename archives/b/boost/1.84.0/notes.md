# Boost 1.84.0 OpenHarmony Conan adaptation

The recipe installs Boost headers and builds the compiled libraries required by
ecFlow: `Boost::program_options` and `Boost::date_time`. It is not a
header-only package.

Source: `https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.bz2`

SHA256: `cc4b893acf645c9d4b698e9a0f08ca8846aa5d6c68275c14c3e7949c24109454`

The old attempt was header-only. Its recorded evidence says b2 failed at
`tools/build/src/tools/common.jam:1164` while executing `clang++ --version`
through the Boost.Build SHELL mechanism; no compiled libraries were produced.

The new recipe uses the OHOS profile's real `/data/service/hnp/bin/clang` and
`clang++`, target `aarch64-linux-ohos`, libc++, and b2 `-j1`. It fails if b2
does not install either required library.

The Windows worktree has no OHOS clang/llvm toolchain, so full b2 and
test_package execution is blocked locally. Remote validation must run after
the branch is pushed, using:

`conan create archives/b/boost/1.84.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`

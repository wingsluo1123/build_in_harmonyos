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

## CI fix: libc++ `__config_site`

The first remote build failed because HNP clang found `libc++/v1/__config` but
could not find its generated `__config_site`. The recipe now discovers the
latest `/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot`, locates
`native/llvm/include/libcxx-ohos/include/c++/v1` and every `__config_site`
parent directory, and passes them explicitly to b2.

Compile flags now include `--sysroot`, `-nostdinc++`, libc++ v1 and config-site
`-isystem` directories, while link flags include the target sysroot and LLVM
target library directory. The same flags are exported through `cpp_info` so
the test_package and downstream CMake consumers use the identical OHOS
standard library configuration.

## CI fix: OHOS libc and Boost thread surface

The remote smoke matrix showed that the SDK libc++ rune table requires its
expected `__OHOS_FAMILY__=1` macro. OHOS libc does not provide
`strtoll_l`/`strtoull_l` or `pthread_setcancelstate`, so the recipe also uses
`-D_LIBCPP_HAS_NO_C_LOCALE` and `-DBOOST_DISABLE_THREADS`. These flags are in
the b2 compile configuration and are exported through `cpp_info` for the
consumer test and downstream CMake targets. `_LIBCPP_HAS_NO_LOCALIZATION` is
intentionally not used because it disables the required `<locale>` surface.

## CI fix: missing locale `_l` APIs

The next remote build showed that this SDK's `<locale>` does not honor
`_LIBCPP_HAS_NO_C_LOCALE`; it still references `strtoll_l` and `strtoull_l`,
which OHOS libc does not declare. The recipe now generates
`boost_ohos_locale_compat.h` and force-includes it for b2 and consumers. The
header is OHOS-guarded and maps those calls to `strtoll`/`strtoull`, ignoring
the locale argument. It is packaged under `include/` so consumer flags never
point back into a transient build directory.

The Windows worktree has no OHOS clang/llvm toolchain, so full b2 and
test_package execution is blocked locally. Remote validation must run after
the branch is pushed, using:

`conan create archives/b/boost/1.84.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`

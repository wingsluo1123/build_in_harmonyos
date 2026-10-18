# Siconos for HarmonyOS

The 4.4.0 recipe builds the six upstream native components: externals, numerics,
kernel, control, mechanics and io. Fortran is enabled using flang-ohos/20.1.0.
Published OpenBLAS, GMP and Boost supply the actual math/header dependencies;
upstream CXSparse/LDL sources preserve sparse functionality. Python bindings,
optional Bullet/OCE mechanisms and serialization are outside this configuration.

```sh
conan create archives/s/siconos/4.4.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build='siconos/*' --user=ohpcd --channel=stable
```

CMakeDeps consumers use `find_package(siconos CONFIG REQUIRED)` and the public
`Siconos::numerics`, `Siconos::kernel`, `Siconos::control`, `Siconos::mechanics`
and `Siconos::io` targets. The installed native CMake config is also usable with
the package and dependency prefixes. Run consumers in the Conan runtime
environment so shared dependency libraries are discoverable.

`bin/siconos` is a Python3 helper for compiling/running native C++ drivers. Its
version output is a smoke check; the numerical consumers exercise actual APIs.
This package does not supply the optional Python bindings.

The complete native upstream suite runs during the build. Its original
reference failures remain visible as FAIL with their real CTest exit code;
only precisely reproduced Linux reference limitations can satisfy the explicit
build acceptance policy. Package build success does not mean upstream100%.
See the version test report and `validation/reference-policy.json` for the
exact scope, case identities and original failure semantics.

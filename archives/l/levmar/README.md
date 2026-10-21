# levmar

levmar is a C/C++ implementation of the Levenberg-Marquardt algorithm for
non-linear least squares problems. It provides double and single precision
variants with analytic or finite-difference Jacobians, plus box, linear
equation and linear inequality constrained flavours.

## OHOS adaptation

- Builds the official 2.6 release tarball with its upstream CMake project.
- Injects `CMAKE_POLICY_VERSION_MINIMUM=3.5` because the upstream project still
  declares `cmake_minimum_required(VERSION 2.6)`, which CMake 4.x rejects.
- Builds with `HAVE_LAPACK=0`: the OHOS sysroot ships no LAPACK/BLAS, so the
  self-contained LU based solvers are used and the package has no dependency.
- Stages the static library, the `configure_file` generated public header and
  the licence explicitly, since upstream defines no `install()` rules.
- Runs the upstream `lmdemo` example program as a smoke test and the
  `test_package` consumer for the public API.

## Dependencies

None. `libm` is taken from the platform C runtime.

# ittapi 3.28.2

- Builds the static `ittnotify` and `jitprofiling` libraries.
- Enables the upstream C++ wrapper so its eight standalone upstream tests are
  compiled, packaged, and executed by `test_package`.
- Disables IPT, Fortran, and the reference collector to avoid optional platform
  dependencies that are not part of the base API.
- Official OHOS test and CI results remain pending.

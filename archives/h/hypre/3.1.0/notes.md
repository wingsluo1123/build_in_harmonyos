# hypre 3.1.0

- Builds a static sequential CPU library with internal BLAS and LAPACK.
- Compiles the upstream IJ, Struct, and SStruct solver test groups.
- Requires all three registered upstream CTest groups to run during the Conan
  build; non-runnable cross-build configurations fail explicitly instead of
  silently skipping the upstream tests.
- The consumer verifies initialization, the exact 3.1.0 version tuple, and
  finalization.
- Upstream CTest pass rate is gated by the Conan build: all 3 registered
  upstream groups must pass, otherwise CI fails.

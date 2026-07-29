# CGAL 6.1.1 adaptation notes

## Build configuration

- Build system: header-only Conan recipe
- Source: official `CGAL-6.1.1-library.tar.xz` release asset
- Status: built
- Patches: none

## Packaging

The recipe installs the upstream `include/CGAL` tree without compiling a
binary library. The Conan package exports the `CGAL::CGAL` CMake target and
clears its package ID because the packaged files are architecture-independent.

## Dependency boundary

The core package has no mandatory build-time dependency. Individual CGAL
algorithms can require Boost, GMP, MPFR, Eigen, or Qt. Those optional consumer
dependencies are not bundled or downloaded by this recipe.

## Verification

The Conan `test_package` resolves `CGAL::CGAL`, includes the installed
`CGAL/version.h`, and verifies that the packaged version is 6.1.1 or newer.
Removing the package include directory makes the test fail at compile time.

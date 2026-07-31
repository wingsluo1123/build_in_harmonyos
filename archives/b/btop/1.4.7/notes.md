# Adaptation Notes for btop 1.4.7

## Source
- Repository: https://github.com/aristocratos/btop
- License: Apache-2.0
- Build system: makefile

## Build Steps
1. Download source tarball from GitHub releases
2. Build using `make` with CXX and CXXFLAGS from Conan conf (R33)
3. Use -j1 to avoid parallel build issues (R9)
4. Package the generated `btop` binary into `bin/`

## Dependencies
- C++17 compatible compiler
- Make
- System libraries: typically ncurses (detected at build time by the Makefile)

## Notes
- btop uses a custom Makefile; no autotools/CMake involved.
- The binary is statically linked where possible by upstream; runtime dependencies are minimal.
- Test package verifies the binary exists and executes.

# pagetools 0.1 HarmonyOS PC adaptation notes

## Build environment
- Build system: GNU Makefile (raw, no autotools/cmake/meson)
- Compiler: Clang (cross-compile for aarch64)
- Target: HarmonyOS PC aarch64
- Dependencies: netpbm/10.73.42, libtiff/4.7.2

## Build steps

The upstream Makefile is invoked directly with Conan-provided compiler paths and dependency
include/library paths. Key overrides:
- `CXX=` sets the C++ compiler from Conan profile
- `AR=` sets the archiver from Conan profile
- `C++_FLAGS=` adds -fPIC -O2 plus dependency include paths
- `LDFLAGS=` adds dependency library paths
- `LIBPBM=netpbm` overrides the default 'pbm' library name

## Problems and solutions

| Problem | Root cause | Solution |
|---|---|---|
| Makefile uses $(C++) as variable name | $(C++) cannot be overridden via make command line (special characters) | Patch to rename $(C++) to $(CXX) |
| Link commands lack LDFLAGS | Makefile hard-codes -l flags without library search paths | Patch to add $(LDFLAGS) to both link commands |
| LIBPBM defaults to 'pbm' | Upstream Makefile has LIBPBM = pbm; Debian uses netpbm | Override LIBPBM=netpbm on make command line |
| No -fPIC in upstream flags | Static libs built without -fPIC cannot be linked into shared objects on OHOS | Add -fPIC to C++_FLAGS override |
| Missing dependency headers | Clean build environment has no system netpbm/tiff headers | Inject include paths from Conan dependency cpp_info |

## Upstream tests

pagetools 0.1 has no test directory, test target, or automated test command. The two
executables (pbm_findskew, tiff_findskew) produce usage text when invoked without arguments,
which serves as a basic smoke test.

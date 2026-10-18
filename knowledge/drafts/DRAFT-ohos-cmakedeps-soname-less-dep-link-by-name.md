# DRAFT-ohos-cmakedeps-soname-less-dep-link-by-name - Link SONAME-less Conan dependencies by bare name in the upstream CMakeLists

> **Contributor**: GoliWie | **Status**: VERIFIED DRAFT | **Updated**: 2026-10-17
> **Severity**: medium | **Category**: cmake / conan CMakeDeps / linking / SONAME relocatability / OHOS packaging
> **First hit**: `target-factory/2.5` (PR !16506) — the recipe's own
> `libtarget-factory.so` recorded its dependencies' cache paths and was fixed at
> link time before CI reached the gate.

## Usage

Use this pattern when a Conan recipe on HarmonyOS PC links against a
**published** dependency package whose `.so` has no `DT_SONAME`, and the
resulting artifact records that dependency's absolute Conan-cache path in
`DT_NEEDED`.

Confirm first:

```console
$ readelf -d <dep_package>/lib/lib<dep>.so | grep SONAME      # empty -> no DT_SONAME
$ readelf -d <our_package>/lib/lib<name>.so | grep NEEDED     # entries starting with '/'
```

If both hold, the link line is using CMakeDeps' imported target and the linker
copied the path it was handed. This is linker semantics, not a Conan bug.

## Scope

- Any CMake project consuming registry packages without `DT_SONAME`
  (observed: `unilog`, `glog`, `gflags` in the ohpcd registry).
- Both the package's own `lib/*.so` and its `bin/*` executables.

Not applicable when the *built* library itself lacks a SONAME — that is the
CMake platform-module gap, covered by
`DRAFT-cmake-harmonyos-system-name-soname`.

## Symptom

```text
[FAIL] L5b: DT_NEEDED of libtarget-factory.so records a non-relocatable path
        /storage/Users/currentUser/.cache/conan2/p/unilo.../p/lib/libunilog.so
```

Locally everything loads (the cache path exists on the build machine); on a
clean worker the loader does not consult `LD_LIBRARY_PATH` or rpath for a
`NEEDED` containing `/`, so it fails before `main()`:

```text
Error loading shared library /storage/.../conan2/p/.../libunilog.so: No such file or directory
```

## Root cause

CMakeDeps exports `IMPORTED_LOCATION` as the absolute package path. For an
input with no `DT_SONAME`, `ld` writes the path exactly as given into
`DT_NEEDED`. `CMAKE_SKIP_RPATH` does not help: rpath only affects search, not
how a slash-containing `NEEDED` entry is resolved.

## Recommended fix (priority 1)

Hand the *names* and *search directories* to the upstream CMake code and link
by name; keep the imported target only for headers and compile definitions.

Recipe side:

```python
by_name, libdirs = [], []
for ref in ("unilog", "glog", "gflags"):
    dep = self.dependencies[ref]
    by_name.append(ref)
    libdirs.extend(os.path.join(dep.package_folder, d)
                   for d in dep.cpp_info.libdirs)
tc.variables["TARGET_FACTORY_SONAME_LIBS"] = ";".join(by_name)
tc.variables["TARGET_FACTORY_SONAME_LIBDIRS"] = ";".join(libdirs)
```

Patch side (`if`-guarded so non-OHOS builds keep the upstream line verbatim):

```cmake
if(TARGET_FACTORY_SONAME_LIBS)
  target_link_directories(${PROJECT_NAME} PUBLIC ${TARGET_FACTORY_SONAME_LIBDIRS})
  target_include_directories(${PROJECT_NAME} PUBLIC
    $<TARGET_PROPERTY:unilog::unilog,INTERFACE_INCLUDE_DIRECTORIES>)
  target_compile_definitions(${PROJECT_NAME} PUBLIC
    $<TARGET_PROPERTY:unilog::unilog,INTERFACE_COMPILE_DEFINITIONS>)
  target_link_libraries(${PROJECT_NAME} PUBLIC ${TARGET_FACTORY_SONAME_LIBS})
else()
  target_link_libraries(${PROJECT_NAME} PUBLIC unilog::unilog)   # upstream
endif()
```

Verify after `conan create`:

```console
$ readelf -d <package>/lib/lib<name>.so | grep NEEDED   # bare names only, no leading '/'
$ readelf -d <package>/bin/<tool>      | grep NEEDED
$ grep -r IMPORTED_NO_SONAME <package>/lib/cmake/       # empty
```

## Forbidden

- **`patchelf` / `elfedit` post-hoc rewrite of `DT_NEEDED` or `SONAME`.** On
  HMDFS the rewritten ELF refuses `mmap` (see `E537`): `readelf` looks perfect,
  the binary will not start, and any signature is invalidated.
- **Declaring the absolute path acceptable because the current CI layout
  resolves it.** The artifact stays non-relocatable; the L5b gate still fails.
- **Trying to fix this with `CMAKE_SKIP_RPATH` / `LD_LIBRARY_PATH`** — neither
  changes how a slash-containing `NEEDED` entry is opened.

## Fallback (priority 2, not a fix)

Repair the stale absolute paths in the test environment by recreating symlinks
from the recorded path to the dependency package's library, iterating over the
transitive closure (`DRAFT-13577-ohos-stale-absolute-dt-needed-cache-path`).
This keeps a local run green but ships an unfixable artifact.

# expat 2.8.2.1.1 shadow CI report

Date: 2026-08-07
Issue: 1912
Branch: feat/expat-2.8.2.1-1912

## Change

The previous `vips/8.18.4` shadow CI run failed while building `expat/2.8.2.1`:

```text
CMake Error: failed to create symbolic link 'libexpat.so.1': Permission denied
CMake Error: cmake_symlink_library: System Error: Permission denied
```

The failure happened in the CMake build tree before `package()`. The recipe now
sets `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` and keeps
`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,` so CMake builds/installs an
unversioned real `libexpat.so` without symlink creation, while preserving a
valid ELF SONAME.

Because `expat/2.8.2.1` is already published in the artifact registry, this fix
is published as the incremented package version `expat/2.8.2.1.1`.

## Verification

Device: `currentUser@10.62.189.79:2222`

Job directory:

```text
/storage/Users/currentUser/ohos-users/codex/expat-2.8.2.1.1-1912-20260807
```

Runner directory:

```text
/storage/Users/currentUser/ohos-test-runs/codex-2.8.2.1.1-expat-2.8.2.1.1-1912-api-20260807-conan-20260807-134642-37963
```

Command:

```sh
zsh ci/conan/build_and_test.sh archives/e/expat/2.8.2.1.1
```

Result:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content

Build Summary:
  Total:   1
  Success: 1
  Failed:  0
```

Additional checks:

- R37 version-collision check passed for `expat/2.8.2.1.1`.
- `cmake --build` linked `libexpat.so` successfully; no `libexpat.so.1` symlink
  was created.
- `cmake --install` installed `lib/libexpat.so` successfully.
- `binary-sign-tool` signed `libexpat.so` successfully.
- `test_package` built and executed `dlopen(.../libexpat.so)` successfully,
  then resolved and called `XML_ParserCreate`, `XML_Parse`, and
  `XML_ParserFree` against a minimal XML document.
- Negative test moved `lib/` and `include/` away and confirmed the test package
  genuinely depends on expat.
- `llvm-readelf -d libexpat.so` reports:

```text
0x000000000000000e (SONAME) Library soname: [libexpat.so]
```

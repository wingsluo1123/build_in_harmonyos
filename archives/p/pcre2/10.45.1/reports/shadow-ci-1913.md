# pcre2 10.45.1 shadow CI report

Date: 2026-08-07
Issue: 1913
Branch: feat/pcre2-10.45-1913

## Change

The first PR revision modified `pcre2/10.45`, but CI reported that version was
already published. The HarmonyOS configure permission workaround has therefore
been carried on the existing follow-up package version `pcre2/10.45.1`.

The recipe restores executable bits for autotools helper scripts copied into
the Conan work directories, then runs `configure` through `sh`. This avoids the
HarmonyOS package workspace failure where invoking `configure` directly can hit
`Permission denied`.

## Verification

Device: `currentUser@10.62.189.79:2222`

Job directory:

```text
/storage/Users/currentUser/ohos-users/codex/pcre2-10.45.1-1913-20260807
```

Runner directory:

```text
/storage/Users/currentUser/ohos-test-runs/codex-10.45.1-pcre2-10.45.1-1913-20260807-conan-20260807-140010-46553
```

Command:

```sh
zsh ci/conan/build_and_test.sh archives/p/pcre2/10.45.1
```

Result:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: pcre2-config version/help failed, pcre2grep --version OK, pcre2test --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content

Build Summary:
  Total:   1
  Success: 1
  Failed:  0
```

Additional checks:

- `configure` ran through `sh` and completed without the previous permission
  failure.
- Static libraries `libpcre2-8.a`, `libpcre2-16.a`, `libpcre2-32.a`, and
  `libpcre2-posix.a` were packaged.
- `test_package` built and executed successfully.
- Negative test moved `bin/`, `lib/`, and `include/` away and confirmed the
  test package genuinely depends on pcre2.

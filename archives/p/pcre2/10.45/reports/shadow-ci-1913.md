# pcre2/10.45 Shadow CI Report (#1913)

Date: 2026-08-07

## Scope

- Package: `archives/p/pcre2/10.45`
- Branch: `feat/pcre2-10.45-1913`
- Device: `currentUser@10.62.189.79:2222`
- Job base: `/storage/Users/currentUser/ohos-users/codex/pcre2-10.45-1913-20260807`
- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-10.45-pcre2-10.45-1913-20260807-conan-20260807-125547-7005`

## Fix

The OHOS/HMDFS build directory rejects direct execution of the extracted autotools
`configure` script with `Permission denied`, even after execute bits are present.
The recipe now restores autotools script modes and runs configure through the shell:

```text
sh "<source_folder>/configure" <AutotoolsToolchain args>
```

`make` and `make install` continue to use Conan's `Autotools` helper.

## Result

- `conan create`: passed
- `test_package`: passed, `test_pcre2` executed through CTest
- R34 negative test: passed, removing package artifacts makes the test fail as expected
- L0: pass
- L1: pass
- L2: pass (`pcre2grep --version` and `pcre2test --version`; `pcre2-config` warning is non-blocking)
- L4: pass
- L5: pass (`bin/` has content)

Exit code: `0`

## Notes

This unblocks the next `vips/8.18.4` shadow CI attempt after the dependent PR is available.

# Test Report — Gauche 0.9.15.1

## Conan Clean Build Verification

- **Platform**: OpenHarmony OHOS aarch64
- **Build system**: autotools
- **Command**: `conan create archives/g/gauche/0.9.15.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- **Result**: PASS — package created successfully; full package reference is `gauche/0.9.15.1@ohpcd/stable#c25387f136b1703a2cccedff5f14e9f1:6b129b068851896169fae42d399fa922d239ce8a#e81e371cbb45ebe5ec5ddbbb8964a5c7`

## Package Test

Conan `test_package` compiled and ran `test_gauche` successfully:

```text
1/1 Test #1: test_gauche ... Passed
100% tests passed, 0 tests failed out of 1
```

## Gate Summary

- G0: PASS
- G1: PASS
- G2: PASS
- G3: PASS
- G4: PASS
- L2: PASS
- L4: PASS
- L5: PASS

See `reports/conan-verify-report.md` and `reports/conan-create.log` for command output.

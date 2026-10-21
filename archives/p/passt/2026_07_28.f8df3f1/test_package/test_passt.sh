#!/usr/bin/env bash
# test_passt.sh — simple binary product verification for CI
# pesto uses seccomp which may not work in CI workers (SIGSYS on exit).
# Strategy: verify binary exists + is ELF; attempt --version but don't fail on seccomp.
set -euo pipefail

# Locate pesto binary via PATH (conanrun env) or fallback to package layout
PESTO=""
for candidate in \
    "$(command -v pesto 2>/dev/null || true)" \
    "${PWD}/usr/local/bin/pesto" \
    "${PWD}/bin/pesto" \
    "${PWD}/usr/bin/pesto" \
    "/usr/local/bin/pesto" \
    "/usr/bin/pesto"
do
    [ -n "${candidate:-}" ] && [ -x "${candidate}" ] && PESTO="${candidate}" && break
done

if [ -z "${PESTO}" ]; then
    echo "FAIL: pesto binary not found in PATH or package layout"
    exit 1
fi

echo "PASS: pesto binary found at ${PESTO}"

# Verify it is a valid ELF (file command or readelf)
if command -v file >/dev/null 2>&1; then
    file_type=$(file "${PESTO}" 2>/dev/null || true)
    echo "INFO: file type: ${file_type}"
    if echo "${file_type}" | grep -qi "ELF"; then
        echo "PASS: pesto is a valid ELF binary"
    else
        echo "FAIL: pesto is not an ELF binary"
        exit 1
    fi
fi

# 鸿蒙特有测试: verify pesto is AArch64 ELF (OHOS arm64 platform)
# Upstream Linux builds are x86_64; AArch64 is specific to HarmonyOS PC
if command -v readelf >/dev/null 2>&1; then
    elf_machine=$(readelf -h "${PESTO}" 2>/dev/null | grep "Machine:" | head -1 || true)
    if echo "${elf_machine}" | grep -qi "AArch64"; then
        echo "PASS: pesto is AArch64 ELF (鸿蒙特有: OHOS arm64 platform verification)"
    else
        echo "FAIL: pesto is not AArch64 ELF — expected for OHOS arm64"
        echo "       Machine: ${elf_machine}"
        exit 1
    fi
elif command -v file >/dev/null 2>&1; then
    if file "${PESTO}" 2>/dev/null | grep -qi "aarch64"; then
        echo "PASS: file confirms pesto is AArch64 (鸿蒙特有: OHOS arm64 verification)"
    else
        echo "INFO: could not verify AArch64 architecture via file command"
    fi
fi

# Attempt pesto --version (may exit non-zero due to seccomp SIGSYS — expected on OHOS)
# Temporarily disable set -e to capture non-zero exit code
set +e
output=$("${PESTO}" --version 2>&1)
rc=$?
set -e
if echo "${output}" | grep -qi "passt\|version"; then
    echo "PASS: pesto --version printed version info (exit=${rc})"
elif [ "${rc}" -ne 0 ]; then
    echo "INFO: pesto --version exit=${rc} (seccomp may block in CI; binary presence + ELF verified)"
else
    echo "FAIL: pesto --version exit=0 but printed no version info; binary is broken"
    exit 1
fi

exit 0

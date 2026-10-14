#!/system/bin/sh
#
# OHOS-specific package assertions for pappl 1.4.12.
# Usage: test_pappl_ohos.sh <package_folder>
#
set -u
PKG="${1:?package folder required}"
pass=0
fail=0

check() {
  # check <description> <shell command...> (run via sh -c)
  desc="$1"
  shift
  if /system/bin/sh -c "$*" >/dev/null 2>&1; then
    echo "PASS: $desc"
    pass=$((pass + 1))
  else
    echo "FAIL: $desc"
    fail=$((fail + 1))
  fi
}

# Resolve a symbol dumper: nm (PATH), llvm-nm, or plain grep fallback.
nm_tool=""
if command -v nm >/dev/null 2>&1; then
  nm_tool="nm"
elif command -v llvm-nm >/dev/null 2>&1; then
  nm_tool="llvm-nm"
fi

check_symbol() {
  # check_symbol <description> <symbol>
  lib="$PKG/lib/libpappl.a"
  if [ -n "$nm_tool" ]; then
    "$nm_tool" "$lib" 2>/dev/null | grep -q " $2\$"
  else
    grep -aq "$2" "$lib" 2>/dev/null
  fi
}

# 1. Static library is packaged.
check "libpappl.a exists" "test -f '$PKG/lib/libpappl.a'"

# 2-6. Public headers are installed.
for header in pappl.h base.h system.h printer.h device.h; do
  check "header pappl/$header installed" "test -f '$PKG/include/pappl/$header'"
done

# 7. pkg-config metadata is installed and references -lpappl.
check "pappl.pc packaged" "test -f '$PKG/lib/pkgconfig/pappl.pc'"
check "pappl.pc links -lpappl" "grep -q -- -lpappl '$PKG/lib/pkgconfig/pappl.pc'"

# 9-12. Core public symbols are present in the static archive.
for symbol in papplSystemCreate papplMainloop papplPrinterSetUSB papplDeviceOpen; do
  desc="symbol $symbol in libpappl.a"
  if check_symbol "" "$symbol"; then
    echo "PASS: $desc"
    pass=$((pass + 1))
  else
    echo "FAIL: $desc"
    fail=$((fail + 1))
  fi
done

# 13. Web interface resources are packaged.
check "share/pappl/style.css packaged" "test -f '$PKG/share/pappl/style.css'"

# 14. DNS-SD support compiled in (dns_sd client path).
if check_symbol "" "_papplDNSSDInit"; then
  echo "PASS: DNS-SD support compiled in"
  pass=$((pass + 1))
else
  echo "FAIL: DNS-SD support compiled in"
  fail=$((fail + 1))
fi

# 15. USB printer gadget backend compiled in.
if check_symbol "" "_papplPrinterRunUSB"; then
  echo "PASS: USB gadget support compiled in"
  pass=$((pass + 1))
else
  echo "FAIL: USB gadget support compiled in"
  fail=$((fail + 1))
fi

echo "PAPPL_OHOS_ASSERTIONS=$pass PASSED, $fail FAILED"
test "$fail" -eq 0 -a "$pass" -eq 15

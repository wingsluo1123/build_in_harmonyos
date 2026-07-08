#!/bin/sh
# test_package/test_eksblowfish.sh — 烟雾测试脚本
# 验证 Crypt::Eksblowfish 模块的文件结构和 ELF 有效性
# 此脚本由 test_package/conanfile.py 的 test() 方法间接引用

set -e

SO_PATH="${1:-}"
if [ -z "$SO_PATH" ]; then
    echo "Usage: $0 <path_to_Eksblowfish.so>"
    exit 1
fi

echo "[test] Checking Eksblowfish.so existence..."
if [ ! -f "$SO_PATH" ]; then
    echo "[FAIL] Eksblowfish.so not found at: $SO_PATH"
    exit 1
fi
echo "[OK] Eksblowfish.so exists"

echo "[test] Checking ELF format..."
file "$SO_PATH" | grep -q "ELF" || {
    echo "[FAIL] Not a valid ELF file"
    exit 1
}
echo "[OK] Valid ELF shared object"

echo "[test] Checking AArch64 architecture..."
file "$SO_PATH" | grep -q "arm64" || {
    echo "[FAIL] Not an AArch64 binary"
    exit 1
}
echo "[OK] AArch64 architecture confirmed"

echo "[test] Checking NEEDED dependencies..."
readelf -d "$SO_PATH" 2>/dev/null | grep -q "NEEDED" && {
    readelf -d "$SO_PATH" 2>/dev/null | grep "NEEDED"
    echo "[OK] Dependencies found"
} || {
    echo "[WARN] No NEEDED entries (may be normal for some modules)"
}

echo "[test] Checking boot_Crypt__Eksblowfish export symbol..."
nm -D "$SO_PATH" 2>/dev/null | grep -q "boot_Crypt__Eksblowfish" && {
    echo "[OK] boot_Crypt__Eksblowfish symbol exported"
} || {
    echo "[FAIL] boot_Crypt__Eksblowfish symbol not found"
    exit 1
}

echo "[test] Checking security features (NX/RELRO/BIND_NOW)..."
readelf -l "$SO_PATH" 2>/dev/null | grep -q "GNU_STACK" && {
    if readelf -l "$SO_PATH" 2>/dev/null | grep "GNU_STACK" | grep -q "RWE"; then
        echo "[WARN] GNU_STACK has RWE (NX disabled)"
    else
        echo "[OK] NX enabled (GNU_STACK without RWE)"
    fi
}
readelf -d "$SO_PATH" 2>/dev/null | grep -q "BIND_NOW" && {
    echo "[OK] BIND_NOW enabled"
}
readelf -l "$SO_PATH" 2>/dev/null | grep -q "GNU_RELRO" && {
    echo "[OK] RELRO enabled"
}

echo ""
echo "[RESULT] All smoke tests PASSED"

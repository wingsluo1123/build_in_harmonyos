#!/bin/sh
# OCaml 4.14.1.1 smoke test — 验证编译器工具链版本
# OHOS hmmac 拒绝直执行 shebang 脚本，须由 conanfile.py 用显式解释器调用（/bin/sh test.sh）
# bin 目录由 conanfile.py 显式传入（$1），不依赖 PATH，无硬编码本机路径

set -e

BIN_DIR="$1"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin directory not provided or not found"
    exit 1
fi

fail=0

check_version() {
    tool="$1"
    if [ -x "$BIN_DIR/$tool" ]; then
        "$BIN_DIR/$tool" -version || fail=1
    else
        echo "FAIL: $tool not found in $BIN_DIR"
        fail=1
    fi
}

check_version ocaml
check_version ocamlc
check_version ocamlopt

if [ "$fail" -ne 0 ]; then
    echo "test.sh: OCaml toolchain smoke test FAILED"
    exit 1
fi

echo "test.sh: OCaml toolchain smoke test OK"
exit 0

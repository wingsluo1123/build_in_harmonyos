#!/usr/bin/env bash
# run_upstream_tests.sh — ublock 1.70.0 上游测试运行器
#
# 用法: run_upstream_tests.sh <uBlock-src-root>
#
# 上游真实测试入口（R51 清点，见 notes.md / test_package/MANIFEST.yml）：
#   platform/npm/test.js  ——  官方 mocha 入口，默认电池 = tests/wasm.js + tests/snfe.js
#   另有 tests/leaks.js（未被 test.js 收录）与 tests/request-data.js（`--full-battery` 可选）
#
# 注意：上游 test.js 用 promisify(spawn)('mocha', ...) 但不检查子进程退出码
# （实测 mocha 失败时 test.js 仍 exit 0），故本运行器直接调用 mocha 以取得
# 真实退出码与逐项计数，并保留每个用例名称到日志。
#
# 环境变量：
#   UBO_NODE     显式指定 node 解释器（默认 PATH 上的 node）
#   UBO_NPM_CLI  显式指定 npm-cli.js（默认用 PATH 上的 npm；OHOS/CI 上按名执行
#                可能不可用，故配方会传入绝对 npm-cli.js）
#   UBO_SFT_SRC  scaling-palm-tree 源码目录（可选；提供后启用全量电池 request-data）
#   UBO_FULL_BATTERY=1  执行全量电池（request-data）；默认仅默认电池 + leaks
set -uo pipefail

SRC_ROOT="${1:?usage: run_upstream_tests.sh <uBlock-src-root>}"
PKG_DIR="$SRC_ROOT/dist/build/uBlock0.npm"
NODE_BIN="${UBO_NODE:-node}"

# npm 以 node + npm-cli.js 运行（绝对路径），避免按名 exec npm 在 OHOS/CI 上失败
if [ -n "${UBO_NPM_CLI:-}" ] && [ -f "${UBO_NPM_CLI:-}" ]; then
    NPM_CMD=("$NODE_BIN" "$UBO_NPM_CLI")
else
    NPM_CMD=(npm)
fi

cd "$PKG_DIR" || { echo "FATAL: $PKG_DIR not found"; exit 1; }

echo "=== [upstream] uBlock Origin 1.70.0 : platform/npm tests ==="
echo "node: $("$NODE_BIN" --version)"
echo "cwd : $(pwd)"

# ── 1. 材质化测试依赖（mocha + esm-world [ + scaling-palm-tree ]） ──
install_args=(mocha esm-world)
if [ -n "${UBO_SFT_SRC:-}" ] && [ -f "$UBO_SFT_SRC/requests.json" ]; then
    install_args+=("$UBO_SFT_SRC")
    echo "full-battery dep: scaling-palm-tree from $UBO_SFT_SRC"
fi
if ! "${NPM_CMD[@]}" install --no-save --ignore-scripts --no-audit --no-fund "${install_args[@]}" >/dev/null 2>&1; then
    echo "FATAL: npm install of test deps failed"
    exit 1
fi

MOCHA="./node_modules/.bin/mocha"
[ -x "$MOCHA" ] || { echo "FATAL: mocha not installed"; exit 1; }

run_mocha() {
    # run_mocha <logfile> <files...>
    # OHOS CI worker 偶发 `fork: retry: Resource temporarily unavailable`（进程/资源瞬时争用，
    # 实测默认电池首次 fork 失败、紧随其后的 leaks 却成功）。仅在「子进程未产出日志」或日志
    # 命中资源类瞬时错误时做**有界重试**，绝不吞掉真实测试失败。
    local log="$1"; shift
    local attempt rc
    for attempt in 1 2 3; do
        "$UBO_NODE" "$MOCHA" --experimental-vm-modules --no-warnings "$@" >"$log" 2>&1
        rc=$?
        [ "$rc" -eq 0 ] && return 0
        if [ ! -s "$log" ] || grep -qE "Resource temporarily unavailable|cannot fork|Cannot allocate memory" "$log"; then
            echo "  [retry ${attempt}/3] transient fork/resource error (rc=$rc), retry in $((attempt * 10))s..."
            sleep $((attempt * 10))
            continue
        fi
        return "$rc"
    done
    return 1
}

count() { grep -oE '[0-9]+ (passing|failing|pending)' "$1" 2>/dev/null | awk '{print $1, $2}'; }

# ── 2. 默认电池（官方 test.js --mocha 口径） ──
LOG_DEFAULT="upstream-mocha-default.log"
run_mocha "$LOG_DEFAULT" tests/wasm.js tests/snfe.js
RC_DEFAULT=$?
echo "--- default battery (wasm+snfe) rc=$RC_DEFAULT ---"
count "$LOG_DEFAULT"

# ── 3. leaks.js（未被 test.js 收录，但属上游测试资产） ──
LOG_LEAKS="upstream-leaks.log"
run_mocha "$LOG_LEAKS" tests/leaks.js
RC_LEAKS=$?
echo "--- leaks.js rc=$RC_LEAKS ---"
count "$LOG_LEAKS"

# ── 4. 全量电池（--full-battery，需 scaling-palm-tree）—— 仅记录，不作门禁 ──
RC_FULL=0
if [ "${UBO_FULL_BATTERY:-0}" = "1" ]; then
    if [ -f "./node_modules/scaling-palm-tree/requests.json" ]; then
        LOG_FULL="upstream-mocha-fullbattery.log"
        run_mocha "$LOG_FULL" tests/wasm.js tests/snfe.js tests/request-data.js
        RC_FULL=$?
        echo "--- full battery (request-data) rc=$RC_FULL ---"
        count "$LOG_FULL"
    else
        echo "--- full battery skipped: scaling-palm-tree/requests.json absent ---"
    fi
fi

# ── 5. 结论（门禁 = 默认电池 + leaks） ──
if [ "$RC_DEFAULT" -ne 0 ] || [ "$RC_LEAKS" -ne 0 ]; then
    echo "UPSTREAM_TESTS=FAIL"
    exit 1
fi
echo "UPSTREAM_TESTS=PASS"
exit 0

#!/bin/sh
# test_package/test.sh — ublock 1.70.0 消费者验证（L1 smoke test）
#
# 用法: test.sh <package_folder>
#
# 被测物 = Conan 资产包：
#   res/ublock/ubo-core/   @gorhill/ubo-core 静态网络过滤引擎 Node 库
#   res/ublock/chromium/   uBlock Origin 浏览器扩展
# 验证 = 布局存在性 + 内容锚点 + 扩展 manifest 版本 + 真实驱动引擎 API
# （consumer/engine_flow.mjs，R34 非空壳）。带 [OHOS] 标记为鸿蒙特有用例。
# 纯 POSIX sh；node 不可用时相应断言 [skip] 不计失败。
PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

RES="$PKG_FOLDER/res/ublock"
CORE="$RES/ubo-core"
EXT="$RES/chromium"
pass=0
fail=0
skip=0

ok()      { echo "  [ok] $1";   pass=$((pass + 1)); }
bad()     { echo "  [FAIL] $1"; fail=$((fail + 1)); }
skipped() { echo "  [skip] $1"; skip=$((skip + 1)); }
chk()     { name="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$name"; else bad "$name"; fi; }

# ───────────── node 解释器探测（要求 WebAssembly 可用） ─────────────
# uBO 引擎核心依赖 WebAssembly 制品。实测 `--jitless` 会让 V8 关闭可执行内存，
# 使 `WebAssembly is not defined`（上游 tests/wasm.js 即验证此点）——故 ublock
# **不能**用 --jitless。探针以「plain node + typeof WebAssembly === 'object'」
# 为准；不满足则 node 相关断言 [skip]（不计失败）。
PROBE_DIR="$(dirname "$0")"
PROBE_JS="$PROBE_DIR/.ubo-node-probe.$$.js"
printf 'if (typeof WebAssembly !== "object") process.exit(1);\nprocess.stdout.write(process.version);\n' > "$PROBE_JS" 2>/dev/null
NODE_BIN=""
for cand in "${UBO_NODE:-}" "$(command -v node 2>/dev/null)" \
            /data/service/hnp/node.org/*/bin/node /data/service/hnp/bin/node; do
    [ -n "$cand" ] || continue
    [ -x "$cand" ] || continue
    if "$cand" "$PROBE_JS" >/dev/null 2>&1; then NODE_BIN="$cand"; break; fi
done
rm -f "$PROBE_JS" 2>/dev/null

# ─────────────────── 1. 打包布局完整性 ───────────────────
chk "core index.js present"        test -s "$CORE/index.js"
chk "core package.json present"    test -s "$CORE/package.json"
chk "core js/ dir present"         test -d "$CORE/js"
chk "core lib/ dir present"        test -d "$CORE/lib"
chk "core wasm json (psl) present" test -s "$CORE/build/publicsuffixlist.json"
chk "extension manifest.json present" test -s "$EXT/manifest.json"
chk "extension background.html present" test -s "$EXT/background.html"
chk "extension js/ dir present"    test -d "$EXT/js"
chk "extension _locales present"   test -d "$EXT/_locales"
chk "licenses/LICENSE.txt present" test -s "$PKG_FOLDER/licenses/LICENSE.txt"

# ─────────────────── 2. 内容锚点 ───────────────────
chk "index.js exposes StaticNetFilteringEngine" \
    grep -q "StaticNetFilteringEngine" "$CORE/index.js"
chk "index.js exports enableWASM" \
    grep -q "enableWASM" "$CORE/index.js"
chk "LICENSE is GPLv3" \
    grep -qi "GNU GENERAL PUBLIC LICENSE" "$PKG_FOLDER/licenses/LICENSE.txt"

# ─────────────────── 3. [OHOS] 鸿蒙特有用例 ───────────────────
# OHOS 包管理器消费路径：res/ublock 下双制品（库 + 扩展）
if [ -f "$CORE/index.js" ] && [ -f "$EXT/manifest.json" ]; then
    ok "[OHOS] res/ublock layout (ubo-core + chromium extension)"
else
    bad "[OHOS] res/ublock layout"
fi

# 扩展 manifest 版本与上游一致（OHOS 浏览器加载扩展时的版本校验依据）
EXT_VER="$(grep -o '"version"[^,]*' "$EXT/manifest.json" 2>/dev/null | head -1 | sed 's/.*: *"//; s/".*//')"
if [ "$EXT_VER" = "1.70.0" ]; then
    ok "[OHOS] extension manifest version == 1.70.0"
else
    bad "[OHOS] extension manifest version (got '$EXT_VER')"
fi

# OHOS node 必须启用 JIT：WebAssembly 引擎可用（与 --jitless 不兼容）
if [ -n "$NODE_BIN" ]; then
    WASMTYPE="$("$NODE_BIN" -e 'process.stdout.write(typeof WebAssembly)' 2>/dev/null)"
    if [ "$WASMTYPE" = "object" ]; then
        ok "[OHOS] WebAssembly available under OHOS node (JIT-enabled)"
    else
        bad "[OHOS] WebAssembly available under OHOS node (got '$WASMTYPE')"
    fi
else
    skipped "[OHOS] WebAssembly available under OHOS node (node unusable)"
fi

# 上游 engines.node 约束 (>=18) 由 OHOS node 满足
if [ -n "$NODE_BIN" ]; then
    NODE_MAJOR="$("$NODE_BIN" -e 'process.stdout.write(String(process.versions.node.split(".")[0]))' 2>/dev/null)"
    if [ -n "$NODE_MAJOR" ] && [ "$NODE_MAJOR" -ge 18 ] 2>/dev/null; then
        ok "[OHOS] engines.node >=18 satisfied by OHOS node (v$NODE_MAJOR)"
    else
        bad "[OHOS] engines.node >=18 (got v$NODE_MAJOR)"
    fi
else
    skipped "[OHOS] engines.node >=18 (node unusable)"
fi

# 引擎在 OHOS node 下的端到端功能（真实调用被测包 API）
if [ -n "$NODE_BIN" ]; then
    CONSUMER="$(dirname "$0")/consumer/engine_flow.mjs"
    if "$NODE_BIN" "$CONSUMER" "$CORE/index.js"; then
        ok "[OHOS] ubo-core engine e2e under OHOS node (block/exception/serialize)"
    else
        bad "[OHOS] ubo-core engine e2e under OHOS node"
    fi
else
    skipped "[OHOS] ubo-core engine e2e (node unusable)"
fi

# wasm 制品随包分发（OHOS aarch64 上 WebAssembly 引擎依赖）
WASM_JSON=$(find "$CORE" -name '*.wasm.json' 2>/dev/null | wc -l | tr -d ' ')
if [ "$WASM_JSON" -ge 3 ]; then
    ok "[OHOS] wasm artifacts bundled (wasm.json count=$WASM_JSON)"
else
    bad "[OHOS] wasm artifacts bundled (count=$WASM_JSON, expect >=3)"
fi

echo "=== Results: $pass passed, $fail failed, $skip skipped ==="
[ "$fail" -eq 0 ]

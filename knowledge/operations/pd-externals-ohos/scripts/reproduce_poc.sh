#!/bin/sh
# reproduce_poc.sh — pd-externals-ohos 双态复现（样例库：pd-vbap）
#
#   态 1（naive）  ：裸 `make`（无 CC / 无 PDINCLUDEDIR，等价「未适配」）
#                    期望：在编译任何源码之前硬失败，且检测器能自动识别（退出码 2，变体 A）
#   态 2（guarded）：`make -j1 CC=clang PDINCLUDEDIR=<puredata>/include/pd`
#                    期望：产出 <name>.pd_linux，检测器判 CLEAN
#
# 约束：可写 TMPDIR；日志全部重定向到文件；**脚本内无任何管道**
#       （规避 SIGPIPE 与 `| head` 截断产生空日志）；无写死绝对路径。
#
# 用法：
#   sh reproduce_poc.sh [--only naive|guarded] [--src <pd-vbap 源码目录>] [--work <工作目录>]

# -e / -u 按 code-style §7 开启：本脚本要**捕获期望中的非零退出码**（态 1 的裸
# make 必须失败才算复现成功），故所有允许失败的命令一律写成
# `cmd && ok=0 || ok=$?` 或置于 if 条件中，显式消化退出码，不会被 -e 误杀。
# pipefail 先用子 shell 试探再应用：脚本头顶是 #!/bin/sh，OHOS 的 sh 可能是不支持
# -o pipefail 的 dash 系，直接写会让脚本在启动时即失败。脚本内本身不用管道
# （见上方约束），故该开关只是额外保险。
set -eu
if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SKILL_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(cd "$SKILL_DIR/../.." && pwd)
GUARD="$SKILL_DIR/scripts/pd_external_guard.py"

ONLY=""
SRC_OVERRIDE=""
WORK=""

while [ $# -gt 0 ]; do
    case "$1" in
        --only) ONLY="$2"; shift 2 ;;
        --src)  SRC_OVERRIDE="$2"; shift 2 ;;
        --work) WORK="$2"; shift 2 ;;
        -h|--help) sed -n '1,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

# ---- 可写 TMPDIR（OHOS 目标机 /tmp 只读）----
if [ -z "${TMPDIR:-}" ]; then
    TMPDIR="$HOME/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
if [ ! -w "$TMPDIR" ]; then
    echo "TMPDIR is not writable: $TMPDIR" >&2
    exit 1
fi
export TMPDIR

if [ -z "$WORK" ]; then
    WORK="$TMPDIR/pd-externals-ohos-poc"
fi
CC_BIN="${CC_SUT:-clang}"
PD_VER="0.54.1"
SRC_URL="https://codeload.github.com/pure-data/vbap/tar.gz/refs/tags/v1.2.1"
SRC_SHA="7a754a9c5051f2f9e8e243e1cd5c348255bae348430fec9d4d60e4649facd6d1"
TARBALL="$WORK/vbap-1.2.1.tar.gz"

# 上次运行下载并校验过的 tarball 可直接复用：保留 TARBALL 本身，只清理
# 其余内容。（原实现先 rm -rf "$WORK" 再判 "$TARBALL" 缓存——TARBALL 位于
# WORK 内，缓存分支永不可达，脚本每次都强制重新下载。）
if [ -f "$TARBALL" ]; then
    find "$WORK" -mindepth 1 -maxdepth 1 \
        ! -name "$(basename "$TARBALL")" -exec rm -rf {} +
else
    rm -rf "$WORK"
    mkdir -p "$WORK"
fi

echo "== repo root : $REPO_ROOT"
echo "== work dir  : $WORK"
echo "== cc        : $CC_BIN"

# ---- 取样例源码（官方源；本地已校验 tarball 可直接复用）----
if [ -n "$SRC_OVERRIDE" ]; then
    echo "== source    : $SRC_OVERRIDE (override)"
else
    if [ -f "$TARBALL" ]; then
        echo "== source    : $TARBALL (cached)"
    else
        echo "== fetching  : $SRC_URL"
        python3 - "$SRC_URL" "$TARBALL" "$SRC_SHA" <<'PY'
import hashlib, sys, time, urllib.request
url, out, want = sys.argv[1], sys.argv[2], sys.argv[3]
last = None
for attempt in range(1, 4):
    try:
        with urllib.request.urlopen(url, timeout=90) as resp:
            data = resp.read()
        break
    except Exception as exc:                      # noqa: BLE001
        last = exc
        print("  [retry %d/3] %s" % (attempt, exc), flush=True)
        time.sleep(5 * attempt)
else:
    raise SystemExit("download failed: %s" % last)
got = hashlib.sha256(data).hexdigest()
if got != want:
    raise SystemExit("sha256 mismatch: got %s want %s" % (got, want))
with open(out, "wb") as fh:
    fh.write(data)
print("  [ok] %d bytes, sha256 %s" % (len(data), got))
PY
    fi
fi

prepare_src() {
    # $1 = 目标目录
    dst="$1"
    rm -rf "$dst"
    mkdir -p "$dst"
    if [ -n "$SRC_OVERRIDE" ]; then
        cp -R "$SRC_OVERRIDE"/. "$dst"/
    else
        tar -xzf "$TARBALL" -C "$dst" --strip-components=1
    fi
}

# ---- Pd 头集（puredata 包：含 s_stuff.h；libpd 包缺该头，不可用于编译）----
PD_INC=""
deploy_pd() {
    dep_dir="$WORK/pd-dep"
    echo "== deploying puredata/$PD_VER (headers)"
    # Conan 2 用 deployer（不是 generator）：full_deploy 把包目录树复制到 <of>/full_deploy/host/<name>
    conan install --requires="puredata/$PD_VER" --deployer=full_deploy -of "$dep_dir" \
        -pr:h "$REPO_ROOT/ci/conan/profiles/ohos-aarch64" -pr:b default \
        > "$WORK/conan-install.log" 2>&1 && rc=0 || rc=$?
    if [ $rc -ne 0 ]; then
        echo "  [fail] conan install rc=$rc (see $WORK/conan-install.log)" >&2
        return 1
    fi
    for cand in $(find "$dep_dir" -type d -path '*/include/pd' 2>/dev/null); do
        PD_INC="$cand"
    done
    if [ -z "$PD_INC" ]; then
        echo "  [fail] include/pd not found under $dep_dir" >&2
        return 1
    fi
    echo "  [ok] PDINCLUDEDIR=$PD_INC"
    return 0
}

guard() {
    # $1 = 日志文件；$2 = 期望退出码语义（hit|clean）
    python3 "$GUARD" log "$1" > "$WORK/guard-$(basename "$1").txt" 2>&1 && rc=0 || rc=$?
    echo "  detector $1 -> rc=$rc"
    sed -n '1,12p' "$WORK/guard-$(basename "$1").txt"
    if [ "$2" = "hit" ] && [ $rc -ne 2 ]; then
        echo "  [fail] detector did not flag the naive build (expected rc=2)" >&2
        return 1
    fi
    if [ "$2" = "clean" ] && [ $rc -ne 0 ]; then
        echo "  [fail] detector flagged the guarded build (expected rc=0)" >&2
        return 1
    fi
    return 0
}

FAILED=0

# ================= 态 1：未适配（裸 make）=================
if [ "$ONLY" = "" ] || [ "$ONLY" = "naive" ]; then
    echo
    echo "=== 态 1：naive（裸 make，无 CC/PDINCLUDEDIR）==="
    prepare_src "$WORK/naive"
    (
        cd "$WORK/naive" || exit 3
        env -u CC -u CXX -u CFLAGS -u CPPFLAGS -u LDFLAGS make -j1
    ) > "$WORK/naive-make.log" 2>&1 && naive_rc=0 || naive_rc=$?
    echo "  make rc=$naive_rc (expected != 0)"
    tail -5 "$WORK/naive-make.log" 2>/dev/null || true
    if [ $naive_rc -eq 0 ]; then
        echo "  [fail] naive build unexpectedly succeeded" >&2
        FAILED=1
    fi
    guard "$WORK/naive-make.log" hit || FAILED=1
fi

# ================= 态 2：适配后（显式 CC + PDINCLUDEDIR）=================
if [ "$ONLY" = "" ] || [ "$ONLY" = "guarded" ]; then
    echo
    echo "=== 态 2：guarded（CC + PDINCLUDEDIR）==="
    prepare_src "$WORK/guarded"
    if deploy_pd; then
        (
            cd "$WORK/guarded" || exit 3
            make -j1 CC="$CC_BIN" PDINCLUDEDIR="$PD_INC"
        ) > "$WORK/guarded-make.log" 2>&1 && guarded_rc=0 || guarded_rc=$?
        echo "  make rc=$guarded_rc (expected 0)"
        if [ $guarded_rc -ne 0 ]; then
            tail -20 "$WORK/guarded-make.log" 2>/dev/null || true
            echo "  [fail] guarded build failed" >&2
            FAILED=1
        else
            ls -l "$WORK/guarded"/*.pd_linux > "$WORK/guarded-artifacts.txt" 2>&1 || true
            cat "$WORK/guarded-artifacts.txt"
        fi
        guard "$WORK/guarded-make.log" clean || FAILED=1
    else
        echo "  [skip] puredata/$PD_VER unavailable (registry/network); state 2 not evaluated" >&2
        FAILED=1
    fi
fi

echo
if [ $FAILED -eq 0 ]; then
    echo "PASS: 双态行为符合预期（未适配失败且可自动识别 / 适配后构建通过）"
    exit 0
fi
echo "FAIL: 双态复现未达预期，详见 $WORK/*.log" >&2
exit 1

#!/bin/bash
# test_package/test.sh — wpmeta 0.2.0 consumer smoke test + HarmonyOS-specific cases.
#
# 5 消费者用例（上游 CLI 语义）+ 3 项鸿蒙特有用例（H1 ELF 目标架构、H2 OHOS
# musl 加载器、H3 端到端预览图 JPEG 编码）。所有用例真实执行已打包的 wpmeta
# 二进制，计数取自本脚本的实际执行结果，并输出 HMBS_TEST_PACKAGE_RESULT 标记。
#
# 注意（OHOS 平台）：/tmp 只读，临时文件一律落在 ${TMPDIR:-$HOME/tmp}。
# 注：不用 set -e / set -o pipefail——C3/C5 需捕获非零 rc 后断言（set -e 会在
# 捕获前中止）；H3 的 head|od|grep -q 管道在 grep -q 提前退出时会被 pipefail
# 误判（weggli/0.2.4 同款豁免）。
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
WPMETA="$(command -v wpmeta || true)"
if [ -z "$WPMETA" ]; then
    echo "FAIL - packaged wpmeta binary not found on PATH" >&2
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-$HOME/tmp}/wpmeta-tp.XXXXXX")" || exit 1
trap 'rm -rf "$WORK"' EXIT

# ── 壁纸夹具（测试期生成，不随 PR 提交二进制）──────────────────────────
# 本仓库 PR diff 对新增二进制文件不附二进制数据段（CI checkout-pr
# 用 git apply 应用 diff 时会报 "missing binary patch data"，先例 dbskkd-cdb
# 的 .cdb 夹具同源约束），因此 64x64 PNG 夹具在此按需生成；生成过程完全确定
# （固定 zlib 等级与滤波字节），每次产物逐字节一致，C4 的 cmp 映射断言仍有效。
FIXDIR="${WORK}/fixtures"
mkdir -p "${FIXDIR}"
if ! command -v python3 > /dev/null 2>&1; then
    echo "FAIL - python3 is required to generate the wallpaper fixtures" >&2
    exit 1
fi
for variant in normal dark; do
    if ! python3 "${HERE}/fixtures/make_wallpaper.py" "$variant" "${FIXDIR}/${variant}.png"; then
        echo "FAIL - could not generate ${variant} wallpaper fixture" >&2
        exit 1
    fi
done
FIX_NORMAL="${FIXDIR}/normal.png"
FIX_DARK="${FIXDIR}/dark.png"

TOTAL=0
PASS=0
FAIL=0

record() { # name expected_rc actual_rc log_file [required_text]
    local name="$1" expect="$2" rc="$3" log="$4" want="${5:-}"
    TOTAL=$((TOTAL + 1))
    if [ "$rc" -ne "$expect" ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL [${name}] rc=${rc} (expected ${expect})"
        sed -n '1,5p' "$log"
        return
    fi
    if [ -n "$want" ] && ! grep -qF "$want" "$log"; then
        FAIL=$((FAIL + 1))
        echo "FAIL [${name}] missing expected text: ${want}"
        sed -n '1,5p' "$log"
        return
    fi
    PASS=$((PASS + 1))
    echo "ok   [${name}] rc=${rc}"
}

echo "wpmeta binary: ${WPMETA}"

# ── consumer cases (upstream CLI semantics) ─────────────────────────
"${WPMETA}" --version > "${WORK}/version.out" 2> "${WORK}/version.err"
record "C1 version" 0 $? "${WORK}/version.out" "wpmeta 0.2.0"

"${WPMETA}" --help > "${WORK}/help.out" 2> "${WORK}/help.err"
record "C2 usage/help" 0 $? "${WORK}/help.out" "Usage:"

"${WPMETA}" > "${WORK}/noargs.out" 2> "${WORK}/noargs.err"
record "C3 missing required arguments" 2 $? "${WORK}/noargs.err" \
    "required arguments were not provided"

# C4: 端到端 —— metadata.toml（normal + dark 变体 + 全量颜色 override，输出
# 确定性）→ KDE metadata.json + GNOME gnome-background-properties XML + 拷贝图像。
SRC1="${WORK}/src1"
DST1="${WORK}/dst1"
mkdir -p "${SRC1}" "${DST1}"
cp "${FIX_NORMAL}" "${SRC1}/ohos_wallpaper.png"
cp "${FIX_DARK}" "${SRC1}/ohos_wallpaper_dark.png"
cat > "${SRC1}/metadata.toml" <<'EOF'
[[authors]]
email = "ohos.pc@example.com"
name.default = "OHOS PC Upstream"

[[wallpapers]]
title.default = "HarmonyOS Wallpaper"
license = "CC-BY-SA-4.0"
id = "HarmonyOS"
path = ["ohos_wallpaper.png", "ohos_wallpaper_dark.png"]
primary_color = "#023C88"
accent_color = "#5789CA"
dark_accent_color = "#5789CA"
EOF
"${WPMETA}" --src "${SRC1}" --dst "${DST1}" > "${WORK}/e2e.out" 2> "${WORK}/e2e.err"
record "C4 end-to-end run (normal+dark)" 0 $? "${WORK}/e2e.err" ""

C4_OK=1
check_file() { # path description
    if [ ! -s "$1" ]; then
        echo "FAIL [C4] missing output: $2 ($1)"
        C4_OK=0
    fi
}
check_text() { # file text description
    if ! grep -qF "$2" "$1" 2>/dev/null; then
        echo "FAIL [C4] $3: '$2' not found in $1"
        C4_OK=0
    fi
}
check_same() { # src_file dst_file description —— 字节级校验拷贝源映射，
    # 保证 normal/dark 两个 fixture 不会被调包（两 fixture 字节互异）
    if ! cmp -s "$1" "$2" 2>/dev/null; then
        echo "FAIL [C4] $3: bytes differ ($2 != $1)"
        C4_OK=0
    fi
}
WP_BASE="${DST1}/usr/share/wallpapers/HarmonyOS"
# 两个生成夹具必须字节互异，否则"哪份拷到哪个目录"的映射断言失去判别力
if cmp -s "${FIX_NORMAL}" "${FIX_DARK}"; then
    echo "FAIL [C4] generated normal/dark fixtures are not byte-distinct"
    C4_OK=0
fi
check_file "${WP_BASE}/contents/images/64x64.png" "copied normal wallpaper"
check_file "${WP_BASE}/contents/images_dark/64x64.png" "copied dark wallpaper"
check_same "${FIX_NORMAL}" \
    "${WP_BASE}/contents/images/64x64.png" "normal variant copy mapping"
check_same "${FIX_DARK}" \
    "${WP_BASE}/contents/images_dark/64x64.png" "dark variant copy mapping"
check_file "${WP_BASE}/metadata.json" "KDE metadata.json"
check_file "${DST1}/usr/share/gnome-background-properties/HarmonyOS.xml" "GNOME background properties XML"
if [ -f "${WP_BASE}/metadata.json" ]; then
    check_text "${WP_BASE}/metadata.json" '"Id": "HarmonyOS"' "KDE Id"
    check_text "${WP_BASE}/metadata.json" '"License": "CC-BY-SA-4.0"' "KDE License"
    check_text "${WP_BASE}/metadata.json" '"Email": "ohos.pc@example.com"' "KDE author email"
    check_text "${WP_BASE}/metadata.json" '"Name": "OHOS PC Upstream"' "KDE author name"
    check_text "${WP_BASE}/metadata.json" '"Light": "#5789CA"' "KDE light accent (override)"
    check_text "${WP_BASE}/metadata.json" '"Dark": "#5789CA"' "KDE dark accent (override)"
fi
GNOME_XML="${DST1}/usr/share/gnome-background-properties/HarmonyOS.xml"
if [ -f "${GNOME_XML}" ]; then
    check_text "${GNOME_XML}" '<name>HarmonyOS Wallpaper</name>' "GNOME name"
    check_text "${GNOME_XML}" 'usr/share/wallpapers/HarmonyOS/contents/images/64x64.png' "GNOME filename"
    check_text "${GNOME_XML}" 'usr/share/wallpapers/HarmonyOS/contents/images_dark/64x64.png' "GNOME filename-dark"
    check_text "${GNOME_XML}" '<pcolor>#023C88</pcolor>' "GNOME pcolor (override)"
    check_text "${GNOME_XML}" '<scolor>#5789CA</scolor>' "GNOME scolor (override)"
fi
if [ "${C4_OK}" -eq 1 ]; then
    TOTAL=$((TOTAL + 1))
    PASS=$((PASS + 1))
    echo "ok   [C4 output assertions]"
else
    TOTAL=$((TOTAL + 1))
    FAIL=$((FAIL + 1))
fi

# C5: 不存在的源目录 → eyre 报错退出（rc=1；walk.rs:81 对起点做目录校验，
#     报错文本为 "Starting path … is not a directory"）
"${WPMETA}" --src "${WORK}/does-not-exist" --dst "${WORK}/dst5" \
    > "${WORK}/badsrc.out" 2> "${WORK}/badsrc.err"
record "C5 nonexistent source directory" 1 $? "${WORK}/badsrc.err" \
    "is not a directory"

# ── HarmonyOS-specific cases ─────────────────────────────────────────
# H1: 打包产物必须是 OHOS armv8（aarch64）目标的可执行 ELF
readelf -h "${WPMETA}" > "${WORK}/elf.out" 2> "${WORK}/elf.err"
record "H1 OHOS target artifact (AArch64 ELF)" 0 $? "${WORK}/elf.out" \
    "AArch64"

# H2: 鸿蒙 musl 加载器 —— 打包二进制的 ELF interpreter 必须是
#     /lib/ld-musl-aarch64.so.1（OHOS aarch64 目标产物标志）
readelf -l "${WPMETA}" > "${WORK}/interp.out" 2> "${WORK}/interp.err"
record "H2 OHOS musl program interpreter" 0 $? "${WORK}/interp.out" \
    "ld-musl-aarch64.so.1"

# H3: 端到端预览图 —— 仅 normal 变体时 KDE 生成 contents/screenshot.jpg
#     （500x500 JPEG，Lanczos3 缩放 + zune-jpeg 编码在 OHOS 上真实执行）
SRC3="${WORK}/src3"
DST3="${WORK}/dst3"
mkdir -p "${SRC3}" "${DST3}"
cp "${FIX_NORMAL}" "${SRC3}/ohos_wallpaper.png"
cat > "${SRC3}/metadata.toml" <<'EOF'
[[authors]]
email = "ohos.pc@example.com"
name.default = "OHOS PC Upstream"

[[wallpapers]]
title.default = "HarmonyOS Preview"
license = "CC0-1.0"
id = "Preview"
path = "ohos_wallpaper.png"
EOF
"${WPMETA}" --src "${SRC3}" --dst "${DST3}" > "${WORK}/preview.out" 2> "${WORK}/preview.err"
record "H3 preview generation run" 0 $? "${WORK}/preview.err" ""
SHOT="${DST3}/usr/share/wallpapers/Preview/contents/screenshot.jpg"
TOTAL=$((TOTAL + 1))
if [ -s "${SHOT}" ] && head -c 3 "${SHOT}" | od -An -tx1 | grep -q "ff d8 ff"; then
    PASS=$((PASS + 1))
    echo "ok   [H3 OHOS preview JPEG artifact]"
else
    FAIL=$((FAIL + 1))
    echo "FAIL [H3 OHOS preview JPEG artifact] ${SHOT}"
fi

echo "consumer + HarmonyOS cases: passed=${PASS} failed=${FAIL} total=${TOTAL}"
printf 'HMBS_TEST_PACKAGE_RESULT=%s\n' \
    "{\"status\":\"$([ "${FAIL}" -eq 0 ] && echo passed || echo failed)\",\"framework\":\"bash\",\"command\":\"test.sh\",\"discovered\":${TOTAL},\"executed\":${TOTAL},\"passed\":${PASS},\"failed\":${FAIL},\"skipped\":0}"

[ "${FAIL}" -eq 0 ] || exit 1

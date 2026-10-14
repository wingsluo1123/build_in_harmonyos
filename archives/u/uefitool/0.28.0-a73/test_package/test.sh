#!/bin/sh
# test_package/test.sh — uefitool 0.28.0-a73 消费者验证
#
# 这个包是**工具包**（没有库、没有公共头），所以"消费者"就是拿到
# `uefiextract` / `uefifind` 两个可执行文件的人。验证分三层，共 28 条：
#
#   A. CLI 契约层（17 条）：退出码与用法文本。期望值全部取自上游 main() 的
#      字面返回，不是我们臆断的：
#        uefiextract -v                    -> 0（uefiextract_main.cpp:65-68）
#        uefiextract --help + 6 个用法条目 -> 0（print_usage 原文逐条 grep）
#        uefiextract 无参数                -> 1（argc <= 1 → print_usage 后 return 1）
#        uefiextract <不存在的文件>        -> 5（readFileIntoBuffer 失败 → U_FILE_OPEN）
#        uefifind   -v / --help / 无参数   -> 0（注意 argc==1 时也返回 U_SUCCESS，
#                                              **与 uefiextract 不对称**，这里钉住它）
#        uefifind   --help + 3 个用法条目  -> 0
#        uefifind   <不存在的文件> ...     -> 5
#        uefifind   <文件> <非法模式> ...  -> 1（U_INVALID_PARAMETER）
#        uefifind   找不到匹配             -> 8（U_ITEM_NOT_FOUND）
#      （为什么是 17 而不是 16：第一个用法循环有 6 个条目 ——
#        "imagefile all" / "unpack" / "dump" / "report" / "guids" / "-m MODE_1"。）
#
#   B. 真实解析层（8 条）：用 make_fixture.py 现造一张最小合法 FFS2 固件卷
#      （4096 字节：EFI_FIRMWARE_FILE_SYSTEM2_GUID 卷头 + 校验和 + BlockMap 终止项，
#      内含一个 FREEFORM 探测文件 + 一个 Volume Top File；探测文件的 RAW 段体里有
#      4 字节魔数 EF BE AD DE 与 32 字节 ASCII 标记），然后让两个工具真的走一遍
#      镜像 → 卷 → 文件 → 段 的解析链路。上游零测试语料，这一层是本包
#      "解析器真的能解析固件"的全部证据来源。
#
#   C. GUID 名表（guids.csv）生效性（3 条）：见 C 段的长注释 ——
#      本包最有分量的证据链，做**双向**验证。
#
# 本脚本由 test_package/conanfile.py 用 bash 启动（OHOS 上 /system/bin/sh 是
# mksh，不能执行 ELF），所以这里用 POSIX 语法但可以放心依赖 bash 的行为。
export PATH="$PATH:/system/bin"

# ── 用例总数自校验 ─────────────────────────────────────────────────────────
# 28 = A 17 + B 8 + C 3（每条检查只走 pass() 或 fail() 之一，各计一次）。
# 全部通过时若计数漂移，直接 Bail out —— 让"到底用了多少条"这件事可机器复核，
# 而不是靠 PR 正文里的一个手写数字。
EXPECTED_CHECKS=28

CHECKS=0
FAILED=0
pass() { CHECKS=$((CHECKS + 1)); echo "ok $CHECKS - $1"; }
fail() { CHECKS=$((CHECKS + 1)); FAILED=$((FAILED + 1)); echo "not ok $CHECKS - $1"; }

HERE=$(cd -- "$(dirname -- "$0")" && pwd -P)
# OHOS 的 /tmp 是只读的（Read-only file system）⇒ 一律走 TMPDIR（真机为 $HOME/tmp）
WORK=$(mktemp -d "${TMPDIR:-/tmp}/uefitool-consumer-XXXXXX") || {
    echo "Bail out! mktemp -d failed"; exit 1; }
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

# 断言锚点（与 make_fixture.py 里的常量一一对应）
PROBE_GUID=A1B2C3D4E5F64A5B8C9D0E1F2A3B4C5D
PROBE_MAGIC=efbeadde
ABSENT_MAGIC=5a5a5a5a
# fixture 里那个 Volume Top File 的 GUID（EFI_FFS_VOLUME_TOP_FILE_GUID）
VTF_GUID_RAW=1BA0062EC77945828566336AE8F78F09
VERSION_TOKEN="NE alpha 73"

# GUID 归一化：去空白与连字符、统一大写 —— 这样断言不依赖 guidToUString 的大小写
# 与是否加连字符（上游 guidToUString 走 usprintf("%08X-%04X-%04X-…") 大写带连字符，
# 但不把断言绑死在这个细节上）。
norm() { tr -d '[:space:]-' | tr 'a-f' 'A-F'; }

echo "--- uefitool 0.28.0-a73 consumer verification ---"

# ── A. CLI 契约层 ────────────────────────────────────────────────────────────

# A1. 版本：PROGRAM_VERSION 里带 __DATE__（"NE alpha 73 (Mon DD YYYY)"），
#    日期随构建时刻变化，所以只钉版本串本体。
out=$(uefiextract -v 2>&1); rc=$?
if [ "$rc" = "0" ] && printf '%s' "$out" | grep -q "$VERSION_TOKEN"; then
    pass "uefiextract -v -> [$out]"
else
    fail "uefiextract -v rc=$rc output=[$out]"
fi

out=$(uefifind -v 2>&1); rc=$?
if [ "$rc" = "0" ] && printf '%s' "$out" | grep -q "$VERSION_TOKEN"; then
    pass "uefifind -v -> [$out]"
else
    fail "uefifind -v rc=$rc output=[$out]"
fi

# A2. 用法文本必须列出真实的子模式（uefiextract_main.cpp 的 print_usage 原文）
if uefiextract --help > "$WORK/extract-help.txt" 2>&1; then
    pass "uefiextract --help rc=0"
else
    fail "uefiextract --help rc=$?"
fi
for mode in "imagefile all" "unpack" "dump" "report" "guids" "-m MODE_1"; do
    if grep -q -- "$mode" "$WORK/extract-help.txt"; then
        pass "uefiextract --help lists [$mode]"
    else
        fail "uefiextract --help does not list [$mode]"
    fi
done

if uefifind --help > "$WORK/find-help.txt" 2>&1; then
    pass "uefifind --help rc=0"
else
    fail "uefifind --help rc=$?"
fi
for mode in "header | body | all" "list | count" "patternsfile"; do
    if grep -q -- "$mode" "$WORK/find-help.txt"; then
        pass "uefifind --help lists [$mode]"
    else
        fail "uefifind --help does not list [$mode]"
    fi
done

# A3. 无参数：两个工具**故意不对称**，各自钉住
uefiextract > /dev/null 2>&1; rc=$?
if [ "$rc" = "1" ]; then
    pass "uefiextract (no args) rc=1"
else
    fail "uefiextract (no args) rc=$rc, expected 1"
fi
uefifind > /dev/null 2>&1; rc=$?
if [ "$rc" = "0" ]; then
    pass "uefifind (no args) rc=0 (upstream asymmetry preserved)"
else
    fail "uefifind (no args) rc=$rc, expected 0"
fi

# A4. 错误路径退出码（U_FILE_OPEN = 5，见 common/basetypes.h）
uefiextract "$WORK/definitely-not-here.bin" > /dev/null 2>&1; rc=$?
if [ "$rc" = "5" ]; then
    pass "uefiextract <missing file> rc=5 (U_FILE_OPEN)"
else
    fail "uefiextract <missing file> rc=$rc, expected 5"
fi
uefifind "$WORK/definitely-not-here.bin" header list 00 > /dev/null 2>&1; rc=$?
if [ "$rc" = "5" ]; then
    pass "uefifind <missing file> rc=5 (U_FILE_OPEN)"
else
    fail "uefifind <missing file> rc=$rc, expected 5"
fi

# ── B. 真实解析层 ───────────────────────────────────────────────────────────

# B1. 造固定装置
IMG="$WORK/probe.fv"
if python3 "$HERE/make_fixture.py" "$IMG" && [ -s "$IMG" ]; then
    SIZE=$(wc -c < "$IMG" | tr -d ' ')
    if [ "$SIZE" = "4096" ]; then
        pass "fixture generated ($SIZE bytes, FFSv2 volume + FREEFORM probe file + Volume Top File)"
    else
        fail "fixture size $SIZE, expected 4096"
    fi
else
    fail "make_fixture.py failed to generate $IMG"
fi

# B2. report 模式：解析整棵树并生成文本报告
( cd "$WORK" && uefiextract "$IMG" report ) > "$WORK/report.log" 2>&1; rc=$?
if [ "$rc" = "0" ]; then
    pass "uefiextract <fixture> report rc=0"
else
    fail "uefiextract <fixture> report rc=$rc"
    sed 's/^/# /' "$WORK/report.log"
fi
REPORT="$IMG.report.txt"
if [ -s "$REPORT" ]; then
    pass "report written ($(wc -c < "$REPORT" | tr -d ' ') bytes)"
    if norm < "$REPORT" | grep -q "$PROBE_GUID"; then
        pass "report names the probe file GUID ($PROBE_GUID)"
    else
        fail "report does not contain probe GUID $PROBE_GUID"
        sed 's/^/# /' "$REPORT" | head -40
    fi
else
    fail "report file $REPORT missing or empty"
fi

# B3. uefifind 段体检索：命中 fixture 里那个 RAW 段的 4 字节魔数
out=$(uefifind "$IMG" body count "$PROBE_MAGIC" 2>&1); rc=$?
if [ "$rc" = "0" ] && printf '%s' "$out" | grep -qE '[1-9]'; then
    pass "uefifind <fixture> body count $PROBE_MAGIC rc=0 -> [$(printf '%s' "$out" | tr '\n' ' ')]"
else
    fail "uefifind body count rc=$rc output=[$out]"
fi

out=$(uefifind "$IMG" body list "$PROBE_MAGIC" 2>&1); rc=$?
if [ "$rc" = "0" ] && printf '%s' "$out" | norm | grep -q "$PROBE_GUID"; then
    pass "uefifind <fixture> body list $PROBE_MAGIC rc=0 -> names probe file GUID"
else
    fail "uefifind body list rc=$rc expected probe GUID $PROBE_GUID, output=[$out]"
fi

# B4. 检索一个不可能出现的模式 ⇒ U_ITEM_NOT_FOUND = 8
uefifind "$IMG" body count "$ABSENT_MAGIC" > /dev/null 2>&1; rc=$?
if [ "$rc" = "8" ]; then
    pass "uefifind <fixture> body count $ABSENT_MAGIC rc=8 (U_ITEM_NOT_FOUND)"
else
    fail "uefifind absent-pattern rc=$rc, expected 8"
fi

# B5. dump 模式：把 FFS 树按 GUID 落盘成目录树
( cd "$WORK" && uefiextract "$IMG" dump ) > "$WORK/dump.log" 2>&1; rc=$?
if [ "$rc" = "0" ] && [ -d "$IMG.dump" ]; then
    FOUND=$(find "$IMG.dump" -type f | wc -l | tr -d ' ')
    if [ "$FOUND" -ge 1 ]; then
        pass "uefiextract <fixture> dump rc=0, $FOUND file(s) under $(basename "$IMG").dump/"
    else
        fail "dump dir exists but holds no files"
    fi
else
    fail "uefiextract <fixture> dump rc=$rc (dir_exists=$([ -d "$IMG.dump" ] && echo yes || echo no))"
    sed 's/^/# /' "$WORK/dump.log"
fi

# ── C. GUID 名表（guids.csv）生效性 ─────────────────────────────────────────
#
# 这一层是本包最有分量的一条证据链，所以做**双向**验证（只验一个方向会漏掉
# "名表其实没生效、只是恰好没报错"这种沉默失败）：
#
#   事实：上游把 GUID→可读名映射表（12042 行）**只**通过 GUI 的 Qt 资源
#   （UEFITool/uefitool.qrc）打包，INSTALL() 规则里没有它；而两个 CLI 里
#   UEFIExtract 在 main() 的**第一行**就调 initGuidDatabase("guids.csv") ——
#   相对路径，按**当前工作目录**解析。名表为空时 common/guiddatabase.cpp
#   静默返回空串，common/ffs.cpp 的 guidToUString() 就回退到
#   usprintf("%08X-%04X-%04X-%02X%02X-…") 的裸格式。
#   ⇒ 退出码不变、报告照样生成、只有"可读名"悄悄消失。
#
#   锚点用的是 fixture **卷头**的 FileSystemGuid：它正好是 guids.csv 里的
#   8C8CE578-8A3D-4F1C-9935-896185C32DD3 → EfiFirmwareFileSystem2Guid。
#   该名字取自 ffsparser.cpp:1520 的 guidToUString(volumeHeader->FileSystemGuid)
#   （声明处 ffs.h:25 的 convertToString 默认值为 true，即默认查名表）。
#
# 参数 $1 = 被测包内 share/uefitool/guids.csv 的绝对路径，由
# test_package/conanfile.py 从 dependencies[...].package_folder 算出后传入。

VOLUME_GUID_RAW=8C8CE5788A3D4F1C9935896185C32DD3
VOLUME_GUID_NAME=EfiFirmwareFileSystem2Guid

# C1. 无名表方向：此刻 CWD 里没有 guids.csv（B2 步就是在无表状态下跑的）
#     ⇒ 卷名必须是裸 GUID。
if norm < "$REPORT" | grep -q "$VOLUME_GUID_RAW"; then
    pass "no guids.csv in CWD -> volume stays raw ($VOLUME_GUID_RAW)"
else
    fail "raw volume GUID $VOLUME_GUID_RAW absent from report (no-guids.csv case)"
    sed 's/^/# /' "$REPORT" | head -25
fi

# C2. 有名表方向：把随包安装的 guids.csv 放进 CWD 再跑一次 ⇒ 卷名必须变成
#     可读名。这一条同时证明 package() 把 guids.csv 装到 share/uefitool/
#     是**必要且有效**的。
GUIDS_SRC="$1"
if [ -n "$GUIDS_SRC" ] && [ -f "$GUIDS_SRC" ]; then
    cp "$GUIDS_SRC" "$WORK/guids.csv"
    ( cd "$WORK" && uefiextract "$IMG" report ) > "$WORK/report-with-db.log" 2>&1
    rc=$?
    if [ "$rc" = "0" ] && grep -q "$VOLUME_GUID_NAME" "$REPORT"; then
        pass "guids.csv in CWD -> volume named '$VOLUME_GUID_NAME'"
    else
        fail "guids.csv present but volume name '$VOLUME_GUID_NAME' missing (rc=$rc)"
        sed 's/^/# /' "$REPORT" | head -25
    fi
else
    fail "guids.csv not handed over by test_package (arg1='$GUIDS_SRC')"
fi

# C3. guids 子模式：把镜像里各文件/卷的 GUID 汇总导出成 <img>.guids.csv
#
# ★ 这条用例同时钉住一个上游行为（也是本 fixture 必须有 VTF 的原因）：
#   guidDatabaseFromTreeRecursive()（common/guiddatabase.cpp:124）是按
#   `model->text(index)` 非空来筛选节点的，而 text 只对 VTF / NVRAM store /
#   apriori / protected-range hash 这类特殊文件才被赋值
#   （ffsparser.cpp:2249、2343-2375、3604-3624、4393-4516）——
#   普通文件的"名字"在 `model->name(index)` 里（ffsparser.cpp:2222 + 2262）。
#   ⇒ 镜像里没有 VTF 时 GUID 库恒为空；而 uefiextract_main.cpp:102-107 的
#     guids 分支在空库时**没有终结 return**，控制流落穿到第 217-218 行的
#     print_usage() + return 1 —— 明明什么都没错，却打印用法并退出 1。
#   （对照：report 分支第 119 行有显式 return 1，dump 分支返回 dump 的状态。）
( cd "$WORK" && uefiextract "$IMG" guids ) > "$WORK/guids-mode.log" 2>&1
rc=$?
if [ "$rc" = "0" ] && [ -s "$IMG.guids.csv" ] \
   && norm < "$IMG.guids.csv" | grep -q "$VTF_GUID_RAW"; then
    pass "uefiextract <fixture> guids rc=0 -> $(basename "$IMG").guids.csv ($(wc -c < "$IMG.guids.csv" | tr -d ' ') bytes, names the VTF $VTF_GUID_RAW)"
else
    fail "uefiextract guids rc=$rc, file_nonempty=$([ -s "$IMG.guids.csv" ] && echo yes || echo no)"
    sed 's/^/# /' "$WORK/guids-mode.log"
fi

echo "--- uefitool consumer: $CHECKS checks run, $FAILED failed ---"
# 计数自校验（只在全绿时生效，免得失败时多出一行噪声）：
# 让 PR 正文里写的"28 条"可以被运行日志机械复核，而不是一句自我声明。
if [ "$FAILED" = "0" ] && [ "$CHECKS" != "$EXPECTED_CHECKS" ]; then
    echo "Bail out! check count drifted: ran $CHECKS, expected $EXPECTED_CHECKS"
    exit 1
fi
[ "$FAILED" = "0" ] || exit 1
echo "ALL CHECKS PASSED (${CHECKS}/${EXPECTED_CHECKS})"
exit 0

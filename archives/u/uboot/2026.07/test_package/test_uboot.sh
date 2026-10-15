#!/bin/sh
# uboot test_package E2E entry (run by conan create, env=conanrun):
#
#   1. smoke:      version + ut lib (in-process unit test smoke)
#   2. fixtures:   mkfixtures.sh builds the bootstd E2E images
#                  (upstream pytest test_ut.py fixture 口径) + self-verifies
#   3. subtests:   per-subtest `ut <suite> <name>` for every test registered
#                  in u-boot.sym's linker-list symbols — the upstream pytest
#                  methodology (test/py/conftest.py generate_ut_subtest),
#                  which also isolates each test in its own process
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
export U_BOOT_SANDBOX=${U_BOOT_SANDBOX:?set U_BOOT_SANDBOX via runenv_info}
export U_BOOT_MKIMAGE=${U_BOOT_MKIMAGE:?set U_BOOT_MKIMAGE via runenv_info}
export U_BOOT_DTB=${U_BOOT_UT_DTB:?set U_BOOT_UT_DTB via runenv_info}
export U_BOOT_TESTAPP=${U_BOOT_UT_TESTAPP:?set U_BOOT_UT_TESTAPP via runenv_info}
export U_BOOT_UT_PAIRS=${U_BOOT_UT_PAIRS:-}
export U_BOOT_SYM=${U_BOOT_SYM:-}
export HOST_FIXTURES=$HERE/fixtures
export UT_WORKDIR=$HERE/work
# OHOS /tmp 只读：HOME 与 TMPDIR 全部落在工作目录
mkdir -p "$UT_WORKDIR/home" "$UT_WORKDIR/tmp"
export HOME=$UT_WORKDIR/home
export TMPDIR=$UT_WORKDIR/tmp

echo "===== 0. package assets in place ====="
# L1e 反向验证（R34）：bin/ 5 工具 + u-boot-sandbox + test/ 三资产 +
# sandbox 运行期资源 other.dtb（OF_LIVE 组单元测试按 argv[0] 相对路径
# arch/sandbox/dts/other.dtb 解析，须与二进制同相对布局分发），
# 任一被删除/清零立即失败，不进入后续步骤
BIN=$(dirname "$U_BOOT_SANDBOX")
for f in "$U_BOOT_SANDBOX" "$BIN/mkimage" "$BIN/dumpimage" \
         "$BIN/fit_info" "$BIN/mkenvimage" "$BIN/fdtgrep" \
         "$U_BOOT_UT_DTB" "$U_BOOT_UT_TESTAPP" "$U_BOOT_UT_PAIRS" \
         "$BIN/arch/sandbox/dts/other.dtb"; do
    [ -n "$f" ] && [ -s "$f" ] || {
        echo "ERROR: missing package asset: $f" >&2
        exit 1
    }
done
echo "10 package assets present"

echo "===== 0b. host tools smoke ====="
# 5 个 host 工具以无参调用冒烟：应打印 usage banner 而非崩溃/静默
for t in mkimage dumpimage fit_info mkenvimage fdtgrep; do
    out=$("$BIN/$t" 2>&1 || true)
    case "$out" in
    *[Uu]sage*) echo "tool $t usage banner OK" ;;
    *Please\ specify*) echo "tool $t banner OK" ;;   # mkenvimage 无参为参数校验提示
    *) echo "ERROR: $t smoke failed (no banner)" >&2; exit 1 ;;
    esac
done

echo "===== 0c. firmware (OHOS native build artifact) ====="
# qemu_arm64 固件仅在有 aarch64 交叉/原生编译器时构建（CI Linux 上跳过并告警）
FW="$(dirname "$BIN")/firmware/u-boot-qemu_arm64.bin"
if [ -s "$FW" ]; then
    if grep -aq "U-Boot" "$FW"; then
        echo "firmware in place, banner string OK ($(wc -c <"$FW") bytes)"
    else
        echo "ERROR: banner string not found in $FW" >&2
        exit 1
    fi
else
    echo "WARN: $FW absent (build without aarch64 compiler) - skipped"
fi

echo "===== 0d. SDL test surface in place ====="
# 上游 VIDEO_SANDBOX_SDL 门控的测试面（test/dm/video.o + test/boot/
# {cedit,expo}.o，经制品仓 sdl2 依赖接入）：VIDEO_SANDBOX_SDL depends on
# SANDBOX_SDL，而后者的 Kconfig default 探测（HOST_HAS_SDL=$(success,
# sdl2-config --version)）失败会被 syncconfig 按 depends 静默收敛——整片
# SDL 门控测试被裁而构建仍"成功"。pairs.txt 由 u-boot.sym 链接器列表符号
# 生成（测试面在则定义符号必在），此处以视频套件基础用例为锚做在位校验，
# 防该无声退化（dm_test_video_base 上游无编译条件，随 video.o 同进同出）。
grep -q "^dm_2_dm_test_video_base$" "$U_BOOT_UT_PAIRS" || {
    echo "ERROR: SDL-gated video tests absent from pairs.txt (SDL surface dropped)" >&2
    exit 1
}
echo "SDL-gated test surface present (dm video suite)"

echo "===== 1. smoke ====="
# membuf_readline（lib 套件）以 CWD 相对路径读取 "README" 作为测试数据
# （上游 pytest 的 CWD=源码树根，README 天然在场）；此处提供随包分发的
# 同契约 README 副本（fixtures/README，上游源码树逐字节副本）并切换到
# 工作目录运行。stdin 重定向 /dev/null：lib 套件无交互需求，且隔离
# 调用方 stdin 的管道残留字节（sandbox serial 的 testc 会读宿主 fd0，
# 残留字节将令 ut 的 tstc 判定误判）。
cp "$HOST_FIXTURES/README" "$UT_WORKDIR/README"
cd "$UT_WORKDIR"
"$U_BOOT_SANDBOX" -c "version; ut lib; exit" < /dev/null

echo "===== 2. fixtures ====="
sh "$HOST_FIXTURES/mkfixtures.sh"

echo "===== 3. per-subtest ut ====="
sh "$HOST_FIXTURES/ut-run-subtests.sh"

echo "=== All tests passed ==="

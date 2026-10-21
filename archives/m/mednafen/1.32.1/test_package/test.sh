#!/data/service/hnp/bin/bash
# test_package/test.sh — mednafen 1.32.1 消费者测试（真跑安装出来的 bin/mednafen）
#
# 为什么不是 conan-init 的空壳 test.c：
#   1) mednafen 是 application 包（唯一产物 bin/mednafen），只 printf 的 test.c
#      证不到任何东西（PF3/R34 空壳）；
#   2) mednafen **没有** `--version` 选项（src/drivers/main.cpp 的参数表里只有
#      -help），test_package-executable 模板的 `--version` 分支必然落空。
#
# 为什么 `--help` 不能用退出码判成败（事实 + 证据）：
#   `--help` 命中 src/drivers/main.cpp:974-986 的 `if(ShowCLHelp){ printf(usage...);
#   return false; }`，而 main() 对该 false 的分支是 main.cpp:2408-2414
#   `CreateDataDirs(); SaveSettings(); MDFNI_Kill(); return -1;`
#   ⇒ 进程退出码是 **255**，不是 0（本机实测 rc=255）。
#   故本测试对 `--help` 只断言**输出内容**，退出码只在负控制上使用。
#
# 本测试跑的是**两条真上游测试面**：
#   [甲] MDFN_RunCheapTests()：src/mednafen.cpp:1457 在 MDFNI_Init() 里无条件调用，
#        清单在 src/tests.cpp 的 MDFN_RunCheapTests()，**60 项**注册断言
#        （位运算/有符号溢出/结构体对齐/浮点/哈希 md5+sha1+sha256+crc/zlib 往返/
#         SString/路径工具/CD 工具…）。任一失败即抛异常中断，走不到参数解析。
#        ⇒ "Usage:/Options: 帮助文本完整出现" ≡ "60 项内置断言全过 + SDL2 真初始化
#          + MDFNI_Init 全流程跑通"。
#   [乙] MDFNI_RunExpensiveTests()：由上游调试开关 `-exptests <dir>` 触发
#        （src/drivers/main.cpp:920 注册，:992-996 调起），清单在 src/testsexp.cpp 的
#        MDFNI_RunExpensiveTests()，**12 项**注册断言（TestSurface / TestMemoryStream /
#        TestStreamMisc / Testsnhex / TestSettings / NVFSTest / Stream64Test /
#        StreamBufTest / TestZLInflate / MDFN_RunExceptionTests(1,0) 与 (4,30000) 等）。
#        跑完会落到 main 的 "No game filename specified!" 收尾 ⇒ 该行出现即证明
#        12 项全部走完、中途没有抛异常。
#   两条合计 72 项 = 本包上游**可执行断言**的全量注册面（分母见 ../notes.md 五维账本）。
#
# 覆盖面：
#   A. 帮助路径真跑（[甲]）+ 启动横幅里**依赖真实链接版本**的三条断言
#      （zlib 1.3.1 / SDL2 2.30.10 / libFLAC 1.5.0）—— 校验头文件与库确实来自
#      本次 conan 依赖图（sdl2/2.30.10、flac/1.5.0、zlib/1.3.1.1），而不是宿主残留；
#   B. `-exptests` 扩展测试面真跑（[乙]）+ 它落盘的两个夹具文件（cfgtest.cfg /
#      streamtest.bin）——文件出现是"配置读写真跑过""FileStream 读写真跑过"的实物证据；
#   C. 参数解析器的判别能力：无参数（argc<=1）与非法选项都必须非零退出、
#      且非法选项不得打印帮助正文（防"任何调用都返回 0 / 都打印帮助"的假绿）。
set -u

# OHOS: /system/bin/sh (mksh) 不能执行 ELF，本脚本必须跑在 bash 下。
if [ -z "${BASH_VERSION:-}" ]; then
    if [ -x /data/service/hnp/bin/bash ]; then
        exec /data/service/hnp/bin/bash "$0" "$@"
    fi
    echo "FATAL: 本测试需要 bash，但 /data/service/hnp/bin/bash 不存在" >&2
    exit 1
fi

# HMDFS: /tmp 是只读 erofs；mktemp -d 在 HMDFS 上建出 drwx--S--- 目录（连 owner
# 都写不进去）⇒ 不用 mktemp，直接 mkdir -p 一个以 $$ 结尾的唯一目录（框架 L1e
# 破坏性负例会对同一个 test_package 起第二轮，共用固定目录会互相覆写）。
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}"
WORK="${_TMPBASE}/mednafen-test-package.$$"
if ! mkdir -p "$WORK" 2>/dev/null; then
    WORK="${HOME}/tmp/mednafen-test-package.$$"
    mkdir -p "$WORK" 2>/dev/null || { echo "FATAL: no writable work dir $WORK" >&2; exit 1; }
fi
# mednafen 的配置目录默认是 $HOME/.mednafen（src/drivers/main.cpp:1469-1500
# GetBaseDirectory()），这里显式钉到夹具目录：既保证可写，也避免污染宿主 HOME。
export MEDNAFEN_HOME="$WORK/home"
mkdir -p "$MEDNAFEN_HOME" "$WORK/expt"

TOTAL=0
FAILED=0
out=""
rc=0

run() {
    # run <label> <expect: ok|fail> <cmd...>
    label="$1"; shift
    expect="$1"; shift
    TOTAL=$((TOTAL + 1))
    out="$("$@" 2>&1)"
    rc=$?
    echo "----- [$TOTAL] $label  (cmd: $*, rc=$rc)"
    echo "$out" | head -25
    if [ "$expect" = "ok" ] && [ "$rc" -ne 0 ]; then
        echo "❌ $label: 期望退出 0，实得 $rc"; FAILED=$((FAILED + 1)); return
    fi
    if [ "$expect" = "fail" ] && [ "$rc" -eq 0 ]; then
        echo "❌ $label: 期望非零退出，实得 0（无条件 return 0 的假绿）"
        FAILED=$((FAILED + 1)); return
    fi
}

run_help() {
    # run_help <label>  —— 真跑 `mednafen --help`。退出码按上游实现固定为 255，
    # 所以这里只挡 rc=126/127（没执行起来）并要求输出非空；内容断言交给 grep_check。
    label="$1"
    TOTAL=$((TOTAL + 1))
    out="$(mednafen --help 2>&1)"
    rc=$?
    # 无显示环境（CI 容器/无 X/Wayland 会话）下 SDL_Init(SDL_INIT_VIDEO) 会失败，
    # 上游此时会打 "Could not initialize SDL" 并在 DoArgs 之前退出。这里**不改判据**，
    # 只把视频后端显式钉到 SDL2 自带的 dummy 驱动后重跑同一命令；
    # 两种情况都跑不出 Usage 才算失败。
    case "$out" in
        *"Usage:"*) : ;;
        *)  echo "  (第一次未出帮助文本，改以 SDL_VIDEODRIVER=dummy 重跑)"
            export SDL_VIDEODRIVER=dummy
            out="$(mednafen --help 2>&1)"
            rc=$? ;;
    esac
    echo "----- [$TOTAL] $label  (cmd: mednafen --help, rc=$rc)"
    echo "$out" | head -25
    if [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
        echo "❌ $label: 二进制没能执行起来（rc=$rc）"; FAILED=$((FAILED + 1)); return
    fi
    if [ -z "$out" ]; then
        echo "❌ $label: 无任何输出"; FAILED=$((FAILED + 1)); return
    fi
}

grep_check() {
    # grep_check <label> <fixed-string>  —— 对上一次 run/run_help 的输出做内容断言。
    # 一律 grep -qiF（固定串）：E1274——BRE 的 \| 在部分实现上不被支持。
    label="$1"; pat="$2"
    TOTAL=$((TOTAL + 1))
    if printf '%s\n' "$out" | grep -qiF -- "$pat"; then
        echo "----- [$TOTAL] $label: 命中 [$pat]"
    else
        echo "❌ $label: 输出里没有 [$pat]"
        FAILED=$((FAILED + 1))
    fi
}

grep_absent() {
    # grep_absent <label> <fixed-string>  —— 断言上一次输出里**不含**该固定串
    label="$1"; pat="$2"
    TOTAL=$((TOTAL + 1))
    if printf '%s\n' "$out" | grep -qiF -- "$pat"; then
        echo "❌ $label: 输出里不应出现 [$pat]"
        FAILED=$((FAILED + 1))
    else
        echo "----- [$TOTAL] $label: 确认不含 [$pat]"
    fi
}

file_check() {
    # file_check <label> <path>  —— 实物证据：该文件存在且非空
    label="$1"; path="$2"
    TOTAL=$((TOTAL + 1))
    if [ -s "$path" ]; then
        echo "----- [$TOTAL] $label: 已落盘 $(wc -c < "$path") 字节 ($path)"
    else
        echo "❌ $label: 文件不存在或为空 ($path)"
        FAILED=$((FAILED + 1))
    fi
}

echo "== mednafen 1.32.1 消费者测试（真跑安装后的 CLI）=="

# [甲] 帮助路径真跑（同时执行 MDFNI_Init 里那 60 项上游内置断言）
run_help "mednafen --help（内含 60 项 MDFN_RunCheapTests 断言）"
grep_check "启动横幅自述 mednafen 1.32.1" "Starting Mednafen 1.32.1"
grep_check "打印了构建信息节" "Build information:"
grep_check "链接到本次打包的 zlib 1.3.1" "Compiled against zlib 1.3.1"
grep_check "链接到本次打包的 SDL2 2.30.10" "Compiled against SDL 2.30.10"
grep_check "链接到本次打包的 libFLAC 1.5.0" "Running with libFLAC 1.5.0"
grep_check "已解析配置目录（GetBaseDirectory）" "Base directory: "
grep_check "注册了模拟模块表（含 apple2/nes/snes/psx）" "Emulation modules: apple2 nes snes"
grep_check "打印 Usage 行" "Usage: "
grep_check "打印 Options 节" "Options:"
grep_check "列出 -help 选项" "-help"

# [乙] 上游扩展测试面真跑（-exptests 触发 MDFNI_RunExpensiveTests 的 12 项）
run "mednafen -exptests（12 项 MDFNI_RunExpensiveTests 断言）" fail \
    mednafen -exptests "$WORK/expt"
grep_check "NVFSTest 走完" "NVFSTest done."
grep_check "ZLInflateFilter 测试走完" "ZLInflateFilter test done."
grep_check "走到 main 收尾（未中途抛异常）" "No game filename specified!"
file_check "扩展测试写出 cfgtest.cfg（配置读写真跑过）" "$WORK/expt/cfgtest.cfg"
file_check "扩展测试写出 streamtest.bin（FileStream 读写实跑过）" "$WORK/expt/streamtest.bin"

# [丙] 负控制：无参数 / 非法选项都必须非零退出，且非法选项不得打印帮助正文
run "mednafen 无参数必须非零退出" fail mednafen
grep_check "无参数给出明确诊断" "No command-line arguments specified"
run "mednafen 非法选项必须非零退出" fail mednafen --no-such-option-zzz
grep_absent "非法选项不打印帮助正文（参数解析判别式生效）" "Options:"

echo "== 消费者测试汇总：$TOTAL 项断言，失败 $FAILED 项 =="
if [ "$FAILED" -ne 0 ]; then
    exit 1
fi
echo "mednafen 1.32.1 test_package: ALL PASSED"
exit 0

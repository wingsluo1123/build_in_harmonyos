#!/data/service/hnp/bin/bash
# test_package/test.sh — indi-apogee 冒烟测试（断言层）
#
# 用法:
#   test.sh <BINDIR>   在 BINDIR 下找 indi_apogee_ccd / indi_apogee_wheel 并运行探针
#   test.sh            不给参数时用 PATH（由 conanrun 提供制品 bin/）
#
# conanfile.py 的 test() 在 OHOS 上会先搭好一个 staging 目录 —— 产物二进制 + 全部 host
# 依赖 libdir 下的 .so 的**已重签副本** —— 把该目录作为 BINDIR 传进来。**本脚本自己把
# BINDIR 前置**进 LD_LIBRARY_PATH（显式冒号拼接，见下方），不依赖调用方设环境变量：
# OHOS loader 先查 LD_LIBRARY_PATH（porting/linux/user/ldso/dynlink.c load_library；
# ada-bar-codes/005 round-15 同结论），而 staging 是自包含的，前置后 loader 不会先去撞
# 缓存里那几个加载不了的 .so 所在 libdir。
#
#   真机实测：HMDFS 上未签名（或签名失效）的 OHOS 共享库无法被 mmap(PROT_EXEC)，报
#   "Error loading shared library <so>: (needed by ...)"。这条报错**不带 errno**，读起来
#   像「搜索路径上找不到」，实际是候选文件被逐个否掉 —— 极易误诊成路径/环境变量问题
#   （知识图谱 E537/R49 的收窄结论；libindi 自己的 test_package 因此改成全静态链接）。
#   给 .so 补上有效自签名即可加载（E077：内核只认有效 .codesign）。
#   staging 里的副本与产物逐字节相同，只多了签名；依赖包与 conan 缓存不动。
#
# 不给 BINDIR 的分支是工具不全时的退化路径：只保证「存在且可执行」，明确告警、不假装跑过。
#
# 断言设计（重要）：
#   INDI 驱动源码里没有 main()，入口由 libindi 的 libs/indibase/indidrivermain.c 提供并编进
#   libindidriver。该 main 只认 -v，随后进入 eventLoop() 阻塞读 stdin，stdin EOF 时 exit(1)。
#   ⇒ 「进程退出码」「-v 打印版本」都不是有效断言。
#   ⇒ 有效断言 = 往 stdin 喂一条 INDI <getProperties>，stdout 必须回出 <def...> 属性定义。
#     它同时证明了：ELF 可加载、依赖 so 可解析、libindi 链接正确、驱动已注册进事件循环。
set -eu

BINDIR="${1:-}"
PROBE='<getProperties version="1.7"/>'

# 自己把 BINDIR **前置**进 LD_LIBRARY_PATH，显式冒号拼接，不依赖调用方（conan 的 EnvVars）
# 给环境变量。两件事都踩过：
#   1) 追加会把 BINDIR 排到 conan/conanrun 给的目录之后；那些目录里的 .so 在 HMDFS 上
#      签名失效、加载不了（见文件头），OHOS loader 撞上先出现的坏候选就不再往后找 ⇒
#      自包含的 staging 等于白搭。前置 + staging 自包含则根本不会去撞它们。
#   2) 2026-10-03 实测旧写法拼出的值里是「<某 libdir>: /storage/…/stage」——冒号后带空格
#      ⇒ " /storage/…" 是无效目录，staging 压根没上路径。自己拼就没有中间人。
# BINDIR 为空时不动 LD_LIBRARY_PATH，保持退化分支的旧行为。
if [ -n "$BINDIR" ]; then
    LD_LIBRARY_PATH="$BINDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export LD_LIBRARY_PATH
fi

fail=0

resolve_bin() {
    if [ -n "$BINDIR" ]; then
        printf '%s/%s\n' "$BINDIR" "$1"
        return 0
    fi
    command -v "$1" 2>/dev/null || true
    return 0
}

check_binary() {
    bin="$1"
    path="$(resolve_bin "$bin")"
    if [ -z "$path" ]; then
        echo "FAIL: $bin 不在 PATH 中（未指定 BINDIR，且 conanrun 未提供制品 bin/）"
        return 1
    fi
    if [ ! -f "$path" ]; then
        echo "FAIL: $bin 不存在 -> $path"
        return 1
    fi
    if [ ! -x "$path" ]; then
        echo "FAIL: $bin 不可执行 -> $path"
        return 1
    fi
    echo "OK: $bin 存在且可执行 -> $path"
    return 0
}

check_indi_roundtrip() {
    bin="$1"
    path="$(resolve_bin "$bin")"
    if [ -z "$path" ] || [ ! -x "$path" ]; then
        echo "FAIL: $bin 无法执行，跳过 getProperties 往返"
        return 1
    fi
    # 驱动的 stdin EOF 会让 eventLoop() 以非 0 退出，属正常，故 || true
    out="$(printf '%s\n' "$PROBE" | "$path" 2>&1 || true)"
    if printf '%s\n' "$out" | grep -q '<def'; then
        n="$(printf '%s\n' "$out" | grep -c '<def' || true)"
        echo "OK: $bin 响应 getProperties，返回 $n 条属性定义"
        return 0
    fi
    echo "FAIL: $bin 未对 getProperties 回出任何 <def...> 属性定义，输出前 20 行："
    printf '%s\n' "$out" | head -20 | sed 's/^/    /'
    # 诊断：给出探针路径与 loader 实际看到的搜索路径，便于区分
    # 「so 不在路径上」与「so 在路径上但被拒（无 errno，签名问题）」
    echo "  (诊断) BINDIR=${BINDIR:-<未设置>}"
    echo "  (诊断) LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<未设置>}"
    return 1
}

for b in indi_apogee_ccd indi_apogee_wheel; do
    check_binary "$b" || fail=1
    check_indi_roundtrip "$b" || fail=1
done

if [ "$fail" -ne 0 ]; then
    echo "[test] indi-apogee 冒烟测试失败"
    exit 1
fi

echo "[test] indi-apogee 冒烟测试通过（2 个二进制 × 存在性 + INDI getProperties 往返）"

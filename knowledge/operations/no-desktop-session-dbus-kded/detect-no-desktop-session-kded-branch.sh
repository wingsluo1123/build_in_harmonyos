#!/bin/sh
# detect-no-desktop-session-kded-branch.sh
#   检测上游工程是否属于「桌面会话 / KDED 绑定」问题域，并给出分层判定。
#
# 用法:
#   sh detect-no-desktop-session-kded-branch.sh <上游源码目录>
#
# 退出码:
#   0 = 命中（按同目录 strategy.md 选择处理策略）
#   1 = 未命中（该包与此主题无关，无需策略）
#   2 = 用法/路径错误
#
# 判定分层（与 README.md「问题识别」一致）:
#   类型 A 形态开关型 —— 源码用能力宏（如 KPty_HAVE_UTEMPTER）联动 BUILD_AS_EXECUTABLE
#          之类的形态选项，平台能力为假时自动切到无会话形态。→ 零补丁，靠平台能力宏兜底
#   类型 B 插件绑定型 —— 工程 find_package(KF6DBusAddons ...) 且产物是 KDED 插件
#          （K_PLUGIN_FACTORY_WITH_JSON / KDEDModule / X-KDE-Library）。→ 走 strategy.md 分层策略
#   类型 C 会话服务型 —— 代码直接使用会话 D-Bus（QDBusConnection::sessionBus /
#          org.kde.kded / org.kde.kglobalaccel 等）。→ 走 strategy.md 分层策略
# 安全模式（code-style 规则 7）：-e 生效处已对“预期非零”的命令兜底——grep 无匹配（该模式 0 命中）
# 退出码为 1，由 count_of/files_of 内部的 `|| true` 吸收；否则第一个无命中的模式就会让脚本提前
# 以 1 退出，被误读成 MISS。
set -eu -o pipefail

SRC="${1:-}"
if [ -z "$SRC" ]; then
    echo "usage: sh $0 <upstream-source-dir>"
    exit 2
fi
if [ ! -d "$SRC" ]; then
    echo "ERROR: not a directory: $SRC"
    exit 2
fi

# 最多列 3 个命中文件（用 sed 限行，避免管道到 head 产生 SIGPIPE）
# 0 命中（grep 退出码 1）是正常输入：两个函数都以 `|| true` 吸收非零，保证 set -e 下仍取到 "0"/空串
files_of() {
    grep -rIl -m1 -e "$1" "$SRC" --exclude-dir=.git 2>/dev/null | sed -n '1,3p' || true
}
count_of() {
    grep -rIl -m1 -e "$1" "$SRC" --exclude-dir=.git 2>/dev/null | wc -l | tr -d ' ' || true
}

A_ABI_MACRO="$(count_of 'KPty_HAVE_UTEMPTER')"
A_FORM_OPTION="$(count_of 'cmake_dependent_option')"
B_DBUSADDONS="$(count_of 'KF6DBusAddons')"
B_PLUGIN_JSON="$(count_of 'K_PLUGIN_FACTORY_WITH_JSON')"
B_KDED_MODULE="$(count_of 'KDEDModule')"
B_KDE_LIBRARY="$(count_of 'X-KDE-Library')"
C_SESSION_BUS="$(count_of 'QDBusConnection::sessionBus')"
C_KDED_BUS="$(count_of 'org.kde.kded')"
C_KGLOBAL="$(count_of 'org.kde.kglobalaccel')"
C_SYSTEMDUSER="$(count_of 'systemd --user')"

TYPE_A=0
if [ "$A_ABI_MACRO" -gt 0 ] && [ "$A_FORM_OPTION" -gt 0 ]; then
    TYPE_A=1
fi
TYPE_B=0
if [ "$B_DBUSADDONS" -gt 0 ] && { [ "$B_PLUGIN_JSON" -gt 0 ] || [ "$B_KDED_MODULE" -gt 0 ] || [ "$B_KDE_LIBRARY" -gt 0 ]; }; then
    TYPE_B=1
fi
TYPE_C=0
if [ "$C_SESSION_BUS" -gt 0 ] || [ "$C_KDED_BUS" -gt 0 ] || [ "$C_KGLOBAL" -gt 0 ] || [ "$C_SYSTEMDUSER" -gt 0 ]; then
    TYPE_C=1
fi

echo "== 无桌面会话 / KDED 绑定检测 =="
echo "SRC         = $SRC"
echo "TYPE_A_capability_switch = $TYPE_A   (KPty_HAVE_UTEMPTER=$A_ABI_MACRO, cmake_dependent_option=$A_FORM_OPTION)"
echo "TYPE_B_kded_plugin       = $TYPE_B   (KF6DBusAddons=$B_DBUSADDONS, K_PLUGIN_FACTORY_WITH_JSON=$B_PLUGIN_JSON, KDEDModule=$B_KDED_MODULE, X-KDE-Library=$B_KDE_LIBRARY)"
echo "TYPE_C_session_service   = $TYPE_C   (sessionBus=$C_SESSION_BUS, org.kde.kded=$C_KDED_BUS, kglobalaccel=$C_KGLOBAL, systemd-user=$C_SYSTEMDUSER)"
echo "-- 证据 --"
if [ "$TYPE_A" -eq 1 ]; then
    echo "A1 $(files_of 'KPty_HAVE_UTEMPTER' | sed -n '1p')"
    echo "A2 $(files_of 'cmake_dependent_option' | sed -n '1p')"
fi
if [ "$TYPE_B" -eq 1 ]; then
    echo "B1 $(files_of 'KF6DBusAddons' | sed -n '1p')"
    echo "B2 $(files_of 'K_PLUGIN_FACTORY_WITH_JSON' | sed -n '1p')"
fi
if [ "$TYPE_C" -eq 1 ]; then
    echo "C1 $(files_of 'QDBusConnection::sessionBus' | sed -n '1p')"
    echo "C2 $(files_of 'org.kde.kded' | sed -n '1p')"
fi
echo "-- 建议动作 --"
if [ "$TYPE_A" -eq 1 ]; then
    echo "HIT  A：上游自带无会话形态开关 —— 先确认本平台依赖包导出的能力宏值（如 KPty_HAVE_UTEMPTER），"
    echo "     为假即自动走无会话分支，无需补丁；验证方式见同目录 sample/ + reproduce.sh。"
fi
if [ "$TYPE_B" -eq 1 ] || [ "$TYPE_C" -eq 1 ]; then
    echo "HIT  B/C：存在会话/KDED 绑定 —— 按 strategy.md 分层：能切形态则切（P1），不能切则用中性符号探测"
    echo "     降级（P2），仍不可行才标记平台不支持（P3，env_unsupported），禁止伪造会话总线。"
fi
if [ "$TYPE_A" -eq 0 ] && [ "$TYPE_B" -eq 0 ] && [ "$TYPE_C" -eq 0 ]; then
    echo "MISS 未命中：本包不涉及桌面会话 / KDED 绑定，无需本主题策略。"
    exit 1
fi
exit 0

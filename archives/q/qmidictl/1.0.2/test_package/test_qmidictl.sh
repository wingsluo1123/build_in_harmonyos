#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# qmidictl/1.0.2 consumer probe (OHOS aarch64)
#
# Usage: test_qmidictl.sh <package_bin_dir> <package_root>
#
# R34: 全部断言落在被测包真实产出的可执行文件/安装资源上；先 exec 二进制
# （--version / --help），再核对 ELF 头与 DT_NEEDED 中的 Qt6 运行库。
# 规避 SIGPIPE：不使用 `cmd | head` 这类管道短路，输出统一收进变量。
# ---------------------------------------------------------------------------
set -u

BIN_DIR="${1:?usage: test_qmidictl.sh <bin_dir> <package_root>}"
PKG_ROOT="${2:-$(dirname "$BIN_DIR")}"
BIN="${BIN_DIR}/qmidictl"

PASS=0
FAIL=0
FAILED_NAMES=""

ok() {
  PASS=$((PASS + 1))
  printf '  [PASS] %s\n' "$1"
}

ko() {
  FAIL=$((FAIL + 1))
  FAILED_NAMES="${FAILED_NAMES} $1"
  printf '  [FAIL] %s -- %s\n' "$1" "$2"
}

contains() {
  case "$1" in
    *"$2"*) return 0 ;;
    *) return 1 ;;
  esac
}

printf '== qmidictl consumer probe ==\n'
printf '   bin: %s\n' "${BIN}"

# --- TP-001 打包的二进制存在 ------------------------------------------------
if [ -f "${BIN}" ]; then
  ok "TP-001 binary present"
else
  ko "TP-001 binary present" "missing ${BIN}"
  printf '\nRESULT: PASSED (%d/%d)\n' "${PASS}" "$((PASS + FAIL))"
  exit 1
fi

# --- TP-002 ELF 头 ----------------------------------------------------------
ELF_MAGIC=$(od -An -tx1 -N4 "${BIN}" 2>/dev/null | tr -d ' \n')
if [ "${ELF_MAGIC}" = "7f454c46" ]; then
  ok "TP-002 ELF header"
else
  ko "TP-002 ELF header" "magic=${ELF_MAGIC}"
fi

# --- TP-003 DT_NEEDED 中链接了 Qt6 Core/Widgets/Gui/Svg/Network -----------------
# 注：conan 的 test() 环境（env="conanrun"）会重排 PATH / LD_LIBRARY_PATH，外部
# 工具（grep 等）在该环境下可能取不到，若再 `2>/dev/null` 就会"静默空值 → 假失败"。
# 这里改为多工具探测（readelf 优先，grep 兜底，均试绝对路径）+ 纯 bash 解析，
# 并把工具错误打到日志，保证结论可解释。
scan_needed() {
  local bin="$1" tool out rc line entry
  for tool in readelf llvm-readelf /data/service/hnp/bin/readelf /usr/bin/readelf; do
    command -v "$tool" >/dev/null 2>&1 || [ -x "$tool" ] || continue
    out=$("$tool" -d "$bin" 2>&1)
    rc=$?
    if [ "${rc}" -ne 0 ]; then
      printf '   [scan] %s rc=%s err=%s\n' "${tool}" "${rc}" "${out%%$'\n'*}"
      continue
    fi
    case "${out}" in
      *"Shared library:"*)
        while IFS= read -r line; do
          case "${line}" in
            *"Shared library: ["*"]"*)
              entry="${line#*Shared library: [}"
              entry="${entry%%]*}"
              printf '%s\n' "${entry}"
              ;;
          esac
        done <<EOF
${out}
EOF
        return 0
        ;;
    esac
  done
  for tool in grep /usr/bin/grep /bin/grep /data/service/hnp/bin/grep; do
    command -v "$tool" >/dev/null 2>&1 || [ -x "$tool" ] || continue
    out=$(LC_ALL=C "$tool" -a -o -E 'lib[A-Za-z0-9_.+-]*\.so\.[0-9]+' "$bin" 2>&1)
    rc=$?
    if [ "${rc}" -eq 0 ] && [ -n "${out}" ]; then
      printf '%s\n' "${out}"
      return 0
    fi
    printf '   [scan] %s rc=%s err=%s\n' "${tool}" "${rc}" "${out%%$'\n'*}"
  done
  return 1
}

if NEEDED=$(scan_needed "${BIN}"); then
  NEEDED_FLAT="${NEEDED//$'\n'/ }"
  ok "TP-003 read DT_NEEDED (${NEEDED_FLAT})"
else
  NEEDED=""
  NEEDED_FLAT=""
  ko "TP-003 read DT_NEEDED" "no usable readelf/grep in this environment"
fi

for lib in libQt6Core.so.6 libQt6Widgets.so.6 libQt6Gui.so.6 libQt6Svg.so.6 libQt6Network.so.6; do
  if contains "${NEEDED_FLAT}" "${lib}"; then
    ok "TP-003 linked ${lib}"
  else
    ko "TP-003 linked ${lib}" "dt_needed=[${NEEDED_FLAT}]"
  fi
done

# --- TP-004/005 真实 exec：--version / --help（offscreen，不开窗）-----------
export QT_QPA_PLATFORM=offscreen
export QT_LOGGING_RULES="qt.qpa.*=false"

VERSION_OUT=$(QT_QPA_PLATFORM=offscreen "${BIN}" --version 2>&1)
VERSION_RC=$?
if contains "${VERSION_OUT}" "1.0.2"; then
  ok "TP-004 --version reports 1.0.2"
else
  ko "TP-004 --version reports 1.0.2" "rc=${VERSION_RC} out=$(printf '%s' "${VERSION_OUT}" | tr '\n' '|')"
fi

if contains "${VERSION_OUT}" "QmidiCtl"; then
  ok "TP-005 --version reports program name"
else
  ko "TP-005 --version reports program name" "out=$(printf '%s' "${VERSION_OUT}" | tr '\n' '|')"
fi

HELP_OUT=$("${BIN}" --help 2>&1)
HELP_RC=$?
if contains "${HELP_OUT}" "--udp-port"; then
  ok "TP-006 --help documents --udp-port"
else
  ko "TP-006 --help documents --udp-port" "rc=${HELP_RC} out=$(printf '%s' "${HELP_OUT}" | tr '\n' '|')"
fi

if contains "${HELP_OUT}" "--interface"; then
  ok "TP-007 --help documents --interface"
else
  ko "TP-007 --help documents --interface" "rc=${HELP_RC} out=$(printf '%s' "${HELP_OUT}" | tr '\n' '|')"
fi

# --- TP-008/009/010 安装的桌面资源（消费者安装后可用的真实产物）-------------
DESKTOP="${PKG_ROOT}/share/applications/org.rncbc.qmidictl.desktop"
if [ -f "${DESKTOP}" ]; then
  ok "TP-008 desktop entry installed"
else
  ko "TP-008 desktop entry installed" "missing ${DESKTOP}"
fi

SVG_ICON="${PKG_ROOT}/share/icons/hicolor/scalable/apps/org.rncbc.qmidictl.svg"
if [ -f "${SVG_ICON}" ]; then
  ok "TP-009 scalable icon installed"
else
  ko "TP-009 scalable icon installed" "missing ${SVG_ICON}"
fi

MAN_PAGE="${PKG_ROOT}/share/man/man1/qmidictl.1"
if [ -f "${MAN_PAGE}" ]; then
  ok "TP-010 man page installed"
else
  ko "TP-010 man page installed" "missing ${MAN_PAGE}"
fi

# --- TP-011 许可证文件随包安装 ----------------------------------------------
if [ -f "${PKG_ROOT}/licenses/LICENSE" ]; then
  ok "TP-011 license file packaged"
else
  ko "TP-011 license file packaged" "missing ${PKG_ROOT}/licenses/LICENSE"
fi

TOTAL=$((PASS + FAIL))
printf '\nRESULT: '
if [ "${FAIL}" -eq 0 ]; then
  printf 'PASSED (%d/%d)\n' "${PASS}" "${TOTAL}"
  exit 0
fi
printf 'FAILED (%d/%d), failed:%s\n' "${PASS}" "${TOTAL}" "${FAILED_NAMES}"
exit 1

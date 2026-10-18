#!/bin/sh
# test_pnmixer.sh — pnmixer 0.7.2 消费者测试：结构性 / 链接性 / 安装面断言（R34/R51）。
#
# 本脚本只做**不需要执行被测二进制**的断言，因此必须始终真正通过；一旦产物被
# 移走或缺少安装面文件，必须真正失败（CI 的 L1e 破坏性反向验证依赖这一点）：
#   1-2. bin/pnmixer 存在且可执行
#   3.   产物是合法 ELF
#   4-7. DT_NEEDED 记录 gtk-3 / asound / X11 / glib-2.0（上游 pkg_check_modules
#         的四个必需模块）+ libgdk-3（GTK3 的 GDK 库）—— 证明交付物真的链接了
#         这些模块，不是空壳；libnotify 则断言**不在**链接面（故意 OFF，见下）
#   8.   libnotify 未被链接（WITH_LIBNOTIFY=OFF 的负向断言）
#   9.   .codesign 段存在（OHOS 签名是产物可加载的前提）
#   10-14. 安装面：desktop / icon / man / pixmaps / gtk3 glade 全部落盘
#
# CLI 契约（--version / --help / 错误选项 / 无显示失败路径）需要**真正执行**
# 二进制，由 test_package/conanfile.py 的 test() 直接运行，并按已声明的 OHOS
# 运行期限制特征容忍（先例：已合入的 pasystray/0.8.2、pavucontrol-qt/2.4.0）。
#
# 用法：test_pnmixer.sh <path-to-pnmixer-binary> <package-folder>
# 退出码：全部通过 0，否则 1；末行打印机器可读汇总。
set -u

BIN="${1:?usage: test_pnmixer.sh <path-to-pnmixer> <package-folder>}"
PKG="${2:?usage: test_pnmixer.sh <path-to-pnmixer> <package-folder>}"

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

ok()  { TOTAL=$((TOTAL + 1)); PASSED=$((PASSED + 1)); printf '  PASS  %s\n' "$1"; }
bad() { TOTAL=$((TOTAL + 1)); FAILED=$((FAILED + 1)); printf '  FAIL  %s\n' "$1"; }
skip(){ SKIPPED=$((SKIPPED + 1)); printf '  SKIP  %s\n' "$1"; }

echo "== pnmixer 0.7.2 test_package (structural): $BIN"
echo "== package folder: $PKG"

# --- 1-2. 产物存在且可执行 ------------------------------------------------
if [ -f "$BIN" ]; then ok "binary exists"; else bad "binary missing: $BIN"; fi
if [ -x "$BIN" ]; then ok "binary is executable"; else bad "binary not executable"; fi

# --- 3. 合法 ELF ---------------------------------------------------------
if [ -f "$BIN" ]; then
  MAGIC=$(head -c 4 "$BIN" 2>/dev/null | od -An -tx1 2>/dev/null | tr -d ' \n' || true)
  if [ "$MAGIC" = "7f454c46" ]; then
    ok "binary is a valid ELF (magic 7f454c46)"
  else
    bad "not a valid ELF (magic '$MAGIC')"
  fi
else
  bad "cannot check ELF magic: binary missing"
fi

# --- 4-8. DT_NEEDED 覆盖上游五个 pkg-config 模块 --------------------------
READELF=""
for c in /data/service/hnp/bin/llvm-readelf /data/service/hnp/bin/readelf \
         /usr/bin/llvm-readelf /usr/bin/readelf /system/bin/readelf; do
  if [ -x "$c" ]; then READELF="$c"; break; fi
done
if [ -n "$READELF" ] && [ -f "$BIN" ]; then
  NEEDED=$("$READELF" -d "$BIN" 2>/dev/null || true)
  if [ -z "$NEEDED" ]; then
    # -d 不可用时退回字符串扫描，避免静默 PASS
    NEEDED=$(strings "$BIN" 2>/dev/null || true)
  fi
  case "$NEEDED" in
    *libgtk-3.so*)    ok "DT_NEEDED links libgtk-3 (=gtk+-3.0)" ;;
    *) bad "DT_NEEDED is missing libgtk-3.so (gtk+-3.0 module)" ;;
  esac
  case "$NEEDED" in
    *libasound.so*)   ok "DT_NEEDED links libasound (=alsa module)" ;;
    *) bad "DT_NEEDED is missing libasound.so (alsa module)" ;;
  esac
  case "$NEEDED" in
    *libgdk-3.so*)    ok "DT_NEEDED links libgdk-3 (GTK3's GDK)" ;;
    *) bad "DT_NEEDED is missing libgdk-3.so" ;;
  esac
  case "$NEEDED" in
    *libX11.so*)      ok "DT_NEEDED links libX11 (=x11 module)" ;;
    *) bad "DT_NEEDED is missing libX11.so (x11 module)" ;;
  esac
  case "$NEEDED" in
    *libglib-2.0.so*) ok "DT_NEEDED links libglib-2.0 (=glib-2.0 module)" ;;
    *) bad "DT_NEEDED is missing libglib-2.0.so (glib-2.0 module)" ;;
  esac
  # libnotify 是**故意不链**的（WITH_LIBNOTIFY=OFF）：制品仓 libnotify/0.8.3 的
  # libnotify.so.4.0.0 签名被 OHOS 加载器拒绝（dlopen → Permission denied），
  # 链上它交付物就完全起不来。这里断言它确实不在链接面里。
  case "$NEEDED" in
    *libnotify.so*)   bad "DT_NEEDED links libnotify.so although WITH_LIBNOTIFY=OFF" ;;
    *) ok "DT_NEEDED has no libnotify.so (notifications intentionally off)" ;;
  esac
  # --- 9. OHOS 签名段 ---------------------------------------------------
  SECTIONS=$("$READELF" -SW "$BIN" 2>/dev/null || true)
  case "$SECTIONS" in
    *.codesign*) ok "ELF carries an OHOS .codesign section (signed artifact)" ;;
    *) bad "ELF has no .codesign section (unsigned artifact cannot be loaded)" ;;
  esac
else
  skip "no readelf available; ELF/DT_NEEDED/.codesign assertions not counted"
fi

# --- 10-14. 安装面 ------------------------------------------------------
for spec in \
  "share/applications/pnmixer.desktop:desktop entry" \
  "share/icons/hicolor/128x128/apps/pnmixer.png:hicolor application icon" \
  "share/man/man1/pnmixer.1:man page" \
  "share/pnmixer/pixmaps/pnmixer-high.png:tray pixmap set" \
  "share/pnmixer/ui/popup-menu-gtk3.glade:gtk3 glade UI file"
do
  rel="${spec%%:*}"
  label="${spec#*:}"
  if [ -f "$PKG/$rel" ]; then
    ok "installed data present: $rel ($label)"
  else
    bad "installed data missing: $rel ($label)"
  fi
done

printf 'HMBS_TEST_PACKAGE_STRUCTURAL={"total":%s,"passed":%s,"failed":%s,"skipped":%s}\n' \
  "$TOTAL" "$PASSED" "$FAILED" "$SKIPPED"
[ "$FAILED" -eq 0 ] || exit 1
exit 0

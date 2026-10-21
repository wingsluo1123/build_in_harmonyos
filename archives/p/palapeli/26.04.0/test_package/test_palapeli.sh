#!/bin/sh
# test_palapeli.sh <package_folder>
#   安装产物完整性 + OHOS 可移植性断言（E537 口径：不得残留路径型 DT_NEEDED）。
#   切图算法的真实功能验证在同目录的 consumer.cpp 里做（conan test 会先跑它）。
#
#   不在 CI 里执行 bin/palapeli：它是 KXmlGui GUI 程序，启动即需要 QPA 平台插件
#   与会话环境；无桌面会话的构建机上跑它只会得到平台插件缺失的假失败。
#   程序本体的可加载性由 DT_NEEDED 断言 + 插件 ABI 断言覆盖。
set -eu

PKG=${1:-}
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "usage: $0 <package_folder>" >&2
    exit 2
fi

FAILS=0
ok()   { echo "ASSERT-OK   $*"; }
bad()  { echo "ASSERT-FAIL $*"; FAILS=$((FAILS + 1)); }

need_file() {   # need_file <relative path> <可执行?>
    p="$PKG/$1"
    if [ ! -e "$p" ]; then
        bad "缺少产物 $1"
    elif [ "${2:-}" = "x" ] && [ ! -x "$p" ]; then
        bad "产物不可执行 $1"
    else
        ok "产物存在 $1"
    fi
}

# ── 产物清单 ─────────────────────────────────────────────────────────────
need_file bin/palapeli x
need_file lib/libpala.so
need_file lib/plugins/kf6/thumbcreator/palathumbcreator.so
need_file lib/plugins/palapelislicers/palapeli_rectslicer.so
need_file lib/plugins/palapelislicers/palapeli_jigsawslicer.so
need_file lib/plugins/palapelislicers/palapeli_goldbergslicer.so
need_file share/mime/packages/palapeli-mimetypes.xml
need_file share/applications/org.kde.palapeli.desktop

# MIME 数据库缓存：仅当 shared-mime-info 工具可用（tool_requires）时才由
# update_xdg_mimetypes() 生成，属于可选产物 —— 有则校验其非空。
if [ -f "$PKG/share/mime/mime.cache" ]; then
    if [ -s "$PKG/share/mime/mime.cache" ]; then
        ok "mime.cache 已生成且非空 (update-mime-database 生效)"
    else
        bad "mime.cache 为空"
    fi
else
    echo "ASSERT-INFO mime.cache 未生成（构建期无 shared-mime-info 工具，属预期分支）"
fi

# ── ELF 断言 ─────────────────────────────────────────────────────────────
READELF=""
for cand in llvm-readelf readelf; do
    if command -v "$cand" > /dev/null 2>&1; then
        READELF=$cand
        break
    fi
done
[ -n "$READELF" ] || { echo "ASSERT-SKIP 未找到 readelf，跳过 DT_NEEDED 断言"; }

needed() {   # needed <elf> -> 每行一个 DT_NEEDED 名
    "$READELF" -d "$1" 2>/dev/null | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p'
}

if [ -n "$READELF" ]; then
    for elf in "$PKG/bin/palapeli" "$PKG/lib/libpala.so" \
               "$PKG/lib/plugins/kf6/thumbcreator/palathumbcreator.so" \
               "$PKG/lib/plugins/palapelislicers/palapeli_rectslicer.so"; do
        [ -f "$elf" ] || continue
        base=$(basename "$elf")
        pathform=$(needed "$elf" | grep -c '/' || true)
        if [ "${pathform:-0}" -eq 0 ]; then
            ok "$base 无路径型 DT_NEEDED（E537 口径）"
        else
            bad "$base 残留 $pathform 条路径型 DT_NEEDED"
        fi
    done

    # 真实消费依赖闭包：主程序必须直接依赖 libkdegames（KDEGames6）
    if needed "$PKG/bin/palapeli" | grep -q '^libKDEGames6\.so'; then
        ok "bin/palapeli 直接依赖 libKDEGames6.so（闭包真实生效）"
    else
        bad "bin/palapeli 未依赖 libKDEGames6.so"
    fi

    # 注意：OHOS 构建链下 CMake 不会给共享库加版本号/SONAME。最小复现（普通
    # add_library(SHARED) + VERSION/SOVERSION，同一 cmake+clang 组合）也只产出
    # libfoo.so 且链接命令里没有 -Wl,-soname，与本包无关，因此这里不断言 SONAME。
    # 对第三方消费真正关键的是导出符号是否完整（-fvisibility/导出宏是否生效）。
    NM=""
    for cand in llvm-nm nm; do
        if command -v "$cand" > /dev/null 2>&1; then
            NM=$cand
            break
        fi
    done
    if [ -n "$NM" ]; then
        syms=$("$NM" -D --defined-only "$PKG/lib/libpala.so" 2>/dev/null || true)
        miss=""
        for sym in _ZN4Pala6Slicer7processEPNS_9SlicerJobE _ZNK4Pala9SlicerJob6piecesEv; do
            case "$syms" in
                *"$sym"*) : ;;
                *) miss="$miss $sym" ;;
            esac
        done
        if [ -z "$miss" ]; then
            ok "libpala.so 导出 Slicer::process / SlicerJob::pieces"
        else
            bad "libpala.so 缺少导出符号:$miss"
        fi
    else
        echo "ASSERT-SKIP 未找到 nm，跳过导出符号断言"
    fi
fi

echo "RESULT: failures=$FAILS"
[ "$FAILS" -eq 0 ] || exit 1

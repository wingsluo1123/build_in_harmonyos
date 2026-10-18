#!/system/bin/sh
set -eu
set -o pipefail
if [ "$#" -ne 3 ]; then
    printf "usage: %s PACKAGE_FOLDER MOVED_FOLDER TEST_R_SCRIPT\n" "$0" >&2
    exit 64
fi
package=$1
moved=$2
script=$3
if [ ! -x "$package/bin/R" ] || [ ! -x "$package/bin/Rscript" ]; then
    printf "missing R launchers in package: %s\n" "$package" >&2
    exit 66
fi
if [ ! -f "$script" ]; then
    printf "missing R test script: %s\n" "$script" >&2
    exit 66
fi
rm -rf "$moved"
mkdir -p "$moved"
cp -R "$package"/. "$moved"/
# 非 ELF 文件（脚本/配置）直接扫描构建机路径；ELF 文件的原始 grep 会命中
# openssl/3.5.6.1 发布二进制自带的构建信息串（libcrypto.a 内嵌
# "compiler: clang ... -I$HOME/usr/local/include"，静态链入 libcurl.so），
# 与 conanfile _reject_build_paths 的白名单语义对齐：ELF 的运行时路径
# 违规由下方 readelf -d 的 NEEDED/RPATH/RUNPATH 闭包检查覆盖，
# 构建元数据字符串由配方级 _reject_build_paths 字节扫描（含白名单）覆盖。
for elf_probe in $(find "$moved" -type f); do
    if /data/service/hnp/bin/llvm-readelf -h "$elf_probe" >/dev/null 2>&1; then
        continue
    fi
    # HOME 未设置/为空时 $HOME 退化为空正则（恒匹配任意行），必须前置非空守卫
    if [ -n "$HOME" ] && grep -a -n -E "$HOME|[.]conan2|[.]conan-build-r-base" "$elf_probe"; then
        printf "non-relocatable build/cache path found in moved package: %s\n" "$elf_probe" >&2
        exit 1
    fi
done
unset R_HOME RHOME R_SHARE_DIR R_INCLUDE_DIR R_DOC_DIR CURL_CA_BUNDLE SSL_CERT_FILE SSL_CERT_DIR LD_LIBRARY_PATH
export PATH="/data/service/hnp/bin:/system/bin:/bin:/usr/bin"

# Make both the original target package and every original dependency package
# physically inaccessible while exercising the moved copy.  Always restore the
# cache permission, including failure paths.
# Cache 根不得硬编码：CI worker 上 CONAN_HOME 可能被重定向（如 ~/.cache/conan2），
# 本机默认 ~/.conan2。目录不存在时跳过遮蔽（可移植性检查仍执行），
# 禁止在 set -e 下对缺失路径 stat 直接中止整个测试（PR #13992 教训）。
cache_root=${CONAN_HOME:-$HOME/.conan2}
harmonybrew_root=$HOME/.harmonybrew
cache_mode=
harmonybrew_mode=
if [ -d "$cache_root" ]; then
    cache_mode=`stat -c %a "$cache_root"`
fi
# layer 2 (harmonybrew 前缀根) 是纵深防御层的可选项：仅在该根实际存在时才遮蔽。
if [ -d "$harmonybrew_root" ]; then
    harmonybrew_mode=`stat -c %a "$harmonybrew_root"`
fi
restore_hidden_roots() {
    if [ -n "$cache_mode" ]; then
        chmod "$cache_mode" "$cache_root"
    fi
    if [ -n "$harmonybrew_mode" ]; then
        chmod "$harmonybrew_mode" "$harmonybrew_root"
    fi
}
trap restore_hidden_roots EXIT HUP INT TERM
if [ -n "$cache_mode" ]; then
    chmod 000 "$cache_root"
fi
if [ -n "$harmonybrew_mode" ]; then
    chmod 000 "$harmonybrew_root"
fi

rhome=`"$moved/bin/R" RHOME`
test "$rhome" = "$moved/lib/R"
"$moved/bin/R" --vanilla --slave -f "$script"
"$moved/bin/Rscript" --vanilla -e "stopifnot(getRversion() == '4.5.1'); cat('R_BASE_RSCRIPT=PASS\n')"

# 端到端消费者用例（rule12）：生产者 R 进程落盘 CSV → 独立 Rscript 子进程
# 作为真实消费者拟合线性模型并回写结果 → 生产者回读验证。工作目录放在
# moved 副本旁（/tmp 只读，E002，不可作 tempdir；HMDFS chmod 不生效，
# E046，不能用 000 遮蔽语义），成功与失败路径均清理。
script_dir=`dirname "$script"`
e2e_work="$moved-e2e-work"
rm -rf "$e2e_work"
mkdir -p "$e2e_work"
e2e_status=0
"$moved/bin/Rscript" --vanilla "$script_dir/test_consumer_e2e.R" "$e2e_work" || e2e_status=$?
rm -rf "$e2e_work"
test "$e2e_status" -eq 0
for elf in `find "$moved" -type f`; do
    if /data/service/hnp/bin/llvm-readelf -h "$elf" >/dev/null 2>&1; then
        dyn=`/data/service/hnp/bin/llvm-readelf -d "$elf" 2>/dev/null`
        if printf "%s\n" "$dyn" | grep -E "RPATH|RUNPATH" | grep -E "/storage/Users|[.]conan2|[.]conan-build"; then
            exit 1
        fi
        for needed in `printf "%s\n" "$dyn" | sed -n "s/.*Shared library: \[\(.*\)\]/\1/p"`; do
            case "$needed" in
                libc.so|libdl.so|libm.so|librt.so|libpthread.so) ;;
                *) test -e "$moved/lib/R/lib/$needed" || {
                    printf "unsatisfied packaged ELF NEEDED: %s needs %s\n" "$elf" "$needed" >&2
                    exit 1
                } ;;
            esac
        done
    fi
done
restore_hidden_roots
trap - EXIT HUP INT TERM
if [ -n "$cache_mode" ]; then
    printf "R_BASE_CACHE_MASK=PASS
"
else
    printf "R_BASE_CACHE_MASK=SKIPPED (root absent: %s)
" "$cache_root"
fi
if [ -n "$harmonybrew_mode" ]; then
    printf "R_BASE_HARMONYBREW_MASK=PASS
"
else
    printf "R_BASE_HARMONYBREW_MASK=SKIPPED (root absent: %s)
" "$harmonybrew_root"
fi
printf "R_BASE_RELOCATION_NEGATIVE_TEST=PASS
"

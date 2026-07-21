#!/bin/bash
#=============================================================================
# rebuild_perl_xs.sh — Perl 5.42.0 → 5.42.2 批量重新编译脚本
#=============================================================================
set -euo pipefail

REPO_DIR="/storage/Users/currentUser/build_in_harmonyos"
CONAN_USER="ohpcd"
CONAN_CHANNEL="stable"
DRY_RUN=false
ONLY_PKG=""

# 环境变量
export PERL5LIB="/storage/Users/currentUser/usr/local/perl_5.42.2/lib/5.42.2/aarch64-linux:/storage/Users/currentUser/usr/local/perl_5.42.2/lib/5.42.2"
export C_INCLUDE_PATH="/storage/Users/currentUser/usr/local/include"
export LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib"
export TMPDIR="/storage/Users/currentUser/build_in_harmonyos/.tmp"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=true; shift ;;
    --only)     ONLY_PKG="$2"; shift 2 ;;
    *)          echo "未知参数: $1"; exit 1 ;;
  esac
done

mkdir -p "$TMPDIR"

# Perl 版本检查
PERL_VER=$(perl -MConfig -e 'print "$Config{version}"')
echo "当前 Perl 版本: $PERL_VER"
if [[ "$PERL_VER" != "5.42.2" ]]; then
  echo "❌ Perl 版本不是 5.42.2"
  exit 1
fi
echo "✅ Perl 5.42.2 已就绪"
echo ""

# XS 模块列表
XS_PACKAGES=(
  perl-crypt-cast5/0.05-r14
  perl-crypt-openssl-dsa/0.20
  perl-dbd-pg/3.18.0
  perl-dbd-sqlite/1.78
  perl-dbi/1.637
  perl-devel-lexalias/0.05
  perl-digest-md5/2.59
  perl-digest-sha1/2.13
  perl-digest-sha3/1.01
  perl-encode-hanextra/0.23
  perl-encode-jis2k/0.05-r2
  perl-ev/4.35
  perl-html-parser/3.83-r1
  perl-http-parser-xs/0.17-r9
  perl-io-tty/1.20-r2
  perl-ipc-sharelite/0.17-r14
  perl-json-xs/4.04
  perl-json-maybexs/1.004008-r0
  perl-list-moreutils-xs/0.430-r6
  perl-locale-gettext/1.07-r2
  perl-match-simple-xs/0.002
  perl-math-pari/2.030528-r1
  perl-math-random-mt-auto/6.23-r10
  perl-mime-base64/3.16
  perl-mouse/2.6.0-r0
  perl-net-dns-sec/1.26-r1
  perl-net-libidn/0.12-r17
  perl-net-libresolv/0.03-r2
  perl-net-pcap/0.21-r2
  perl-netaddr-ip/4.079-r14
  perl-padwalker/2.5-r5
  perl-perlio-utf8_strict/0.010
  perl-proc-processtable/0.637
  perl-proc-wait3/0.05
  perl-xml-parser/2.59
  perl-crypt-cast5/0.05-r14
  perl-object-pad/0.821-r0
  perl-package-anon/0.05-r16
  perl-package-stash-xs/0.30-r5
  perl-params-classify/0.015
  perl-params-util/1.102
  perl-params-validate/1.31
  perl-set-object/1.43-r0
)

mapfile -t XS_PACKAGES < <(printf '%s\n' "${XS_PACKAGES[@]}" | sort -u)

SUCCEEDED=()
FAILED=()
SKIPPED=()

for pkg_ref in "${XS_PACKAGES[@]}"; do
  pkg_name="${pkg_ref%%/*}"
  pkg_ver="${pkg_ref#*/}"
  upstream_ver=$(echo "$pkg_ver" | sed 's/-r[0-9]*$//')

  if [[ -n "$ONLY_PKG" && "$pkg_name" != "$ONLY_PKG" ]]; then
    continue
  fi

  echo ""
  echo "=========================================="
  echo "📦 $pkg_ref"
  echo "=========================================="

  recipe_dir="$REPO_DIR/archives/p/$pkg_name/$pkg_ver"
  if [[ ! -d "$recipe_dir" ]]; then
    recipe_dir="$REPO_DIR/archives/p/$pkg_name/$upstream_ver"
  fi

  if [[ ! -d "$recipe_dir" ]]; then
    echo "⚠️  Recipe 未找到（可能在 PR 分支中）"
    SKIPPED+=("$pkg_ref (recipe not in main)")
    continue
  fi

  conanfile="$recipe_dir/conanfile.py"
  if [[ ! -f "$conanfile" ]]; then
    echo "⚠️  conanfile.py 不存在（可能在 PR 分支中）"
    SKIPPED+=("$pkg_ref (no conanfile.py)")
    continue
  fi

  echo "Recipe: $recipe_dir"
  echo "命令: conan create $recipe_dir --name=$pkg_name --version=$pkg_ver @${CONAN_USER}/${CONAN_CHANNEL}"

  if $DRY_RUN; then
    echo "[DRY-RUN] 跳过实际编译"
    continue
  fi

  if conan create "$recipe_dir" --name="$pkg_name" --version="$pkg_ver" \
       --user="${CONAN_USER}" --channel="${CONAN_CHANNEL}" 2>&1 | tee /dev/stderr; then
    SUCCEEDED+=("$pkg_ref")
    echo "✅ 成功: $pkg_ref"
  else
    FAILED+=("$pkg_ref")
    echo "❌ 失败: $pkg_ref"
  fi
done

echo ""
echo "==================== 汇总报告 ===================="
echo "Perl 版本: $PERL_VER"
echo "总计: ${#XS_PACKAGES[@]} 个 XS 模块"
echo ""
echo "✅ 成功: ${#SUCCEEDED[@]} 个"
for p in "${SUCCEEDED[@]}"; do echo "   $p"; done
echo ""
echo "❌ 失败: ${#FAILED[@]} 个"
for p in "${FAILED[@]}"; do echo "   $p"; done
echo ""
echo "⚠️ 跳过: ${#SKIPPED[@]} 个"
for p in "${SKIPPED[@]}"; do echo "   $p"; done

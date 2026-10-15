#!/bin/sh
# krb5-server 服务端工具真实调用测试：
# 用 kdb5_util 创建临时 Kerberos 数据库并列出 principal，
# 验证 kdc 服务端工具链（kdb5_util -> libkdb5/libkadm5srv/openssl）真实可用。
# POSIX 兼容：不用 bash 专有的 set -o pipefail（dash/busybox sh 会失败或静默失效），
# 用 set -eu；grep 失败时借助临时文件判断而非管道退出码。
set -eu

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# KDB 插件目录：默认从 kdb5_util 位置推导（conanrun PATH 含 package/bin），
# 或由调用方通过 KRB5_DB_MODULE_DIR 显式指定。
KDB5_BIN=$(command -v kdb5_util)
DB_MODULE_DIR="${KRB5_DB_MODULE_DIR:-$(dirname "$KDB5_BIN")/../lib/krb5/plugins/kdb}"

# 最小 krb5.conf（无系统 /etc/krb5.conf），显式指定 db 插件目录
cat > "$WORKDIR/krb5.conf" <<EOF
[libdefaults]
    default_realm = TEST.REALM
[dbmodules]
    db_module_dir = $DB_MODULE_DIR
EOF
export KRB5_CONFIG="$WORKDIR/krb5.conf"

# 真实调用：创建 Kerberos 数据库（K/M、kadmin/admin 等 principal）
kdb5_util -r TEST.REALM -d "$WORKDIR/test.kdb" \
    create -s -sf "$WORKDIR/.k5.TEST.REALM" -P test123

test -s "$WORKDIR/test.kdb"
test -s "$WORKDIR/.k5.TEST.REALM"

# 真实调用：列出主密钥（验证数据库可读，应包含 K/M@TEST.REALM）
# 输出写临时文件再 grep（避免管道退出码语义差异，POSIX 可移植）
kdb5_util -r TEST.REALM -d "$WORKDIR/test.kdb" \
    -sf "$WORKDIR/.k5.TEST.REALM" list_mkeys \
    > "$WORKDIR/mkeys.out"
grep -q 'K/M@TEST.REALM' "$WORKDIR/mkeys.out"

echo "krb5-server kdb5_util create/list OK"

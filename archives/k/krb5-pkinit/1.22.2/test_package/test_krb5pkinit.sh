#!/bin/sh
# krb5-pkinit 服务端工具链真实调用测试：
# 用 kdb5_util 创建临时 Kerberos 数据库并列出主密钥，
# 验证 kdc 服务端工具链（kdb5_util -> libkdb5/libkadm5srv/LibreSSL）真实可用，
# 且 PKINIT 插件与 KDB 插件目录共存。
set -euo pipefail

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# KDB 插件目录：默认从 kdb5_util 位置推导（conanrun PATH 含 package/bin）
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

# 真实调用：列出主密钥（应包含 K/M@TEST.REALM）
kdb5_util -r TEST.REALM -d "$WORKDIR/test.kdb" \
    -sf "$WORKDIR/.k5.TEST.REALM" list_mkeys \
    | grep -q 'K/M@TEST.REALM'

# PKINIT 客户端插件必须存在于安装产物中
PKINIT_PLUGIN=$(dirname "$KDB5_BIN")/../lib/krb5/plugins/preauth/pkinit.so
test -s "$PKINIT_PLUGIN"

echo "krb5-pkinit kdb5_util create/list + pkinit.so OK"

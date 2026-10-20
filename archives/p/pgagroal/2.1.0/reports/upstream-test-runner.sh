#!/bin/sh
# pgagroal 2.1.0 上游 MCTF 套件在 HarmonyOS PC 上的执行脚本（本报告的实际运行脚本）
# 用法:  sh upstream-test-runner.sh run      # 起 PG + 连接池并一次跑完 96 个用例
#        sh upstream-test-runner.sh build    # 按配方参数重建源码树与 pgagroal_test
#
# 前置：本机已有 conan 制品（openssl/zstd/zlib/bzip2/lz4、postgresql 16.x），
#       以及上游 2.1.0 的源码树（含 test/；release 资产不含该目录，需 git checkout tag）。
set -e

SRC=${SRC:-/storage/Users/currentUser/tmp/xtract/tag/pgagroal-2.1.0}
WORK=${WORK:-/storage/Users/currentUser/tmp/pgagroal-build}
PATCHES=${PATCHES:-/storage/Users/currentUser/tmp/pgagroal-work/pgagroal/patches}
TMPDIFF=${TMPDIFF:-$(dirname "$0")/upstream-test-aes-tmpdir.diff}
GEN=${GEN:?请设置 conan 生成的 conan_toolchain.cmake 所在目录}
CC=${CC:-clang}
CMAKE=${CMAKE:-cmake}
GIT=${GIT:-git}
C=${C:-/storage/Users/currentUser/.conan2/p}
PGBIN=${PGBIN:?请设置 PostgreSQL bin 目录}
BASE=${BASE:-/storage/Users/currentUser/tmp/pgtest}
SANDBOX=/data/storage/el2/base/cache
SOCK=$SANDBOX/pgtest-run
DBPORT=15432
POOLPORT=6432
TPASS=yourpassword
UTF8USER=utf8user
UTF8DB=utf8db
PGTS=$WORK/pgagroal-testsuite

case "${1:-run}" in
build)
    rm -rf "$WORK"; mkdir -p "$WORK"; cp -r "$SRC"/. "$WORK"/
    for p in "$PATCHES"/*.patch; do (cd "$WORK" && "$GIT" apply -p1 "$p"); done
    # 仅本机跑通用例所需：/tmp 在 HarmonyOS PC 上是只读 erofs，见 upstream-test-report.md
    (cd "$WORK" && "$GIT" apply -p1 "$TMPDIFF")
    CFLAGS="-DHAVE_LINUX=1" "$CMAKE" -S "$WORK" -B "$WORK/build" -G "Unix Makefiles" \
        -DCMAKE_TOOLCHAIN_FILE="$GEN/conan_toolchain.cmake" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$WORK/install" \
        -DCMAKE_C_COMPILER="$CC" -DDOCS=OFF -DPGAGROAL_ALLOW_STATIC_DEPS=ON \
        -DOPENSSL_INCLUDE_DIR="$C/opens8df551124b5bd/p/include" \
        -DOPENSSL_INCLUDE_DIRS="$C/opens8df551124b5bd/p/include" \
        -DOPENSSL_SSL_LIBRARY="$C/opens8df551124b5bd/p/lib/libssl.a" \
        -DOPENSSL_CRYPTO_LIBRARY="$C/opens8df551124b5bd/p/lib/libcrypto.a" \
        -DZLIB_INCLUDE_DIR="$C/zlib8c00356330b7a/p/include" \
        -DZLIB_LIBRARY="$C/zlib8c00356330b7a/p/lib/libz.a" \
        -DBZIP2_INCLUDE_DIR="$C/bzip2577f2fece997b/p/include" \
        -DBZIP2_LIBRARY="$C/bzip2577f2fece997b/p/lib/libbz2.a" \
        -DZSTD_INCLUDE_DIR="$C/zstdba7ec16b111f0/p/include" \
        -DZSTD_LIBRARY="$C/zstdba7ec16b111f0/p/lib/libzstd.so" \
        -DLZ4_INCLUDE_DIR="$C/lz4ae086f15e5be7/p/include" \
        -DLZ4_LIBRARY="$C/lz4ae086f15e5be7/p/lib/liblz4.a"
    "$CMAKE" --build "$WORK/build" -- -j1
    ls -l "$WORK/build/src/pgagroal" "$WORK/build/test/pgagroal_test"
    ;;
run)
    export TMPDIR=$SANDBOX            # 1) 上游 aes 用例的临时目录（/tmp 只读）
    export HOME=$SANDBOX/pghome       # 2) ~/.pgagroal 需要可 chmod 700/600 的家目录
    rm -rf "$HOME" "$BASE" "$SOCK"
    mkdir -p "$HOME" "$BASE/log" "$SOCK" "$PGTS/conf" "$PGTS/resource" "$WORK/log"
    cp -r "$WORK/test/resource/." "$PGTS/resource/"
    export LD_LIBRARY_PATH="$WORK/build/src:$C/zstdba7ec16b111f0/p/lib:$C/opens8df551124b5bd/p/lib"
    export PATH="$PGBIN:$WORK/build/src:$PATH"
    export PGPASSWORD="$TPASS"
    export PGAGROAL_TEST_BASE_DIR="$PGTS"

    "$PGBIN/initdb" -D "$BASE/pgdata" -U myuser --auth=trust --encoding=UTF8 --locale=C >"$BASE/log/initdb.log" 2>&1
    "$PGBIN/pg_ctl" -D "$BASE/pgdata" -l "$BASE/log/pg.log" \
        -o "-p $DBPORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=$SOCK" -w start
    "$PGBIN/psql" -h 127.0.0.1 -p $DBPORT -U myuser -d postgres -q \
        -c "CREATE ROLE $UTF8USER LOGIN SUPERUSER PASSWORD '$TPASS'" \
        -c "CREATE ROLE postgres LOGIN SUPERUSER PASSWORD '$TPASS'"
    "$PGBIN/createdb" -h 127.0.0.1 -p $DBPORT -U myuser mydb
    "$PGBIN/createdb" -h 127.0.0.1 -p $DBPORT -U myuser -O $UTF8USER "$UTF8DB"
    "$PGBIN/pgbench" -i -s 1 -h 127.0.0.1 -p $DBPORT -U myuser mydb >"$BASE/log/pgbench-init.log" 2>&1

    CONF=$PGTS/conf
    cat >"$CONF/pgagroal.conf" <<EOF
[pgagroal]
host = localhost
port = $POOLPORT
log_type = file
log_level = debug5
log_path = $BASE/log/pgagroal.log
max_connections = 8
idle_timeout = 600
validation = off
pipeline = performance
unix_socket_dir = $SOCK
pidfile = $BASE/pgagroal.$POOLPORT.pid

[primary]
host = 127.0.0.1
port = $DBPORT
EOF
    printf 'host    all all all trust\n' >"$CONF/pgagroal_hba.conf"
    printf 'mydb=pgalias1,pgalias2 myuser 6 6 1\n%s %s 2 2 1\n' "$UTF8DB" "$UTF8USER" >"$CONF/pgagroal_databases.conf"
    printf '# frontend users (empty on purpose)\n' >"$CONF/pgagroal_frontend_users.conf"
    : >"$CONF/pgagroal_users.conf"
    "$WORK/build/src/pgagroal-admin" master-key -P "$TPASS" >/dev/null 2>&1
    chmod 700 "$HOME/.pgagroal"; chmod 600 "$HOME/.pgagroal/master.key"
    for u in myuser "$UTF8USER"; do
        "$WORK/build/src/pgagroal-admin" -f "$CONF/pgagroal_users.conf" -U "$u" -P "$TPASS" user add >/dev/null 2>&1 || true
    done
    "$WORK/build/src/pgagroal" -c "$CONF/pgagroal.conf" -a "$CONF/pgagroal_hba.conf" \
        -u "$CONF/pgagroal_users.conf" -l "$CONF/pgagroal_databases.conf" \
        -F "$CONF/pgagroal_frontend_users.conf" -d
    for i in 1 2 3 4 5 6 7 8 9 10; do
        "$WORK/build/src/pgagroal-cli" -c "$CONF/pgagroal.conf" status details >/dev/null 2>&1 && break
        sleep 2
    done

    set +e
    ( cd "$WORK/build/test" && ./pgagroal_test "$WORK" myuser mydb )
    RC=$?
    set -e
    "$WORK/build/src/pgagroal-cli" -c "$CONF/pgagroal.conf" shutdown >/dev/null 2>&1 || true
    "$PGBIN/pg_ctl" -D "$BASE/pgdata" -m immediate stop >/dev/null 2>&1 || true
    exit $RC
    ;;
*)
    echo "usage: $0 [build|run]" >&2
    exit 2
    ;;
esac

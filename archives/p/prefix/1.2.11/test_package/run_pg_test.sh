#!/bin/bash
# test_package/run_pg_test.sh — prefix 1.2.11 消费者 + 上游回归测试。
#
# 在一个真实运行于 OHOS PC 的 PostgreSQL 18.3 实例中装载「本配方安装后的包」：
#   1. 把 postgresql 安装（bin/lib/share）复制到隔离工作目录，保持 conan 缓存干净可重复；
#   2. initdb + 启动服务（仅 TCP：OHOS 构建的 PostgreSQL 没有 unix socket 支持）；
#   3. 把包内的 prefix.so + prefix.control + prefix--*.sql 安装进该隔离实例；
#   4. 用 pg_regress 重放上游回归套件（sql/ + expected/，归档内与上游逐字节一致）；
#   5. 执行鸿蒙特有断言，其中 CONSUMER-1 是完整的消费者端到端业务用例（规则 12）。
#
# 用法: run_pg_test.sh <pg_bindir> <pkg_libdir> <pkg_sharedir> <tests_dir>
#
# 有意不使用 `set -e`：所有失败先收集再统一汇报，最后的非零退出码才是真正的闸门。
set -uo pipefail

PG_BINDIR="${1:?pg_bindir required}"
PKG_LIBDIR="${2:?pkg_libdir required}"
PKG_SHAREDIR="${3:?pkg_sharedir required}"
TESTS_DIR="${4:?tests_dir required}"

MODULE="$PKG_LIBDIR/prefix.so"
CONTROL="$PKG_SHAREDIR/extension/prefix.control"
CSV="$TESTS_DIR/prefixes.fr.csv"

# 上游回归用例，顺序与上游 Makefile 一致
# （Makefile:8 `REGRESS = create_extension prefix falcon $(EXPLAINSQL) queries`）。
# explain.sql 会查询 prefix.sql 建立的 ranges/numbers 与 falcon.sql 建立的 tst，
# 因此该顺序不可调换。
REGRESS="create_extension prefix falcon explain queries"

[ -f "$MODULE" ] || { echo "FAIL: prefix.so not found in package libdir: $MODULE"; exit 1; }
[ -f "$CONTROL" ] || { echo "FAIL: prefix.control not found in package sharedir"; exit 1; }
# 上游 Makefile:4 DATA = prefix--1.2.0.sql prefix--unpackaged--1.2.0.sql prefix--1.1--1.2.0.sql
for f in prefix--1.2.0.sql prefix--unpackaged--1.2.0.sql prefix--1.1--1.2.0.sql; do
    [ -f "$PKG_SHAREDIR/extension/$f" ] || { echo "FAIL: $f not found in package sharedir"; exit 1; }
done
[ -d "$TESTS_DIR/sql" ] || { echo "FAIL: upstream test tree not found: $TESTS_DIR/sql"; exit 1; }
[ -f "$CSV" ] || { echo "FAIL: upstream fixture prefixes.fr.csv not found: $CSV"; exit 1; }

# OHOS /tmp 是只读 erofs 挂载（E002）：用可写临时目录。
TMPBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPBASE" || { echo "FAIL: cannot create $TMPBASE"; exit 1; }
WORKDIR="$(mktemp -d "$TMPBASE/prefix-test-XXXXXX")" || { echo "FAIL: mktemp"; exit 1; }
PGROOT="$WORKDIR/pginstall"
DATADIR="$WORKDIR/data"
LOGFILE="$WORKDIR/server.log"
TESTDIR="$WORKDIR/testdir"

cleanup() {
    if [ -x "$PGROOT/bin/pg_ctl" ]; then
        "$PGROOT/bin/pg_ctl" -D "$DATADIR" stop -m immediate >/dev/null 2>&1 || true
    fi
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

fail() { echo "FAIL: $*"; exit 1; }

# ── 1. 隔离的 PostgreSQL 安装 ───────────────────────────────────────────────
PG_SRC_ROOT="$(dirname "$PG_BINDIR")"
mkdir -p "$PGROOT"
cp -r "$PG_SRC_ROOT/bin" "$PG_SRC_ROOT/lib" "$PG_SRC_ROOT/share" "$PGROOT/" \
    || fail "cannot copy postgresql installation"
INITDB="$PGROOT/bin/initdb"; PGCTL="$PGROOT/bin/pg_ctl"
PSQL="$PGROOT/bin/psql";     PG_CONFIG="$PGROOT/bin/pg_config"
for bin in "$INITDB" "$PGCTL" "$PSQL" "$PG_CONFIG"; do
    [ -x "$bin" ] || fail "required PostgreSQL binary missing after copy: $bin"
done
# PG 18 是以 --enable-rpath + '/' 前缀构建的：可执行文件按 $ORIGIN/../lib 找 libpq.so.5，
# 隔离安装后仍需显式给出 <pgroot>/lib。
export LD_LIBRARY_PATH="$PGROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

"$INITDB" -D "$DATADIR" -U postgres --no-locale -E UTF8 >"$WORKDIR/initdb.log" 2>&1 \
    || { echo "FAIL: initdb failed"; tail -20 "$WORKDIR/initdb.log"; exit 1; }

# ── 2. 把「本配方安装后的包」装进隔离实例 ─────────────────────────────────
PKGLIBDIR="$("$PG_CONFIG" --pkglibdir)" || fail "pg_config --pkglibdir"
SHAREDIR="$("$PG_CONFIG" --sharedir)"   || fail "pg_config --sharedir"
case "$PKGLIBDIR" in "$PGROOT"*) ;; *) fail "pg_config not relocatable: $PKGLIBDIR";; esac
cp "$MODULE" "$PKGLIBDIR/prefix.so" || fail "cannot install prefix.so"
mkdir -p "$SHAREDIR/extension"
cp "$CONTROL" "$SHAREDIR/extension/" || fail "cannot install prefix.control"
cp "$PKG_SHAREDIR/extension/"prefix--*.sql "$SHAREDIR/extension/" || fail "cannot install SQL scripts"

# ── 3. 启动服务（OHOS 两项必须的运行时适配）─────────────────────────────────
# a) 仅 TCP：OHOS 构建的 PostgreSQL 带 -DHAVE_NO_UNIX_SOCKETS，没有 unix socket。
# b) file_extend_method=write_zeros：PG 18 默认用 posix_fallocate 扩展数据文件，
#    而 OHOS 的用户文件系统拒绝 posix_fallocate（返回 EACCES），导致 COPY / 批量
#    插入在需要扩展文件时报 "could not extend file ... with FileFallocate():
#    Permission denied"。改用零填充写入路径即可正常扩展。
PORT=$(( (RANDOM % 20000) + 40000 ))
"$PGCTL" -D "$DATADIR" -l "$LOGFILE" \
    -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories='' -c file_extend_method=write_zeros" \
    -w -t 60 start || { echo "FAIL: server did not start (port $PORT)"; tail -20 "$LOGFILE"; exit 1; }

export PGHOST=127.0.0.1 PGPORT="$PORT" PGUSER=postgres
q() { "$PSQL" -X -h 127.0.0.1 -p "$PORT" -U postgres -d "${2:-postgres}" -t -A -c "$1"; }

# ── 4. 重放上游回归套件 ────────────────────────────────────────────────────
mkdir -p "$TESTDIR/sql" "$TESTDIR/expected" "$TESTDIR/tmp"
cp "$TESTS_DIR/sql/"*.sql "$TESTDIR/sql/"            || fail "cannot stage upstream sql/"
cp "$TESTS_DIR/expected/"*.out "$TESTDIR/expected/"  || fail "cannot stage upstream expected/"
# prefix.sql 的 `\copy prefixes from 'prefixes.fr.csv'` 是 psql 客户端相对路径，
# 其解析基准是 pg_regress 的 cwd；PostgreSQL 自己的回归套件同样避免依赖 cwd
# （上游 src/test/regress/sql/copy.sql 用 \getenv 取绝对路径）。这里只把该路径
# 字面量改写为绝对路径——sql 与 expected 同时替换，psql 回显行才能逐行匹配；
# SQL 逻辑未改动，归档内保存的测试文件与上游逐字节一致。
STAGE_CSV="$TESTDIR/prefixes.fr.csv"
cp "$CSV" "$STAGE_CSV" || fail "cannot stage prefixes.fr.csv"
sed -i "s#'prefixes.fr.csv'#'$STAGE_CSV'#g" "$TESTDIR/sql/prefix.sql" "$TESTDIR/expected/prefix.out" \
    || fail "cannot pin prefixes.fr.csv path"
grep -q "$STAGE_CSV" "$TESTDIR/sql/prefix.sql" || fail "csv path rewrite did not apply"

PG_REGRESS="$PGROOT/lib/postgresql/pgxs/src/test/regress/pg_regress"
[ -x "$PG_REGRESS" ] || fail "pg_regress not found: $PG_REGRESS"

echo "── 上游回归套件（pg_regress）──"
( cd "$TESTDIR" && "$PG_REGRESS" --inputdir="$TESTDIR" --outputdir="$TESTDIR" \
    --bindir="$PGROOT/bin" --dbname=contrib_regression $REGRESS ) \
    >"$WORKDIR/pg_regress.log" 2>&1
REGRESS_RC=$?
cat "$WORKDIR/pg_regress.log"

UP_TOTAL=$(grep -cE '^(ok|not ok) ' "$WORKDIR/pg_regress.log")
UP_PASS=$(grep -cE '^ok ' "$WORKDIR/pg_regress.log")
UP_FAIL=$((UP_TOTAL - UP_PASS))
if [ "$REGRESS_RC" -ne 0 ]; then
    echo "FAIL: pg_regress exited $REGRESS_RC"
    [ -f "$TESTDIR/regression.diffs" ] && head -80 "$TESTDIR/regression.diffs"
fi

# ── 5. 鸿蒙特有断言 ────────────────────────────────────────────────────────
echo "── 鸿蒙特有断言 ──"
OHOS_PASS=0
OHOS_TOTAL=0
ohos() {  # ohos <描述> <0|1 结果>
    OHOS_TOTAL=$((OHOS_TOTAL + 1))
    if [ "$2" -eq 0 ]; then OHOS_PASS=$((OHOS_PASS + 1)); echo "PASS: $1"; else echo "FAIL: $1"; fi
}

q "DROP DATABASE IF EXISTS prefix_ohos;" >/dev/null 2>&1
q "CREATE DATABASE prefix_ohos;" >/dev/null 2>&1

# OH-1: 包内模块在 OHOS 原生 postgres 进程里 dlopen 成功
q "CREATE EXTENSION prefix;" prefix_ohos >"$WORKDIR/oh1.log" 2>&1
rc=$?
ext_n=$(q "SELECT count(*) FROM pg_extension WHERE extname='prefix';" prefix_ohos 2>/dev/null)
ext_v=$(q "SELECT default_version FROM pg_available_extensions WHERE name='prefix';" prefix_ohos 2>/dev/null)
[ "$rc" -eq 0 ] && [ "$ext_n" = "1" ] && [ "$ext_v" = "1.2.0" ]
ohos "OH-1 CREATE EXTENSION prefix 在 OHOS postgres 服务进程中装载模块（pg_extension 行数=$ext_n，可用版本=$ext_v）" $?

# OH-2: 交付产物的平台 ABI —— AArch64，且唯一 DT_NEEDED 为 libc，无构建机 rpath
READELF="$(command -v readelf || command -v llvm-readelf || true)"
if [ -n "$READELF" ]; then
    machine="$("$READELF" -h "$MODULE" 2>/dev/null | awk -F: '/Machine/{gsub(/ /,"",$2);print $2}')"
    needed="$("$READELF" -d "$MODULE" 2>/dev/null | awk '/NEEDED/{gsub(/[][]/,"",$NF);print $NF}' | sort -u | tr '\n' ' ')"
    runpath="$("$READELF" -d "$MODULE" 2>/dev/null | awk '/RUNPATH|RPATH/{print $0}')"
    [ "$machine" = "AArch64" ] && [ "$needed" = "libc.so " ] && [ -z "$runpath" ]
    ohos "OH-2 产物 ABI：machine=$machine needed=[$needed] rpath=[${runpath:-none}]" $?
else
    ohos "OH-2 产物 ABI 检查跳过（本机无 readelf/llvm-readelf）" 1
fi

# OH-3 = CONSUMER-1：完整的消费者端到端业务用例（规则 12）。
#   用户场景：法国电话前缀路由 —— 运营商把号码段路由到归属运营商。
#   真实输入：prefixes.fr.csv（法国电信监管机构公布的官方号码前缀分配表，11966 行）。
#   被测产物：本配方安装后的 prefix.so + prefix.control + prefix--*.sql（装入隔离实例）。
#   完整流程：建前缀表 → 建 prefix_range 表与 GiST 索引 → 建用户号码表 →
#            用 @> 运算符 + GiST 索引做最长前缀匹配解析出号码归属运营商。
#   预期业务输出：与上游黄金值一致的归属结果；且「走索引」与「走顺序扫描」两条
#                互相独立的执行路径必须给出完全一致的结果集。
echo "── CONSUMER-1：FR 号码前缀路由消费者端到端用例 ──"
CONSUMER_SQL="$WORKDIR/consumer1.sql"
cat >"$CONSUMER_SQL" <<'SQL'
CREATE TABLE prefixes (
       prefix    text primary key,
       name      text not null,
       shortname text,
       state     char default 'S',
       check( state in ('S', 'R') )
);
COPY prefixes FROM '@CSV@' WITH (FORMAT csv, DELIMITER ';', QUOTE '"');

-- 官方号码前缀分配表 → prefix_range 集合 + GiST 倒排索引（路由检索结构）
CREATE TABLE ranges AS SELECT prefix::prefix_range, name, shortname, state FROM prefixes;
CREATE INDEX idx_prefix ON ranges USING gist(prefix gist_prefix_range_ops);
ANALYZE ranges;

-- 待路由的用户号码（与上游回归用例同构的确定性构造，保证可复现）
CREATE TABLE numbers(number text primary key);
INSERT INTO numbers
  SELECT '01' || substr(regexp_replace(md5(i::text), '[a-f]', '', 'g'), 1, 8)
   FROM generate_series(1, 5000) i;
ANALYZE numbers;

-- 路径 1：强制走 GiST 索引，做最长前缀匹配 → 号码归属运营商
SET enable_seqscan TO off;
CREATE TEMP TABLE routed_index AS
SELECT n.number, m.name, m.shortname, m.prefix::text AS matched_prefix
  FROM numbers n
  LEFT JOIN LATERAL (
       SELECT r.name, r.shortname, r.prefix FROM ranges r
        WHERE r.prefix @> n.number
        ORDER BY length(r.prefix) DESC LIMIT 1) m ON true;

-- 路径 1 的计划证据：必须命中 GiST 索引
\o @PLANDIR@/plan_path1.txt
EXPLAIN (COSTS OFF) SELECT r.name, r.shortname, r.prefix FROM ranges r
   WHERE r.prefix @> '0146640123' ORDER BY length(r.prefix) DESC LIMIT 1;
\o

-- 路径 2（独立交叉校验）：**真正**强制顺序扫描 —— 关掉全部索引扫描方式。
-- 注意：只设 enable_seqscan=on 仅恢复默认，LATERAL 子查询仍可能走 idx_prefix，
-- 那样两条路径退化为同一计划、diff=0 平凡成立（PR 检视意见 P2 指出的问题）。
SET enable_seqscan TO on;
SET enable_indexscan TO off;
SET enable_bitmapscan TO off;
SET enable_indexonlyscan TO off;
CREATE TEMP TABLE routed_seq AS
SELECT n.number, m.name, m.shortname, m.prefix::text AS matched_prefix
  FROM numbers n
  LEFT JOIN LATERAL (
       SELECT r.name, r.shortname, r.prefix FROM ranges r
        WHERE r.prefix @> n.number
        ORDER BY length(r.prefix) DESC LIMIT 1) m ON true;

-- 路径 2 的计划证据：必须是 Seq Scan 且不得出现 idx_prefix
\o @PLANDIR@/plan_path2.txt
EXPLAIN (COSTS OFF) SELECT r.name, r.shortname, r.prefix FROM ranges r
   WHERE r.prefix @> '0146640123' ORDER BY length(r.prefix) DESC LIMIT 1;
\o
RESET enable_indexscan;
RESET enable_bitmapscan;
RESET enable_indexonlyscan;

-- 业务结果汇总（单行，供外层脚本逐字段核对）
SELECT 'CONSUMER1'
    || '|prefixes=' || (SELECT count(*) FROM prefixes)
    || '|ranges='   || (SELECT count(*) FROM ranges)
    || '|numbers='  || (SELECT count(*) FROM numbers)
    || '|routed='   || (SELECT count(*) FROM routed_index WHERE matched_prefix IS NOT NULL)
    || '|matched='  || (SELECT count(*) FROM numbers n JOIN ranges r ON r.prefix @> n.number)
    || '|diff_ix_seq=' || ((SELECT count(*) FROM (SELECT * FROM routed_index EXCEPT SELECT * FROM routed_seq) d)
                         + (SELECT count(*) FROM (SELECT * FROM routed_seq EXCEPT SELECT * FROM routed_index) d))
    || '|owner1=' || (SELECT name || '/' || prefix::text FROM ranges r
                       WHERE r.prefix @> '0146640123' ORDER BY length(r.prefix) DESC LIMIT 1)
    || '|owner2=' || (SELECT name || '/' || prefix::text FROM ranges r
                       WHERE r.prefix @> '0100091234' ORDER BY length(r.prefix) DESC LIMIT 1)
    AS consumer1_result;
SQL
sed -i "s#@CSV@#$STAGE_CSV#" "$CONSUMER_SQL" || fail "cannot pin consumer csv path"
sed -i "s#@PLANDIR@#$WORKDIR#" "$CONSUMER_SQL" || fail "cannot pin plan output dir"
grep -q "$STAGE_CSV" "$CONSUMER_SQL" || fail "consumer csv path substitution did not apply"

CONSUMER_LOG="$WORKDIR/consumer1.log"
"$PSQL" -X -h 127.0.0.1 -p "$PORT" -U postgres -d prefix_ohos -q -v ON_ERROR_STOP=1 \
    -f "$CONSUMER_SQL" >"$CONSUMER_LOG" 2>&1
C1_RC=$?
cat "$CONSUMER_LOG"

CONSUMER1_EXPECT="CONSUMER1|prefixes=11966|ranges=11966|numbers=5000|routed=2019|matched=2019|diff_ix_seq=0|owner1=FRANCE TELECOM/0146|owner2=LONG PHONE/010009"
# psql 默认对齐格式会给结果行加前导空格并按列宽右侧补空格，这里按标记串截取并去尾空格。
consumer1_got="$(grep -m1 -o 'CONSUMER1|.*' "$CONSUMER_LOG" | sed 's/[[:space:]]*$//' || true)"
PLAN1="$WORKDIR/plan_path1.txt"
PLAN2="$WORKDIR/plan_path2.txt"
c1_ok=1
[ "$C1_RC" -eq 0 ] || { c1_ok=0; echo "  原因：消费者流程退出码=$C1_RC"; }
[ "$consumer1_got" = "$CONSUMER1_EXPECT" ] || { c1_ok=0; echo "  原因：业务结果行不一致"; }
# 两侧计划证据都必须存在：路径 1 走 idx_prefix；路径 2 必须是 Seq Scan 且不含索引。
# （只断言其中一侧会让 diff_ix_seq=0 平凡成立——见 PR 检视意见 P2）
for f in "$PLAN1" "$PLAN2"; do
    [ -s "$f" ] || { c1_ok=0; echo "  原因：缺少执行计划证据 $f"; }
done
grep -q "idx_prefix" "$PLAN1" 2>/dev/null || { c1_ok=0; echo "  原因：路径 1（关序扫）计划未使用 idx_prefix 索引"; }
grep -q "Seq Scan" "$PLAN2" 2>/dev/null || { c1_ok=0; echo "  原因：路径 2（关全部索引扫描）计划未见 Seq Scan"; }
grep -q "idx_prefix" "$PLAN2" 2>/dev/null && { c1_ok=0; echo "  原因：路径 2 仍使用了 idx_prefix，两条路径不独立"; }
echo "  路径1计划: $(tr '\n' ' ' <"$PLAN1" 2>/dev/null | sed 's/  */ /g')"
echo "  路径2计划: $(tr '\n' ' ' <"$PLAN2" 2>/dev/null | sed 's/  */ /g')"
echo "  实际业务输出: ${consumer1_got:-<无>}"
echo "  期望业务输出: $CONSUMER1_EXPECT"
ohos "CONSUMER-1 号码路由端到端：装载 11966 条官方前缀；索引路径与真·顺序扫描路径（关 enable_indexscan/bitmapscan/indexonlyscan）结果零差异；0146640123→FRANCE TELECOM/0146，0100091234→LONG PHONE/010009" $((1 - c1_ok))

# OH-4: 被测对象来源核对 —— 包内产物与隔离实例中实际加载的模块，都必须等于
# MANIFEST.yml 锚定的 sha256。不能拿包文件与其自身的副本比较（按构造必然相等、
# 断言不可能失败——见 PR 检视意见 P3）。
EXPECTED_SHA="$(grep -m1 '^artifact_sha256:' "$TESTS_DIR/MANIFEST.yml" 2>/dev/null | sed 's/^[^:]*:[[:space:]]*//' | tr -d '"' | tr -d ' ')"
inst_sum=$(sha256sum "$PKGLIBDIR/prefix.so" 2>/dev/null | awk '{print $1}')
pkg_sum=$(sha256sum "$MODULE" 2>/dev/null | awk '{print $1}')
oh4_ok=1
[ -n "$EXPECTED_SHA" ] || { oh4_ok=0; echo "  原因：MANIFEST.yml 未提供 artifact_sha256 锚点"; }
[ -n "$inst_sum" ] && [ "$inst_sum" = "$EXPECTED_SHA" ] || { oh4_ok=0; echo "  原因：隔离实例内模块 sha256=$inst_sum 与锚点不符"; }
[ "$pkg_sum" = "$EXPECTED_SHA" ] || { oh4_ok=0; echo "  原因：包内产物 sha256=$pkg_sum 与锚点不符"; }
ohos "OH-4 被测模块来源：包内产物与隔离实例 pkglibdir 内的 prefix.so 均等于 MANIFEST 锚定 sha256（$EXPECTED_SHA）" $((1 - oh4_ok))

echo
echo "RESULT: 上游回归 $UP_PASS/$UP_TOTAL 通过（失败=$UP_FAIL）；鸿蒙断言 $OHOS_PASS/$OHOS_TOTAL 通过"
[ "$REGRESS_RC" -eq 0 ] && [ "$UP_TOTAL" -eq 5 ] && [ "$UP_PASS" -eq 5 ] && [ "$OHOS_PASS" -eq "$OHOS_TOTAL" ] || {
    echo "FAILED"; exit 1;
}
echo "ALL TESTS PASSED"
exit 0

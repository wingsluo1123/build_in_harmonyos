// Consumer test for the packaged tntdb library.
//
// Exercises real public APIs against a local sqlite file database
// (no servers needed): connect, DDL/DML, selectValue/selectRow/select,
// cursor iteration, transactions, plus offline Value/Decimal/SqlBuilder
// checks. Prints one CHECK line per case and a TNTEST_RESULT summary;
// the conanfile emits HMBS_TEST_PACKAGE_RESULT by parsing the CHECK
// lines (single deterministic source; TNTEST_RESULT is only evidence).
//
// Isolation: each of the 10 checks runs guarded so one throwing case
// cannot abort the remaining checks (single exception previously hid
// 7 checks and produced passed=0 with no per-name evidence). No test
// is skipped; failures still return nonzero.
#include <cstdio>
#include <cstdlib>
#include <string>

#include <unistd.h>

#include <tntdb/connect.h>
#include <tntdb/connection.h>
#include <tntdb/decimal.h>
#include <tntdb/result.h>
#include <tntdb/row.h>
#include <tntdb/sqlbuilder.h>
#include <tntdb/statement.h>
#include <tntdb/transaction.h>
#include <tntdb/value.h>

#define TNTEST_TOTAL 10

static int g_passed = 0;
static int g_total = 0;

#define CHECK(cond, name)                                   \
    do {                                                    \
        ++g_total;                                          \
        if (cond) {                                         \
            ++g_passed;                                     \
            std::printf("CHECK PASS: %s\n", name);          \
        } else {                                            \
            std::printf("CHECK FAIL: %s\n", name);          \
        }                                                   \
        std::fflush(stdout);                                \
    } while (0)

struct Ctx
{
    tntdb::Connection conn;
    bool connected;
    std::string diag;
    Ctx() : connected(false) {}
};

// Guarded runners: always return bool, never throw. Declared before use
// so every CHECK line is emitted exactly once per named case.
static bool guardedCtx(const char* name, bool (*fn)(Ctx&), Ctx& ctx)
{
    try
    {
        return fn(ctx);
    }
    catch (const std::exception& ex)
    {
        std::printf("DIAG %s exception: %s\n", name, ex.what());
        std::fflush(stdout);
        return false;
    }
    catch (...)
    {
        std::printf("DIAG %s unknown exception\n", name);
        std::fflush(stdout);
        return false;
    }
}

static bool guardedPlain(const char* name, bool (*fn)())
{
    try
    {
        return fn();
    }
    catch (const std::exception& ex)
    {
        std::printf("DIAG %s exception: %s\n", name, ex.what());
        std::fflush(stdout);
        return false;
    }
    catch (...)
    {
        std::printf("DIAG %s unknown exception\n", name);
        std::fflush(stdout);
        return false;
    }
}

static bool t_selectValueMax(Ctx& c)
{
    double maxScore = 0.0;
    bool notNull = c.conn.selectValue("select max(score) from kv").get(maxScore);
    return notNull && maxScore > 9.49 && maxScore < 9.51;
}

static bool t_selectRowFields(Ctx& c)
{
    tntdb::Row row = c.conn.selectRow(
        "select id, name, score from kv where name='grace'");
    std::string name;
    double score = 0.0;
    return row.size() == 3 && row[1].get(name) && name == "grace"
        && row[2].get(score) && score > 8.24 && score < 8.26;
}

static bool t_selectCursorCount(Ctx& c)
{
    tntdb::Result res = c.conn.select("select id from kv order by id");
    unsigned rows = 0;
    for (tntdb::Result::const_iterator it = res.begin(); it != res.end(); ++it)
        ++rows;
    return rows == 2;
}

static bool t_statementBind(Ctx& c)
{
    // Upstream base-test.cpp uses generic set("name", value); use the
    // same overload so the sqlite driver takes the proven path.
    tntdb::Statement st = c.conn.prepare(
        "select name from kv where score > :limit order by score desc");
    st.set("limit", 9.0);
    tntdb::Row top = st.selectRow();
    std::string topName;
    return top[0].get(topName) && topName == "ada";
}

static bool t_transactionRollback(Ctx& c)
{
    // Upstream testTransaction relies on Transaction destructor rollback
    // when commit() is not called; use the same pattern (no explicit
    // rollback() call, which is not part of the proven upstream path).
    {
        tntdb::Transaction ta(c.conn);
        c.conn.execute("insert into kv(name, score) values('tmp', 1.0)");
    }
    unsigned cnt = 0;
    return c.conn.selectValue("select count(*) from kv").get(cnt) && cnt == 2;
}

static bool t_valueConvert(Ctx& c)
{
    tntdb::Value v = c.conn.selectValue("select 42");
    int iv = 0;
    std::string sv;
    return v.get(iv) && iv == 42
        && c.conn.selectValue("select 'hi'").get(sv) && sv == "hi";
}

static bool t_valueNull()
{
    tntdb::Value n;
    return n.isNull();
}

static bool t_decimalScale()
{
    // Decimal stores mantissa+exponent with the point after `exponent`
    // digits (see Decimal::Parser::finish `_exponent += _eoff` and
    // toStringFix inserting '.' at exponent): "19.95" parses to
    // mantissa "1995", exponent 2. A previous round asserted -2 and
    // failed on every platform (CI build #83076: 9/10 consumer pass
    // with only decimal-scale FAIL). Check the round-trip string plus
    // the exact exponent so the case is self-validating.
    tntdb::Decimal d("19.95");
    return d.exponent() == 2 && d.toString() == "19.95";
}

static bool t_sqlbuilderSelect()
{
    std::string sql = tntdb::SqlBuilder("select id from %tab")
        .replace("tab", "kv").str();
    return sql == "select id from kv";
}

static bool t_connectionAlive(Ctx& c)
{
    return !!c.conn;
}

int main(int argc, char** argv)
{
    (void)argc; (void)argv;
    // Unbuffered stdout so every CHECK line lands even on abort.
    setvbuf(stdout, NULL, _IONBF, 0);

    const char* tmp = std::getenv("TMPDIR");
    // Per-process DB filename: CI workers share one TMPDIR across builds,
    // so a fixed filename lets concurrent runs delete/recreate each
    // other's file mid-run ("table kv already exists", missing tables,
    // SQLITE_BUSY). HMBS真机 uses an isolated TMPDIR and never collides.
    // PID suffix keeps parallel runs isolated; setup stays idempotent via
    // drop-if-exists. Only the temp path changes, no test is skipped.
    char dbbuf[1024];
    std::snprintf(dbbuf, sizeof(dbbuf), "%s/tntdb_consumer_%ld.db",
                  tmp ? tmp : ".", (long)::getpid());
    std::string db(dbbuf);
    std::printf("DIAG setup db=%s pid=%ld\n", db.c_str(), (long)::getpid());
    std::fflush(stdout);
    std::remove(db.c_str());

    Ctx ctx;
    try
    {
        ctx.conn = tntdb::connect("sqlite:" + db);
        ctx.connected = true;
        ctx.conn.execute("drop table if exists kv");
        ctx.conn.execute(
            "create table kv(id integer primary key, name text, score real)");
        ctx.conn.execute("insert into kv(name, score) values('ada', 9.5)");
        ctx.conn.execute("insert into kv(name, score) values('grace', 8.25)");
    }
    catch (const std::exception& ex)
    {
        std::printf("DIAG setup exception: %s\n", ex.what());
        std::fflush(stdout);
        ctx.diag = ex.what();
        ctx.connected = false;
    }

    if (ctx.connected)
    {
        CHECK(guardedCtx("selectValue-max", t_selectValueMax, ctx), "selectValue-max");
        CHECK(guardedCtx("selectRow-fields", t_selectRowFields, ctx), "selectRow-fields");
        CHECK(guardedCtx("select-cursor-count", t_selectCursorCount, ctx), "select-cursor-count");
        CHECK(guardedCtx("statement-bind", t_statementBind, ctx), "statement-bind");
        CHECK(guardedCtx("transaction-rollback", t_transactionRollback, ctx), "transaction-rollback");
        CHECK(guardedCtx("value-convert", t_valueConvert, ctx), "value-convert");
    }
    else
    {
        // Setup failed: emit one FAIL per DB-backed case with the setup
        // evidence so the gap detail names the real cause (no silent skip).
        const char* dbNames[6] = {"selectValue-max", "selectRow-fields",
            "select-cursor-count", "statement-bind",
            "transaction-rollback", "value-convert"};
        for (int i = 0; i < 6; ++i)
        {
            std::printf("DIAG %s skipped-by-setup-failure: %s\n",
                dbNames[i], ctx.diag.c_str());
            std::fflush(stdout);
            CHECK(false, dbNames[i]);
        }
    }
    // Offline checks always run, even when the DB setup failed.
    CHECK(guardedPlain("value-null", t_valueNull), "value-null");
    CHECK(guardedPlain("decimal-scale", t_decimalScale), "decimal-scale");
    CHECK(guardedPlain("sqlbuilder-select", t_sqlbuilderSelect), "sqlbuilder-select");
    if (ctx.connected)
        CHECK(guardedCtx("connection-alive", t_connectionAlive, ctx), "connection-alive");
    else
    {
        std::printf("DIAG connection-alive skipped-by-setup-failure: %s\n",
            ctx.diag.c_str());
        std::fflush(stdout);
        CHECK(false, "connection-alive");
    }

    std::printf("TNTEST_RESULT passed=%d total=%d expected=%d\n",
                g_passed, g_total, TNTEST_TOTAL);
    std::fflush(stdout);
    return (g_total == TNTEST_TOTAL && g_passed == TNTEST_TOTAL) ? 0 : 1;
}

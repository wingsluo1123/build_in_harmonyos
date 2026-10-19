// SPDX-FileCopyrightText: 2022 Jonah Brüchert <jbb@kaidan.im>
//
// SPDX-License-Identifier: LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL
//
// Consumer end-to-end check for futuresql/0.1.1 on HarmonyOS PC:
// links FutureSQL6::FutureSQL from the packaged library and drives the public
// API against a real in-memory SQLite database, so a stub or empty package
// cannot pass. Every case prints TEST PASS/FAIL and the process exits non-zero
// when any case has failed.

#include <QCoreApplication>
#include <QSqlDatabase>
#include <QString>

#include <cstdio>
#include <optional>
#include <tuple>
#include <vector>

#include <ThreadedDatabase>

struct Row {
    using ColumnTypes = std::tuple<int, QString>;

    int id = 0;
    QString data;
};

// Single-column row used to check observable database state.
struct CountRow {
    using ColumnTypes = std::tuple<int>;

    int count = 0;
};

static int failures = 0;

static void check(bool condition, const char *name)
{
    if (condition) {
        std::printf("TEST PASS: %s\n", name);
    } else {
        std::printf("TEST FAIL: %s\n", name);
        ++failures;
    }
    std::fflush(stdout);
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    DatabaseConfiguration config;
    config.setType(DatabaseType::SQLite);
    config.setDatabaseName(QStringLiteral(":memory:"));
    check(config.type() == QStringLiteral("QSQLITE"), "DatabaseType::SQLite maps to the QSQLITE driver");

    auto db = ThreadedDatabase::establishConnection(config);
    if (!db) {
        // establishConnection is documented to return a handle; a null value
        // means the package is broken, so report it without dereferencing.
        std::printf("TEST FAIL: ThreadedDatabase::establishConnection returned a null handle\n");
        std::printf("TEST SUMMARY: FAIL (1 failure(s))\n");
        return 1;
    }
    // execute() returns QFuture<void> and only logs SQL errors, so query the
    // real connection state through the public runOnThread() API instead.
    auto openFuture = db->runOnThread([](const QSqlDatabase &database) {
        return database.isOpen();
    });
    openFuture.waitForFinished();
    check(openFuture.result(), "packaged QSQLITE driver opens the database");

    auto createFuture = db->execute(QStringLiteral(
        "CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, data TEXT)"));
    createFuture.waitForFinished();
    auto tableFuture = db->getResults<CountRow>(QStringLiteral(
        "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'test'"));
    tableFuture.waitForFinished();
    const std::vector<CountRow> tables = tableFuture.result();
    check(tables.size() == 1 && tables.front().count == 1,
          "CREATE TABLE created the test table (verified via sqlite_master)");

    auto insertFuture = db->execute(QStringLiteral("INSERT INTO test (data) VALUES (?)"),
                                    QStringLiteral("harmonyos"));
    insertFuture.waitForFinished();
    auto countFuture = db->getResults<CountRow>(QStringLiteral("SELECT count(*) FROM test"));
    countFuture.waitForFinished();
    const std::vector<CountRow> inserted = countFuture.result();
    check(inserted.size() == 1 && inserted.front().count == 1,
          "INSERT with a bound QVariant stored one row (verified via count(*))");

    auto rowsFuture = db->getResults<Row>(QStringLiteral("SELECT id, data FROM test ORDER BY id ASC"));
    rowsFuture.waitForFinished();
    const std::vector<Row> rows = rowsFuture.result();
    check(rows.size() == 1, "getResults returns exactly one row");
    check(rows.size() == 1 && rows.front().id == 1, "getResults deserializes the integer column");
    check(rows.size() == 1 && rows.front().data == QStringLiteral("harmonyos"),
          "getResults deserializes the text column");

    auto singleFuture = db->getResult<Row>(QStringLiteral("SELECT id, data FROM test ORDER BY id ASC"));
    singleFuture.waitForFinished();
    const std::optional<Row> single = singleFuture.result();
    check(single.has_value() && single->data == QStringLiteral("harmonyos"),
          "getResult returns the first row as a std::optional");

    std::printf("TEST SUMMARY: %s (%d failure(s))\n", failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}

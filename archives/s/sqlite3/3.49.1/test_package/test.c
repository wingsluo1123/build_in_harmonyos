/* test_package/test.c — sqlite3 L1 test (R34: must call tested package's API)
 *
 * Opens an in-memory database, creates a table, inserts rows,
 * queries them back, and verifies the results.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sqlite3.h"

int main(void) {
    sqlite3 *db = NULL;
    char *err = NULL;
    int rc;

    /* 1. Open in-memory database */
    rc = sqlite3_open(":memory:", &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: sqlite3_open: %s\n", sqlite3_errmsg(db));
        return 1;
    }

    /* 2. Create table */
    rc = sqlite3_exec(db, "CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT)", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: CREATE TABLE: %s\n", err);
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    /* 3. Insert data */
    rc = sqlite3_exec(db, "INSERT INTO t VALUES(1, 'hello')", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: INSERT: %s\n", err);
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }
    rc = sqlite3_exec(db, "INSERT INTO t VALUES(2, 'world')", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: INSERT: %s\n", err);
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    /* 4. Query and verify via sqlite3_prepare/step */
    sqlite3_stmt *stmt = NULL;
    rc = sqlite3_prepare_v2(db, "SELECT id, name FROM t ORDER BY id", -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: prepare: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }

    int row_count = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        int id = sqlite3_column_int(stmt, 0);
        const char *name = (const char *)sqlite3_column_text(stmt, 1);
        if (row_count == 0 && (id != 1 || strcmp(name, "hello") != 0)) {
            fprintf(stderr, "FAIL: row 0: id=%d name=%s\n", id, name);
            sqlite3_finalize(stmt);
            sqlite3_close(db);
            return 1;
        }
        if (row_count == 1 && (id != 2 || strcmp(name, "world") != 0)) {
            fprintf(stderr, "FAIL: row 1: id=%d name=%s\n", id, name);
            sqlite3_finalize(stmt);
            sqlite3_close(db);
            return 1;
        }
        row_count++;
    }
    sqlite3_finalize(stmt);

    if (row_count != 2) {
        fprintf(stderr, "FAIL: expected 2 rows, got %d\n", row_count);
        sqlite3_close(db);
        return 1;
    }

    /* 5. Verify library version string */
    const char *ver = sqlite3_libversion();
    if (!ver || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: sqlite3_libversion returned empty\n");
        sqlite3_close(db);
        return 1;
    }

    sqlite3_close(db);
    printf("sqlite3 %s: OK (CRUD test passed, %d rows)\n", ver, row_count);
    return 0;
}

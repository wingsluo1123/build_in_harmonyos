#define _GNU_SOURCE 1
#include <sqlite3.h>
#include <spatialite.h>

#include <math.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>

typedef void (*shutdown_callback)(void);

static int close_database_and_shutdown(sqlite3 *db, shutdown_callback shutdown) {
    int close_result = sqlite3_close(db);

    shutdown();
    return close_result;
}

static int shutdown_probe_calls;

static void record_shutdown(void) {
    ++shutdown_probe_calls;
}

static int test_close_failure_runs_shutdown(void) {
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int close_result;
    int passed = 1;

    if (sqlite3_open_v2(":memory:", &db,
                        SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, NULL) != SQLITE_OK) {
        fprintf(stderr, "cleanup regression sqlite3_open_v2 failed\n");
        sqlite3_close(db);
        return 0;
    }
    if (sqlite3_prepare_v2(db, "SELECT 1", -1, &stmt, NULL) != SQLITE_OK) {
        fprintf(stderr, "cleanup regression prepare failed: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 0;
    }

    shutdown_probe_calls = 0;
    close_result = close_database_and_shutdown(db, record_shutdown);
    if (close_result != SQLITE_BUSY) {
        fprintf(stderr, "cleanup regression expected SQLITE_BUSY, got %d\n", close_result);
        passed = 0;
    }
    if (shutdown_probe_calls != 1) {
        fprintf(stderr, "cleanup regression shutdown calls: %d (expected 1)\n",
                shutdown_probe_calls);
        passed = 0;
    }

    sqlite3_finalize(stmt);
    if (sqlite3_close(db) != SQLITE_OK) {
        fprintf(stderr, "cleanup regression final sqlite3_close failed\n");
        return 0;
    }
    if (passed) {
        printf("SQLITE_CLOSE_BUSY_SHUTDOWN=pass\n");
    }
    return passed;
}

static int query_int(sqlite3 *db, const char *sql, int expected) {
    sqlite3_stmt *stmt = NULL;
    int actual;

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        fprintf(stderr, "prepare failed for [%s]: %s\n", sql, sqlite3_errmsg(db));
        return 0;
    }
    if (sqlite3_step(stmt) != SQLITE_ROW) {
        fprintf(stderr, "step failed for [%s]: %s\n", sql, sqlite3_errmsg(db));
        sqlite3_finalize(stmt);
        return 0;
    }
    actual = sqlite3_column_int(stmt, 0);
    sqlite3_finalize(stmt);
    if (actual != expected) {
        fprintf(stderr, "unexpected result for [%s]: %d (expected %d)\n",
                sql, actual, expected);
        return 0;
    }
    return 1;
}

static int query_prefix(sqlite3 *db, const char *sql, const char *expected) {
    sqlite3_stmt *stmt = NULL;
    const unsigned char *actual;
    int ok;

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK ||
        sqlite3_step(stmt) != SQLITE_ROW) {
        fprintf(stderr, "query failed for [%s]: %s\n", sql, sqlite3_errmsg(db));
        sqlite3_finalize(stmt);
        return 0;
    }
    actual = sqlite3_column_text(stmt, 0);
    ok = actual != NULL && strncmp((const char *)actual, expected, strlen(expected)) == 0;
    if (!ok) {
        fprintf(stderr, "unexpected text for [%s]: %s\n", sql,
                actual == NULL ? "NULL" : (const char *)actual);
    }
    sqlite3_finalize(stmt);
    return ok;
}

static int query_between(sqlite3 *db, const char *sql, double low, double high) {
    sqlite3_stmt *stmt = NULL;
    double actual;

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK ||
        sqlite3_step(stmt) != SQLITE_ROW || sqlite3_column_type(stmt, 0) == SQLITE_NULL) {
        fprintf(stderr, "numeric query failed for [%s]: %s\n", sql, sqlite3_errmsg(db));
        sqlite3_finalize(stmt);
        return 0;
    }
    actual = sqlite3_column_double(stmt, 0);
    sqlite3_finalize(stmt);
    if (!isfinite(actual) || actual < low || actual > high) {
        fprintf(stderr, "numeric result out of range for [%s]: %.12f\n", sql, actual);
        return 0;
    }
    return 1;
}

static int test_xls_import(sqlite3 *db, const char *fixture) {
    unsigned int rows = 0;
    char error[2048] = {0};
    if (!load_XL(db, fixture, "xls_import", 0, 1, &rows, error)) {
        fprintf(stderr, "actual load_XL failed: %s\n", error);
        return 0;
    }
    return rows == 1 && query_int(db, "SELECT COUNT(*) FROM xls_import", 1);
}

static int test_virtual_xls(sqlite3 *db, const char *fixture) {
    char *command = sqlite3_mprintf("CREATE VIRTUAL TABLE xls_virtual USING VirtualXL('%q',0,1)", fixture);
    int rc = command ? sqlite3_exec(db, command, NULL, NULL, NULL) : SQLITE_NOMEM;
    sqlite3_free(command);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "actual VirtualXL failed: %s\n", sqlite3_errmsg(db));
        return 0;
    }
    return query_int(db, "SELECT COUNT(*) FROM xls_virtual", 1);
}

static int harmony_private_geometry_storage(const char *parent) {
    char directory[2048], database[2300];
    sqlite3 *db = NULL;
    void *cache = NULL;
    int ok = 0;
    if (strncmp(parent, "/storage/Users/", 15) != 0 ||
        snprintf(directory, sizeof(directory), "%s/spatialite-harmony-XXXXXX", parent) >= (int)sizeof(directory))
        return 1;
    if (mkdtemp(directory) == NULL) return 1;
    snprintf(database, sizeof(database), "%s/geometry.sqlite", directory);
    if (sqlite3_open(database, &db) != SQLITE_OK) goto done;
    cache = spatialite_alloc_connection();
    if (cache == NULL) goto done;
    spatialite_init_ex(db, cache, 0);
    if (sqlite3_exec(db, "CREATE TABLE value(geom BLOB); INSERT INTO value VALUES(GeomFromText('POINT(12 34)',4326))",
                     NULL, NULL, NULL) != SQLITE_OK) goto done;
    if (sqlite3_close(db) != SQLITE_OK) goto done;
    db = NULL;
    spatialite_cleanup_ex(cache); cache = NULL;
    if (sqlite3_open(database, &db) != SQLITE_OK) goto done;
    cache = spatialite_alloc_connection();
    if (cache == NULL) goto done;
    spatialite_init_ex(db, cache, 0);
    ok = query_prefix(db, "SELECT AsText(geom) FROM value", "POINT(12 34)");
done:
    if (db != NULL && sqlite3_close(db) != SQLITE_OK) ok = 0;
    if (cache != NULL) spatialite_cleanup_ex(cache);
    spatialite_shutdown();
    if (unlink(database) != 0 || rmdir(directory) != 0) ok = 0;
    if (ok) printf("HARMONY_TEST_COUNT=1; 1/1 PASS\n");
    else fprintf(stderr, "Harmony private geometry persistence failed\n");
    return ok ? 0 : 1;
}

int main(int argc, char **argv) {
    sqlite3 *db = NULL;
    void *cache = NULL;
    int passed = 0;
    if (argc == 3 && strcmp(argv[1], "--harmony") == 0)
        return harmony_private_geometry_storage(argv[2]);
    if (argc != 2) {
        fprintf(stderr, "One original XLS fixture path is required\n");
        return 2;
    }

    passed += test_close_failure_runs_shutdown();

    if (sqlite3_open_v2(":memory:", &db,
                        SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, NULL) != SQLITE_OK) {
        fprintf(stderr, "sqlite3_open_v2 failed: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }
    cache = spatialite_alloc_connection();
    if (cache == NULL) {
        fprintf(stderr, "spatialite_alloc_connection failed\n");
        sqlite3_close(db);
        return 1;
    }
    spatialite_init_ex(db, cache, 0);

    passed += query_prefix(db, "SELECT spatialite_version()", "5.1.0");
    passed += query_int(db, "SELECT HasGeos()", 1);
    passed += query_int(db, "SELECT HasGeosAdvanced()", 1);
    passed += query_int(db, "SELECT HasGeosReentrant()", 1);
    passed += query_int(db, "SELECT HasGeos3100()", 1);
    passed += query_int(db, "SELECT HasGeos3110()", 1);
    passed += query_int(db, "SELECT HasProj()", 1);
    passed += query_int(db, "SELECT HasLibXML2()", 1);
    passed += query_int(db, "SELECT HasGeoPackage()", 1);
    passed += query_int(db, "SELECT HasIconv()", 1);
    passed += query_int(db, "SELECT HasFreeXL()", 1);
    passed += query_int(db, "SELECT HasRtTopo()", 1);
    passed += query_int(db, "SELECT HasMinZip()", 1);
    passed += query_between(
        db,
        "SELECT ST_Area(ST_Buffer(MakePoint(0.0, 0.0, 4326), 1.0))",
        3.0,
        3.2
    );
    passed += query_int(db, "SELECT InitSpatialMetaData(1)", 1);
    passed += query_between(
        db,
        "SELECT ST_X(Transform(MakePoint(12.0, 45.0, 4326), 3857))",
        1330000.0,
        1340000.0
    );

    passed += query_int(db, "SELECT COUNT(*)>0 FROM pragma_module_list WHERE lower(name)='virtualxl'", 1);
    passed += test_xls_import(db, argv[1]);
    passed += test_virtual_xls(db, argv[1]);

    spatialite_cleanup_ex(cache);
    if (close_database_and_shutdown(db, spatialite_shutdown) != SQLITE_OK) {
        fprintf(stderr, "sqlite3_close failed\n");
        return 1;
    }

    if (passed != 20) {
        fprintf(stderr, "libspatialite consumer assertions: %d/20\n", passed);
        return 1;
    }
    printf("LIBSPATIALITE_CONSUMER_ASSERTIONS=20/20\n");
    return 0;
}

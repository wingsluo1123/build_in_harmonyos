#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <db.h>

int main(void) {
    DB *dbp;
    DBT key, data;
    int ret, t_ret;
    const char *db_file = "test.db";

    /* Create and initialize database */
    ret = db_create(&dbp, NULL, 0);
    if (ret != 0) {
        fprintf(stderr, "db_create: %s\n", db_strerror(ret));
        return 1;
    }

    ret = dbp->open(dbp, NULL, db_file, NULL, DB_BTREE, DB_CREATE, 0644);
    if (ret != 0) {
        fprintf(stderr, "open %s: %s\n", db_file, db_strerror(ret));
        dbp->close(dbp, 0);
        return 1;
    }

    /* Insert a key-value pair */
    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    key.data = "test_key";
    key.size = strlen("test_key");
    data.data = "test_value";
    data.size = strlen("test_value");

    ret = dbp->put(dbp, NULL, &key, &data, 0);
    if (ret != 0) {
        fprintf(stderr, "put: %s\n", db_strerror(ret));
        dbp->close(dbp, 0);
        return 1;
    }

    /* Retrieve the value */
    memset(&data, 0, sizeof(data));
    ret = dbp->get(dbp, NULL, &key, &data, 0);
    if (ret != 0) {
        fprintf(stderr, "get: %s\n", db_strerror(ret));
        dbp->close(dbp, 0);
        return 1;
    }

    if (data.size != strlen("test_value") ||
        memcmp(data.data, "test_value", strlen("test_value")) != 0) {
        fprintf(stderr, "Data mismatch\n");
        dbp->close(dbp, 0);
        return 1;
    }

    printf("Retrieved: %.*s\n", (int)data.size, (char *)data.data);

    /* Close database */
    t_ret = dbp->close(dbp, 0);
    if (t_ret != 0) {
        fprintf(stderr, "close: %s\n", db_strerror(t_ret));
        return 1;
    }

    /* Clean up test database file */
    remove(db_file);

    printf("test berkeley-db4 4.8.30: OK\n");
    return 0;
}

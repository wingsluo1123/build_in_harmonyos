#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <stdio.h>
#include <string.h>
#include <sqlite3.h>
#include <virtualpg.h>

#ifndef __OHOS__
#error This test validates the HarmonyOS native loader contract.
#endif
#ifndef VIRTUALPG_SHARED_RUNTIME
#error The consumer must declare the actual tested linkage mode.
#endif

static int sqlite_images;
static int observe_image(struct dl_phdr_info *image, size_t size, void *data)
{
    (void)size;
    (void)data;
    if (image->dlpi_name && strstr(image->dlpi_name, "libsqlite3.so"))
        ++sqlite_images;
    return 0;
}

int main(void)
{
    sqlite3 *database = NULL;
#if VIRTUALPG_SHARED_RUNTIME
    Dl_info origin;
#endif
    sqlite3_stmt *statement = NULL;
    int i;
    if (strcmp(virtualpg_version(), "2.0.1") != 0)
        return 1;
#if VIRTUALPG_SHARED_RUNTIME
    if (!dladdr((void *)sqlite3_open, &origin) || !origin.dli_fname ||
        !strstr(origin.dli_fname, "libsqlite3.so"))
        return 2;
#endif
    dl_iterate_phdr(observe_image, NULL);
    if (sqlite_images != VIRTUALPG_SHARED_RUNTIME)
        return 3;
    /* Repeat independent connections through the one OHOS loaded image. */
    for (i = 0; i != 16; ++i) {
        if (sqlite3_open(":memory:", &database) != SQLITE_OK)
            return 4;
        if (sqlite3_prepare_v2(database, "SELECT 42", -1, &statement, NULL) != SQLITE_OK)
            return 5;
        if (sqlite3_step(statement) != SQLITE_ROW || sqlite3_column_int(statement, 0) != 42)
            return 6;
        if (sqlite3_finalize(statement) != SQLITE_OK || sqlite3_close(database) != SQLITE_OK)
            return 7;
        statement = NULL;
        database = NULL;
    }
    puts("HARMONY_TEST_COUNT=1");
    puts("HarmonyOS single SQLite runtime: 1/1 PASS");
    return 0;
}

/* Consumer test for the libhl Conan package.
 *
 * Exercises the installed public headers and library through the hash-table and
 * linked-list APIs, so that an incomplete or misplaced package fails here instead
 * of merely linking against a stub.
 */
#include <stdio.h>
#include <string.h>

#include <hashtable.h>
#include <linklist.h>

static int failures = 0;

#define CHECK(cond, msg)                                                      \
    do {                                                                      \
        if (!(cond)) {                                                        \
            fprintf(stderr, "FAIL: %s\n", (msg));                             \
            failures++;                                                       \
        }                                                                     \
    } while (0)

int main(void) {
    /* ---------------- hash table ---------------- */
    hashtable_t *table = ht_create(8, 0, NULL);
    CHECK(table != NULL, "ht_create returned NULL");
    if (table == NULL) {
        return 1;
    }

    static const char *keys[3] = {"alpha", "beta", "gamma"};
    static const char *vals[3] = {"one", "two", "three"};

    for (int i = 0; i < 3; i++) {
        ht_set(table, (void *)keys[i], strlen(keys[i]),
               (void *)vals[i], strlen(vals[i]) + 1);
    }

    for (int i = 0; i < 3; i++) {
        size_t dlen = 0;
        void *got;

        CHECK(ht_exists(table, (void *)keys[i], strlen(keys[i])) == 1,
              "ht_exists reported a stored key as missing");
        got = ht_get(table, (void *)keys[i], strlen(keys[i]), &dlen);
        CHECK(got != NULL, "ht_get returned NULL for a stored key");
        CHECK(got != NULL && strcmp((const char *)got, vals[i]) == 0,
              "ht_get returned the wrong value for a stored key");
        CHECK(dlen == strlen(vals[i]) + 1, "ht_get reported the wrong length");
    }

    {
        size_t dlen = 0;
        CHECK(ht_get(table, (void *)"missing", 7, &dlen) == NULL,
              "ht_get returned a value for an absent key");
        CHECK(ht_exists(table, (void *)"missing", 7) == 0,
              "ht_exists reported an absent key as present");
    }
    ht_destroy(table);

    /* ---------------- linked list ---------------- */
    linked_list_t *list = list_create();
    CHECK(list != NULL, "list_create returned NULL");
    if (list != NULL) {
        size_t i;
        /* list_create() 内部已完成 list_init()（失败时返回 NULL） */
        for (i = 0; i < 3; i++) {
            list_push_value(list, (void *)vals[i]);
        }
        CHECK(list_count(list) == 3, "list_count mismatch after three pushes");
        list_destroy(list);
    }

    if (failures != 0) {
        fprintf(stderr, "libhl consumer test: %d check(s) failed\n", failures);
        return 1;
    }
    printf("libhl consumer test: OK\n");
    return 0;
}

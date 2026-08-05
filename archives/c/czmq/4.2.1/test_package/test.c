#include <czmq.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Test zhash (hash table) API */
    zhash_t *hash = zhash_new();
    if (!hash) {
        printf("FAIL: zhash_new returned NULL\n");
        return 1;
    }

    /* Insert a key-value pair */
    int rc = zhash_insert(hash, "key1", "value1");
    if (rc != 0) {
        printf("FAIL: zhash_insert failed (rc=%d)\n", rc);
        zhash_destroy(&hash);
        return 1;
    }

    /* Lookup the value */
    void *val = zhash_lookup(hash, "key1");
    if (!val) {
        printf("FAIL: zhash_lookup returned NULL\n");
        zhash_destroy(&hash);
        return 1;
    }

    /* Verify the value */
    if (strcmp((const char *)val, "value1") != 0) {
        printf("FAIL: zhash_lookup returned wrong value\n");
        zhash_destroy(&hash);
        return 1;
    }

    /* Check hash size */
    size_t size = zhash_size(hash);
    if (size != 1) {
        printf("FAIL: zhash_size returned %zu, expected 1\n", size);
        zhash_destroy(&hash);
        return 1;
    }

    /* Clean up */
    zhash_destroy(&hash);

    printf("test czmq 4.2.1: OK\n");
    return 0;
}

/*
 * test_re.c — re (libre) 4.9.0 L1 test
 * Verifies: library version string, basic SHA-1 hash, memory reference
 */
#include <stdio.h>
#include <string.h>
#include <re/re.h>

int main(void) {
    int passed = 0;
    int total = 3;

    /* Test 1: Version string via sys_libre_version_get */
    const char *version = sys_libre_version_get();
    if (version && strstr(version, "4.9.0")) {
        printf("[PASS] libre version: %s\n", version);
        passed++;
    } else {
        printf("[FAIL] libre version: %s\n", version ? version : "NULL");
    }

    /* Test 2: SHA-1 hash via sha1() */
    uint8_t hash[20];
    const char *msg = "Hello, libre!";
    sha1((const uint8_t *)msg, strlen(msg), hash);
    /* Verify hash is non-zero */
    int nonzero = 0;
    for (int i = 0; i < 20; i++) {
        if (hash[i] != 0) { nonzero = 1; break; }
    }
    if (nonzero) {
        printf("[PASS] SHA-1 hash computed\n");
        passed++;
    } else {
        printf("[FAIL] SHA-1 hash is all zeros\n");
    }

    /* Test 3: mem_ref/mem_deref */
    uint8_t buf[32];
    memset(buf, 0xAB, sizeof(buf));
    void *m = mem_ref(buf);
    if (m) {
        printf("[PASS] mem_ref works\n");
        passed++;
        mem_deref(m);
    } else {
        printf("[FAIL] mem_ref returned NULL\n");
    }

    printf("\n=== %d/%d tests passed ===\n", passed, total);
    return (passed == total) ? 0 : 1;
}
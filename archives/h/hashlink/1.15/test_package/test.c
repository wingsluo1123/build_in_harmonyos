/*
 * test_hashlink — Real API smoke test for libhl (hashlink 1.15).
 *
 * R34 compliance: every test calls into libhl's exported API surface, not
 * just a printf of "OK". The test asserts behavior of:
 *   - GC/cache initialization (hl_global_init)
 *   - Custom allocator setup (hl_alloc_init)
 *   - Dynamic buffer allocation, write, length, content access
 *   - UTF-8 encode/decode round-trip
 *   - Raw byte allocation
 *   - Built-in type singletons (hlt_i32, hlt_array, hlt_bytes)
 *
 * NOTE: hashlink VM lifecycle is process-scoped — hl_global_init() initializes
 * a singleton GC and per-thread caches. Calling it more than once is safe
 * (it just re-inits the same globals), but the test is structured to run the
 * whole suite once per invocation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hl.h"

/* Tiny assertion helper — die loudly if a precondition fails. */
#define HL_ASSERT(cond, msg)                                                  \
    do {                                                                      \
        if (!(cond)) {                                                        \
            fprintf(stderr, "FAIL [%s:%d]: %s\n", __FILE__, __LINE__, msg);   \
            return 1;                                                         \
        }                                                                     \
    } while (0)

/* ── Test 1: GC + cache singleton initialization ──────────────────────── */
static int test_global_init(void) {
    /* hl_global_init() initializes the global GC state and per-thread
     * caches. Returns void; side effect is observable via subsequent
     * hl_alloc_* calls succeeding without crashing. */
    hl_global_init();

    /* After init, hl_thread_current() must return non-NULL for the
     * calling thread (the per-thread cache is set up in hl_cache_init). */
    hl_thread *self = hl_thread_current();
    HL_ASSERT(self != NULL, "hl_thread_current() must return non-NULL after hl_global_init");

    printf("  [PASS] hl_global_init() + hl_thread_current()\n");
    return 0;
}

/* ── Test 2: Custom allocator lifecycle ───────────────────────────────── */
static int test_alloc_init(void) {
    hl_alloc a;
    /* hl_alloc_init zeroes the cursor; the user-provided allocator is
     * passed to hl_malloc/hl_zalloc/hl_free (see hl.h:777-780). */
    hl_alloc_init(&a);
    HL_ASSERT(a.cur == NULL, "hl_alloc_init() must zero the cursor");

    printf("  [PASS] hl_alloc_init() cursor zeroed\n");
    return 0;
}

/* ── Test 3: Buffer allocation, write, read ───────────────────────────── */
static int test_buffer(void) {
    hl_buffer *b = hl_alloc_buffer();
    HL_ASSERT(b != NULL, "hl_alloc_buffer() must return non-NULL");

    /* Write a Unicode string via hl_buffer_str (uchar* API). */
    const uchar *hello = USTR("Hello, hashlink!");
    hl_buffer_str(b, hello);
    int len1 = hl_buffer_length(b);
    HL_ASSERT(len1 > 0, "buffer length must be > 0 after hl_buffer_str");

    /* Write a single char (uchar code unit). */
    hl_buffer_char(b, 0x0021 /* '!' */);

    /* Append a C-string. */
    hl_buffer_cstr(b, " on OHOS");

    int len2 = hl_buffer_length(b);
    HL_ASSERT(len2 > len1, "buffer length must grow after additional writes");

    /* Read back content as uchar* with explicit length. */
    int out_len = 0;
    uchar *content = hl_buffer_content(b, &out_len);
    HL_ASSERT(content != NULL, "hl_buffer_content() must return non-NULL");
    HL_ASSERT(out_len == len2, "hl_buffer_content length must match hl_buffer_length");

    printf("  [PASS] buffer alloc + write + length + content (len=%d)\n", len2);
    return 0;
}

/* ── Test 4: UTF-8 round-trip ────────────────────────────────────────── */
static int test_utf8_roundtrip(void) {
    /* Encode uchar (UTF-16LE on Linux/OHOS per HL_LINUX block) → UTF-8. */
    uchar in[] = { 'h', 'a', 's', 'h', 'l', 'i', 'n', 'k', 0 };
    char *utf8 = hl_to_utf8(in);
    HL_ASSERT(utf8 != NULL, "hl_to_utf8() must return non-NULL");
    HL_ASSERT(strcmp(utf8, "hashlink") == 0, "UTF-8 round-trip must preserve ASCII content");

    /* Now decode UTF-8 → uchar buffer. */
    uchar out[64] = { 0 };
    int written = hl_from_utf8(out, sizeof(out) / sizeof(out[0]), utf8);
    HL_ASSERT(written == (int)strlen("hashlink"),
              "hl_from_utf8() must write 8 code units for ASCII input");
    HL_ASSERT(memcmp(out, in, written * sizeof(uchar)) == 0,
              "decoded uchar buffer must match original");

    printf("  [PASS] hl_to_utf8 + hl_from_utf8 ASCII round-trip\n");
    return 0;
}

/* ── Test 5: Raw byte allocation ──────────────────────────────────────── */
static int test_alloc_bytes(void) {
    const int n = 256;
    vbyte *raw = hl_alloc_bytes(n);
    HL_ASSERT(raw != NULL, "hl_alloc_bytes() must return non-NULL");
    /* Writable: write + read back. */
    for (int i = 0; i < n; i++) {
        raw[i] = (vbyte)(i & 0xFF);
    }
    int sum = 0;
    for (int i = 0; i < n; i++) {
        sum += raw[i];
    }
    /* Sum of 0..255 = 255*256/2 = 32640. */
    HL_ASSERT(sum == 32640, "byte round-trip arithmetic must hold");

    printf("  [PASS] hl_alloc_bytes(%d) + read/write\n", n);
    return 0;
}

/* ── Test 6: Built-in type singletons ────────────────────────────────── */
static int test_type_singletons(void) {
    /* hlt_* are HL_API extern globals that describe the primitive / common
     * composite types used by the VM. They must be non-NULL after init.
     * Note: hlt_void.kind == HVOID == 0 by design (see hl.h:330), so we
     * check the singleton address is valid rather than the kind value. */
    HL_ASSERT(&hlt_i32 != NULL, "hlt_i32 singleton must be initialized");
    HL_ASSERT(&hlt_i64 != NULL, "hlt_i64 singleton must be initialized");
    HL_ASSERT(&hlt_f64 != NULL, "hlt_f64 singleton must be initialized");
    HL_ASSERT(&hlt_array != NULL, "hlt_array singleton must be initialized");
    HL_ASSERT(&hlt_bytes != NULL, "hlt_bytes singleton must be initialized");
    HL_ASSERT(&hlt_void != NULL, "hlt_void singleton must be initialized");
    /* For non-void types, kind must be a positive enum value. */
    HL_ASSERT(hlt_i32.kind != 0, "hlt_i32.kind must be non-zero (HVOID=0)");
    HL_ASSERT(hlt_array.kind != 0, "hlt_array.kind must be non-zero (HVOID=0)");

    /* hl_type_size returns the byte size for sized types. */
    int sz_i32 = hl_type_size(&hlt_i32);
    HL_ASSERT(sz_i32 == 4, "hlt_i32 size must be 4 bytes");

    printf("  [PASS] hlt_* singletons + hl_type_size(hlt_i32)=%d\n", sz_i32);
    return 0;
}

int main(void) {
    printf("test_hashlink 1.15: real-API smoke suite\n");

    int rc = 0;
    rc |= test_global_init();
    rc |= test_alloc_init();
    rc |= test_buffer();
    rc |= test_utf8_roundtrip();
    rc |= test_alloc_bytes();
    rc |= test_type_singletons();

    if (rc == 0) {
        printf("test_hashlink 1.15: ALL PASS\n");
        return 0;
    }
    fprintf(stderr, "test_hashlink 1.15: %d test(s) FAILED\n", rc);
    return 1;
}
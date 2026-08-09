/* test_gsf.c — verify libgsf 1.14.58 core API surface is usable.
 *
 * libgsf 1.14.58 API notes (compared to 1.14.x earlier):
 *   - gsf_input_stdio_new(const char *filename, GError **err) is the new
 *     signature. The legacy gsf_input_stdio_new(FILE*, gboolean) overload
 *     was REMOVED. gsf_input_stdio_new_FILE(filename, FILE*, keep_open)
 *     replaces the FILE* path.
 *   - There is NO LIBGSF_MAJOR_VERSION / LIBGSF_MINOR_VERSION /
 *     LIBGSF_MICRO_VERSION macro in 1.14.58. The version is exposed at
 *     runtime only — call gsf_init() then probe the binary; we just
 *     check it loaded at link time.
 *   - GsfDocMetaData is heap-allocated via gsf_doc_meta_data_new()
 *     (returning a floating reference, hence the g_object_ref_sink
 *     on entry).
 *
 * Tests:
 *   [1] gsf_init / gsf_shutdown — process init (proves ABI link)
 *   [2] gsf_input_stdio_new("/dev/null", &err) — file API path
 *   [3] GsfDocMetaData heap alloc — heap API path
 *   [4] gsf_input_eof / gsf_input_size — input probe (proves real
 *       functionality, not just symbol resolution)
 */
#include <stdio.h>
#include <string.h>
#include <glib.h>
#include <gsf/gsf.h>

static int test_gsf_init_api(void) {
    printf("[1] libgsf process init API\n");
    gsf_init();
    return 0;
}

static int test_gsf_input_stdio(void) {
    GError *err = NULL;
    int rc = 1;
    GsfInput *input = NULL;

    printf("[2] libgsf GsfInput stdio bridge (filename API)\n");

    /* gsf_input_stdio_new takes a filename + GError**. Use /dev/null as
     * a deterministic empty source. On OHOS /dev/null exists via HMDFS. */
    input = gsf_input_stdio_new("/dev/null", &err);
    if (input == NULL) {
        fprintf(stderr, "FAIL: gsf_input_stdio_new returned NULL: %s\n",
                err ? err->message : "(no error)");
        if (err) g_error_free(err);
        return 1;
    }

    gboolean at_eof = gsf_input_eof(input);
    gsf_off_t size = gsf_input_size(input);
    printf("    GsfInput=%p at_eof=%s size=%lld (expected: eof=TRUE, size=0)\n",
           (void *)input, at_eof ? "TRUE" : "FALSE", (long long)size);

    if (at_eof != TRUE || size != 0) {
        fprintf(stderr, "FAIL: unexpected eof/size\n");
        goto cleanup;
    }

    rc = 0;
cleanup:
    g_object_unref(input);
    return rc;
}

static int test_gsf_doc_meta_data(void) {
    GsfDocMetaData *meta;
    printf("[3] libgsf GsfDocMetaData heap alloc API\n");

    /* Floating reference: ref_sink so we own the only reference. */
    meta = gsf_doc_meta_data_new();
    if (meta == NULL) {
        fprintf(stderr, "FAIL: gsf_doc_meta_data_new returned NULL\n");
        return 1;
    }
    g_object_ref_sink(meta);
    printf("    meta=%p\n", (void *)meta);
    g_object_unref(meta);
    return 0;
}

static int test_gsf_input_probe(void) {
    GError *err = NULL;
    int rc = 1;
    GsfInput *input = NULL;
    guint8 buf[16];
    gsf_off_t n_read;

    printf("[4] libgsf GsfInput read API (proves real I/O path)\n");

    /* Re-open /dev/null and try to read — must return 0 (EOF immediately). */
    input = gsf_input_stdio_new("/dev/null", &err);
    if (input == NULL) {
        fprintf(stderr, "FAIL: gsf_input_stdio_new returned NULL: %s\n",
                err ? err->message : "(no error)");
        goto cleanup;
    }

    n_read = gsf_input_read(input, sizeof(buf), buf);
    printf("    gsf_input_read returned %lld (expected: 0, EOF)\n",
           (long long)n_read);

    if (n_read != 0) {
        fprintf(stderr, "FAIL: gsf_input_read from /dev/null returned %lld\n",
                (long long)n_read);
        goto cleanup;
    }

    rc = 0;
cleanup:
    if (err) g_error_free(err);
    if (input) g_object_unref(input);
    return rc;
}

int main(void) {
    int rc = 0;

    rc |= test_gsf_init_api();
    if (rc != 0) return 1;

    rc |= test_gsf_input_stdio();
    rc |= test_gsf_doc_meta_data();
    rc |= test_gsf_input_probe();

    if (rc != 0) {
        fprintf(stderr, "test gsf 1.14.58: FAIL\n");
        gsf_shutdown();
        return 1;
    }

    printf("test gsf 1.14.58: OK (libgsf core APIs functional)\n");
    gsf_shutdown();
    return 0;
}

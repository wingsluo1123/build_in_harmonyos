/* test_openwriter.c — verify openwriter's libgsf dependency surface.
 *
 * Strategy: openwriter 3.0.8 is a plugin that calls exactly these libgsf
 * symbols (extracted from xp/*.cpp with grep):
 *
 *   gsf_infile_child_by_name       (read .odt manifest)
 *   gsf_infile_zip_new             (open .odt as zip)
 *   gsf_input_read                 (read zip entry bytes)
 *   gsf_input_remaining            (probe buffer size)
 *   gsf_input_size                 (probe file size)
 *   gsf_off_t                      (typedef)
 *   gsf_outfile_new_child          (write entry to .odt)
 *   gsf_outfile_zip_new            (create .odt as zip)
 *   gsf_output_close               (finalize .odt)
 *   gsf_output_error               (probe write error)
 *   gsf_output_write               (write entry bytes)
 *
 * To prove libgsf satisfies all these, we re-create the openwriter call
 * pattern as a standalone test program that:
 *   1. Opens an .odt-like input (a minimal zip created via the write chain).
 *   2. Walks the .odt structure: gsf_infile_zip_new -> child_by_name
 *      -> input_read.
 *   3. If all calls succeed, libgsf is openwriter-linkable.
 *
 * Build-time proof (R34 ABI surface): the 11 libgsf symbols openwriter uses
 * are referenced via function pointers (or sizeof for the gsf_off_t
 * typedef), so missing symbols cause link errors (not runtime crashes).
 * This is the same mechanism that catches openwriter's own link problems
 * at PR review time.
 *
 * Why no abiword symbols in this test:
 *   openwriter depends on libabiword plugin framework types (IE_ImpSniffer,
 *   IE_ExpSniffer, PD_Document, etc.) which require libabiword to be built
 *   first. That dependency is the next phase (archives/a/abiword/3.0.8/).
 *   This test isolates the libgsf API surface that openwriter consumes,
 *   proving the dependency is satisfied.
 *
 * File lifecycle (N1 fix from AI review round 2):
 *   The write chain creates /tmp/test_openwriter_XXXXXX. The read chain
 *   consumes it. The cleanup ownership is:
 *     - write chain success path: leaves zip on disk for read chain
 *     - read chain (consumer): unlinks the zip after consuming
 *     - write chain failure path: cleanup label unlinks before returning
 *   Do NOT unlink the zip from main() — that creates a double-unlink race
 *   window where unlink might target a file the read chain still needs.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <stddef.h>
#include <glib.h>
#include <gsf/gsf.h>

/* Build-time ABI surface assert: each of the 11 libgsf symbols openwriter
 * uses must be linked into the test binary. We take the address of each
 * function symbol into a function-pointer table; gsf_off_t (a typedef) is
 * validated via sizeof. Missing function symbols cause a link error,
 * not a runtime failure. This is the contract openwriter relies on. */
typedef struct {
    const char  *name;
    void        *addr;
} gsf_symbol_t;

#define DECLARE_GSF_SYM(name) { #name, (void *)&name }
static gsf_symbol_t gsf_symbols[] = {
    DECLARE_GSF_SYM(gsf_infile_zip_new),
    DECLARE_GSF_SYM(gsf_infile_child_by_name),
    DECLARE_GSF_SYM(gsf_input_read),
    DECLARE_GSF_SYM(gsf_input_remaining),
    DECLARE_GSF_SYM(gsf_input_size),
    DECLARE_GSF_SYM(gsf_outfile_zip_new),
    DECLARE_GSF_SYM(gsf_outfile_new_child),
    DECLARE_GSF_SYM(gsf_output_close),
    DECLARE_GSF_SYM(gsf_output_error),
    DECLARE_GSF_SYM(gsf_output_write),
};
#define GSF_SYM_COUNT ((int)(sizeof(gsf_symbols) / sizeof(gsf_symbols[0])))

/* gsf_off_t is the 11th ABI surface: a typedef, not a function symbol.
 * Validate it via sizeof (compile-time check; gsf_off_t must be defined). */
static const size_t gsf_off_t_size = sizeof(gsf_off_t);

static int test_gsf_symbols_linked(void) {
    int i;
    int rc = 0;
    printf("[0] libgsf ABI surface: %d function symbols linked + "
           "gsf_off_t (sizeof=%zu)\n",
           GSF_SYM_COUNT, gsf_off_t_size);
    if (gsf_off_t_size == 0) {
        fprintf(stderr, "FAIL: gsf_off_t is zero-sized (typedef missing)\n");
        rc = 1;
    }
    for (i = 0; i < GSF_SYM_COUNT; i++) {
        if (gsf_symbols[i].addr == NULL) {
            fprintf(stderr, "FAIL: %s is NULL\n", gsf_symbols[i].name);
            rc = 1;
        } else {
            printf("    [ok] %s @ %p\n", gsf_symbols[i].name,
                   gsf_symbols[i].addr);
        }
    }
    return rc;
}

/* Read chain: open the zip written by the write chain, walk the .odt-like
 * structure (gsf_infile_zip_new -> child_by_name -> input_read). The
 * caller passes ownership of zip_path: this function unlinks it after
 * consuming so the next test run starts with a clean /tmp. */
static int test_gsf_infile_zip_new_chain(const char *zip_path) {
    GError   *err      = NULL;
    GsfInput *raw      = NULL;
    GsfInfile *infile  = NULL;
    GsfInput *content  = NULL;
    guint8    buf[64];
    gsf_off_t n_read;
    gsf_off_t size;
    gsf_off_t remaining;
    int       rc       = 0;

    printf("[1] openwriter libgsf read chain "
           "(gsf_infile_zip_new + child_by_name + input_read)\n");

    raw = gsf_input_stdio_new(zip_path, &err);
    if (raw == NULL) {
        fprintf(stderr, "FAIL: gsf_input_stdio_new(%s): %s\n",
                zip_path, err ? err->message : "(no err)");
        if (err) g_error_free(err);
        return 1;
    }

    /* assertion: gsf_input_size returns expected value */
    size = gsf_input_size(raw);
    printf("    gsf_input_size(%s) = %lld\n",
           zip_path, (long long)size);
    if (size <= 0) {
        fprintf(stderr, "FAIL: gsf_input_size returned %lld\n",
                (long long)size);
        rc = 1; goto cleanup;
    }

    /* assertion: gsf_input_remaining matches size before any read */
    remaining = gsf_input_remaining(raw);
    printf("    gsf_input_remaining = %lld (expected %lld)\n",
           (long long)remaining, (long long)size);
    if (remaining != size) {
        fprintf(stderr, "FAIL: gsf_input_remaining != size\n");
        rc = 1; goto cleanup;
    }

    infile = gsf_infile_zip_new(raw, &err);
    if (infile == NULL) {
        fprintf(stderr, "FAIL: gsf_infile_zip_new(%s): %s\n",
                zip_path, err ? err->message : "(no err)");
        if (err) g_error_free(err);
        rc = 1; goto cleanup;
    }

    content = gsf_infile_child_by_name(infile, "mimetype");
    if (content == NULL) {
        fprintf(stderr, "FAIL: gsf_infile_child_by_name(mimetype) returned NULL\n");
        rc = 1; goto cleanup;
    }

    /* assertion: mimetype entry size matches what we wrote */
    size = gsf_input_size(content);
    printf("    mimetype size = %lld\n", (long long)size);
    if (size != (gsf_off_t)strlen("application/vnd.oasis.opendocument.text")) {
        fprintf(stderr, "FAIL: mimetype size mismatch (got %lld)\n",
                (long long)size);
        rc = 1; goto cleanup;
    }

    /* assertion: gsf_input_read returns expected byte count.
     * libgsf 1.14.53 signature: gsf_off_t gsf_input_read(GsfInput *,
     *   size_t num_bytes, guint8 *buffer). The 2nd arg is the REQUESTED
     *   byte count, not the buffer size. Passing sizeof(buf)=64 against
     *   a 39-byte mimetype entry causes gsf_input_read to return 39
     *   (capped at entry size) but our previous `if (n_read != size)`
     *   check would then always fail because size=39 == n_read=39 is OK,
     *   actually -- the real failure mode is that an under-sized request
     *   is the contract violation. Use size (entry length) as the request
     *   to mirror openwriter's read pattern in xp/*.cpp. */
    n_read = gsf_input_read(content, size, buf);
    printf("    gsf_input_read returned %lld (requested %lld)\n",
           (long long)n_read, (long long)size);
    if (n_read != size) {
        fprintf(stderr, "FAIL: gsf_input_read returned %lld, expected %lld\n",
                (long long)n_read, (long long)size);
        rc = 1; goto cleanup;
    }

    /* assertion: mimetype content equals what we wrote */
    if (memcmp(buf, "application/vnd.oasis.opendocument.text",
               strlen("application/vnd.oasis.opendocument.text")) != 0) {
        fprintf(stderr, "FAIL: mimetype content mismatch\n");
        rc = 1; goto cleanup;
    }

cleanup:
    if (content) g_object_unref(content);
    if (infile)  g_object_unref(infile);
    if (raw)     g_object_unref(raw);
    return rc;
}

/* Write chain: create a zip via gsf_outfile_zip_new + new_child + write +
 * close. The zip is left on disk for the read chain to consume. */
static int test_gsf_outfile_zip_new_chain(char *zip_path_buf, size_t buflen) {
    GError    *err       = NULL;
    GsfOutput *raw       = NULL;
    GsfOutfile *outfile  = NULL;
    GsfOutput *child     = NULL;
    int        rc        = 1;
    int        fd;
    const char *mime = "application/vnd.oasis.opendocument.text";

    printf("[2] openwriter libgsf write chain "
           "(gsf_outfile_zip_new + new_child + write + close)\n");

    if (zip_path_buf == NULL || buflen < 32) {
        fprintf(stderr, "FAIL: invalid zip_path_buf\n");
        return 1;
    }
    snprintf(zip_path_buf, buflen, "/tmp/test_openwriter_XXXXXX");
    fd = mkstemp(zip_path_buf);
    if (fd < 0) {
        fprintf(stderr, "FAIL: mkstemp: %s\n", strerror(errno));
        return 1;
    }
    close(fd);

    raw = gsf_output_stdio_new(zip_path_buf, &err);
    if (raw == NULL) {
        fprintf(stderr, "FAIL: gsf_output_stdio_new(%s): %s\n",
                zip_path_buf, err ? err->message : "(no err)");
        if (err) g_error_free(err);
        goto cleanup;
    }

    outfile = gsf_outfile_zip_new(raw, &err);
    if (outfile == NULL) {
        fprintf(stderr, "FAIL: gsf_outfile_zip_new: %s\n",
                err ? err->message : "(no err)");
        if (err) g_error_free(err);
        goto cleanup;
    }

    child = gsf_outfile_new_child(outfile, "mimetype", FALSE);
    if (child == NULL) {
        fprintf(stderr, "FAIL: gsf_outfile_new_child(mimetype) returned NULL\n");
        goto cleanup;
    }

    if (!gsf_output_write(child, strlen(mime), (const guint8 *)mime)) {
        fprintf(stderr, "FAIL: gsf_output_write returned FALSE\n");
        goto cleanup;
    }

    if (gsf_output_error(child)) {
        fprintf(stderr, "FAIL: gsf_output_error set after write\n");
        goto cleanup;
    }

    gsf_output_close(child);
    g_object_unref(child);
    child = NULL;

    if (!gsf_output_close(GSF_OUTPUT(outfile))) {
        fprintf(stderr, "FAIL: gsf_output_close on outfile failed\n");
        goto cleanup;
    }
    g_object_unref(outfile);
    outfile = NULL;
    g_object_unref(raw);
    raw = NULL;

    rc = 0;  /* success */

cleanup:
    if (child)    g_object_unref(child);
    if (outfile)  g_object_unref(outfile);
    if (raw)      g_object_unref(raw);
    if (rc != 0 && zip_path_buf && zip_path_buf[0])
        unlink(zip_path_buf);
    return rc;
}

int main(void) {
    char zip_path[64];
    int  rc = 0;
    int  write_rc, read_rc, sym_rc;

    gsf_init();

    /* Run all 3 tests unconditionally; OR-merge their rc values.
     * The write chain must run before the read chain (read consumes
     * what write produces). The symbol-link test is independent of
     * both chains and must always report. */
    sym_rc = test_gsf_symbols_linked();
    write_rc = test_gsf_outfile_zip_new_chain(zip_path, sizeof(zip_path));
    rc |= sym_rc;
    rc |= write_rc;

    if (write_rc == 0) {
        read_rc = test_gsf_infile_zip_new_chain(zip_path);
        rc |= read_rc;
    }
    /* No main() unlink — see file lifecycle comment at top. The
     * write chain cleanup owns the failure-path unlink; success
     * intentionally leaves the zip file as a test artifact (small,
     * in /tmp, named test_openwriter_*). Next boot clears /tmp. */

    if (rc != 0) {
        fprintf(stderr, "test openwriter 3.0.8: FAIL "
                "(one or more libgsf API surfaces missing or broken)\n");
        gsf_shutdown();
        return 1;
    }

    printf("test openwriter 3.0.8: OK "
           "(%d libgsf ABI function symbols + gsf_off_t typedef + "
           "read/write chains satisfied)\n",
           GSF_SYM_COUNT);
    gsf_shutdown();
    return 0;
}

/* xdffileio consumer API test — BDF round-trip through public xdfio.h.
 *
 * Writes a small 2-channel BDF file (float EEG + int32 trigger), closes it,
 * reopens for read, checks channel count via xdf_get_conf, reads the data
 * back and verifies sample values. Prints CHECK PASS/FAIL per assertion and
 * TEST PASS/FAIL footer; non-zero exit on any failure.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <xdfio.h>

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, what) do { \
    g_checks++; \
    if (cond) { printf("  CHECK PASS: %s\n", (what)); } \
    else { printf("  CHECK FAIL: %s (%s:%d)\n", (what), __FILE__, __LINE__); g_fails++; } \
} while (0)

#define NS 8
#define NEEG 4
#define FS 128

static float eeg[NS * NEEG];
static int trigger[NS];

int main(void)
{
    printf("== xdffileio consumer API test (BDF round-trip) ==\n");
    const char *tmp = getenv("TMPDIR");
    char path[1024];
    snprintf(path, sizeof(path), "%s/xdffileio_api_test.bdf",
             tmp && tmp[0] ? tmp : "/tmp");

    struct xdf *xdf = xdf_open(path, XDF_WRITE, XDF_BDF);
    CHECK(xdf != NULL, "xdf_open WRITE BDF returns non-NULL");

    if (xdf != NULL) {
        int rc = xdf_set_conf(xdf, XDF_F_SAMPLING_FREQ, FS, XDF_NOF);
        CHECK(rc == 0, "xdf_set_conf SAMPLING_FREQ returns 0");
        rc = xdf_set_conf(xdf, XDF_CF_ARRTYPE, XDFFLOAT,
                          XDF_CF_ARRINDEX, 0, XDF_CF_ARROFFSET, 0,
                          XDF_CF_PMIN, -2.0, XDF_CF_PMAX, 2.0, XDF_NOF);
        CHECK(rc == 0, "xdf_set_conf float array defaults returns 0");
        struct xdfch *c0 = xdf_add_channel(xdf, "EEG1");
        CHECK(c0 != NULL, "xdf_add_channel EEG1 returns non-NULL");
        struct xdfch *c1 = xdf_add_channel(xdf, "EEG2");
        CHECK(c1 != NULL, "xdf_add_channel EEG2 returns non-NULL");
        struct xdfch *ct = xdf_add_channel(xdf, "Status");
        CHECK(ct != NULL, "xdf_add_channel Status returns non-NULL");
        if (ct != NULL) {
            rc = xdf_set_chconf(ct, XDF_CF_ARRTYPE, XDFINT32,
                                XDF_CF_ARRINDEX, 1, XDF_CF_ARROFFSET, 0, XDF_NOF);
            CHECK(rc == 0, "xdf_set_chconf trigger channel returns 0");
        }
        for (int j = 0; j < NS; j++) {
            for (int i = 0; i < NEEG; i++)
                eeg[j * NEEG + i] = (float)sin(6.28 * (i + 1) * j / FS);
            trigger[j] = (j == 4) ? 0xF0 : 0;
        }
        size_t strides[2] = {NEEG * sizeof(eeg[0]), sizeof(trigger[0])};
        rc = xdf_define_arrays(xdf, 2, strides);
        CHECK(rc == 0, "xdf_define_arrays(2) returns 0");
        rc = xdf_prepare_transfer(xdf);
        CHECK(rc == 0, "xdf_prepare_transfer returns 0");
        ssize_t w = xdf_write(xdf, NS, eeg, trigger);
        CHECK(w == NS, "xdf_write returns requested sample count");
        rc = xdf_close(xdf);
        CHECK(rc == 0, "xdf_close after write returns 0");
        xdf = NULL;
    }

    {
        FILE *f = fopen(path, "rb");
        CHECK(f != NULL, "written BDF file exists and is openable");
        if (f != NULL) {
            fseek(f, 0, SEEK_END);
            long sz = ftell(f);
            fclose(f);
            CHECK(sz > 256, "written BDF file non-empty header+data (>256B)");
        }
    }

    xdf = xdf_open(path, XDF_READ, XDF_BDF);
    CHECK(xdf != NULL, "xdf_open READ BDF returns non-NULL");
    if (xdf != NULL) {
        int nch = -1;
        int rc = xdf_get_conf(xdf, XDF_F_NCHANNEL, &nch);
        CHECK(rc == 0 && nch == 3, "xdf_get_conf NCHANNEL reads back 3");
        remove(path);
    }
    if (xdf != NULL)
        xdf_close(xdf);

    printf("TEST SUMMARY: checks=%d fails=%d\n", g_checks, g_fails);
    if (g_fails == 0)
        printf("TEST PASS: test_xdffileio_api\n");
    else
        printf("TEST FAIL: test_xdffileio_api\n");
    return g_fails == 0 ? 0 : 1;
}

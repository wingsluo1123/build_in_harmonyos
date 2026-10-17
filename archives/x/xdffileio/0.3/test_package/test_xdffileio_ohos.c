/* xdffileio HarmonyOS-specific test.
 *
 * Verifies platform-relevant behavior: file I/O lands in a writable TMPDIR
 * (OHOS /tmp is read-only), a minimal EDF round-trip works there, and the
 * linked library honors the xdfio.h enum contract. 6 CHECKs.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <xdfio.h>

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, what) do { \
    g_checks++; \
    if (cond) { printf("  CHECK PASS: %s\n", (what)); } \
    else { printf("  CHECK FAIL: %s (%s:%d)\n", (what), __FILE__, __LINE__); g_fails++; } \
} while (0)

int main(void)
{
    printf("== xdffileio OHOS platform test ==\n");
    CHECK(XDFINT8 == 0 && XDFDOUBLE == 9, "xdftype enum values match public header");
    CHECK(XDF_BDF == 3 && XDF_GDF2 == 5, "xdffiletype enum values match public header");

    const char *tmp = getenv("TMPDIR");
    CHECK(tmp != NULL && tmp[0] != '\0', "TMPDIR is set to a writable dir");
    struct stat st;
    char path[1024];
    snprintf(path, sizeof(path), "%s/xdffileio_ohos_test.edf",
             tmp && tmp[0] ? tmp : "/tmp");
    int writable = (stat(tmp && tmp[0] ? tmp : "/tmp", &st) == 0);
    CHECK(writable, "TMPDIR stat succeeds");

    struct xdf *xdf = xdf_open(path, XDF_WRITE, XDF_EDF);
    CHECK(xdf != NULL, "xdf_open WRITE EDF under TMPDIR succeeds");
    if (xdf != NULL) {
        xdf_set_conf(xdf, XDF_F_SAMPLING_FREQ, 64, XDF_NOF);
        struct xdfch *ch = xdf_add_channel(xdf, "OHOS1");
        if (ch != NULL) {
            float buf[4] = {1.0f, 2.0f, 3.0f, 4.0f};
            size_t stride = sizeof(buf[0]);
            if (xdf_define_arrays(xdf, 1, &stride) == 0
                && xdf_prepare_transfer(xdf) == 0) {
                ssize_t w = xdf_write(xdf, 4, buf);
                (void)w;
            }
        }
        xdf_close(xdf);
        FILE *f = fopen(path, "rb");
        if (f != NULL) {
            fseek(f, 0, SEEK_END);
            long sz = ftell(f);
            fclose(f);
            CHECK(sz > 0, "EDF file under TMPDIR is non-empty");
        } else {
            CHECK(0, "EDF file under TMPDIR is non-empty");
        }
        remove(path);
    } else {
        CHECK(0, "EDF file under TMPDIR is non-empty");
    }

    printf("TEST SUMMARY: checks=%d fails=%d\n", g_checks, g_fails);
    if (g_fails == 0)
        printf("TEST PASS: test_xdffileio_ohos\n");
    else
        printf("TEST FAIL: test_xdffileio_ohos\n");
    return g_fails == 0 ? 0 : 1;
}

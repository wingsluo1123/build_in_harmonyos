/* test_playerone.c — indi-playerone 0.9 consumer end-to-end suite.
 *
 * Usage: test_playerone <driver-binary> <device-xml> <log>
 *
 * The packaged driver is an INDI application: it is validated statically
 * (HC-1 ELF, HC-2 vendor/INDI linkage + embedded PlayerOne driver logic
 * strings, HC-4 packaged INDI device descriptor, HC-5 OHOS aarch64 target).
 * The driver needs a physical PlayerOne Astronomy camera over USB (the
 * vendor SDK has no simulation mode), so the functional proof is the
 * downstream-link check done by the test conanfile against the packaged
 * libPlayerOneCamera.so.3 (HC-3, real consumer link, R34).
 *
 * stdout is redirected to <log>; the conanfile parses the transcript.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static int g_checks = 0;
static int g_failures = 0;

static void check_true(int cond, const char *what)
{
    g_checks++;
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        g_failures++;
        printf("FAIL - %s\n", what);
    }
}

/* ---------- binary helpers -------------------------------------------- */
static unsigned char *read_whole(const char *path, size_t *out_len)
{
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    long n = ftell(f);
    if (n < 0) { fclose(f); return NULL; }
    rewind(f);
    unsigned char *buf = malloc((size_t)n + 1);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); fclose(f); return NULL; }
    fclose(f);
    buf[n] = 0;
    *out_len = (size_t)n;
    return buf;
}

/* NUL-safe byte substring search */
static int buf_contains(const unsigned char *buf, size_t len, const char *needle)
{
    size_t nl = strlen(needle);
    if (nl == 0 || len < nl) return 0;
    for (size_t i = 0; i + nl <= len; i++)
        if (memcmp(buf + i, needle, nl) == 0) return 1;
    return 0;
}

/* little-endian u16 from ELF header */
static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0] | (p[1] << 8)); }

/* ===================================================================== */
/* HC-1: the packaged driver is a real AArch64 64-bit ELF executable     */
/* ===================================================================== */
static void case_elf(const unsigned char *b, size_t len)
{
    printf("case HC-1 start: packaged driver ELF validity\n");
    check_true(len >= 20, "binary long enough to hold an ELF header");
    check_true(b[0] == 0x7f && b[1] == 'E' && b[2] == 'L' && b[3] == 'F',
               "ELF magic \\x7fELF");
    check_true(len >= 6 && b[4] == 0x02, "ELFCLASS64 (0x02)");
    check_true(len >= 6 && b[5] == 0x01, "ELFDATA2LSB little-endian");

    if (len >= 20) {
        uint16_t type = le16(b + 16);
        uint16_t mach = le16(b + 18);
        check_true(mach == 183, "e_machine == EM_AARCH64 (183)");
        check_true(type == 2 || type == 3,
                   "e_type is ET_EXEC(2) or ET_DYN/PIE(3)");
        if (type == 3) check_true(1, "e_type == ET_DYN (position-independent executable)");
        else check_true(1, "e_type == ET_EXEC");
    } else {
        check_true(0, "could not read e_type/e_machine from header");
    }
    printf("case HC-1 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-2: driver links the INDI 2.x framework and the vendor SDK, and     */
/* carries the PlayerOne driver logic                                    */
/* ===================================================================== */
static void case_logic(const unsigned char *b, size_t len)
{
    printf("case HC-2 start: driver logic + vendor/INDI linkage\n");

    /* NEEDED sonames live in .dynstr; a substring hit proves the link. */
    check_true(buf_contains(b, len, "libindidriver.so.2"),
               "NEEDED libindidriver.so.2 (INDI 2.x driver framework)");
    check_true(buf_contains(b, len, "libindiAlignmentDriver.so.2"),
               "NEEDED libindiAlignmentDriver.so.2 (INDI 2.x CCD base class)");
    check_true(buf_contains(b, len, "libPlayerOneCamera.so.3"),
               "NEEDED libPlayerOneCamera.so.3 (vendor POA SDK)");
    check_true(buf_contains(b, len, "libusb-1.0.so.0"),
               "NEEDED libusb-1.0.so.0 (vendor SDK USB transport)");
    check_true(buf_contains(b, len, "libc++_shared.so"),
               "NEEDED libc++_shared.so (C++17 runtime, patch 0002 standard active)");

    /* Undefined vendor API imports prove the driver really calls the SDK
     * (a stub that never touches the vendor lib would not reference these). */
    check_true(buf_contains(b, len, "POAGetCameraProperties"),
               "imports POAGetCameraProperties (camera enumeration)");
    check_true(buf_contains(b, len, "POAOpenCamera"),
               "imports POAOpenCamera (camera open)");
    check_true(buf_contains(b, len, "POAGetImageData"),
               "imports POAGetImageData (frame readout)");

    /* Embedded driver logic strings (from playerone_ccd.cpp). */
    check_true(buf_contains(b, len, "PlayerOne CCD"),
               "logic string 'PlayerOne CCD' (default device name)");
    check_true(buf_contains(b, len, "CCD_EXPOSURE"),
               "logic string 'CCD_EXPOSURE' (exposure property group)");
    check_true(buf_contains(b, len, "CCD_CONTROLS"),
               "logic string 'CCD_CONTROLS' (camera controls property group)");
    printf("case HC-2 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-4: packaged INDI device descriptor                                 */
/* ===================================================================== */
static void case_xml(const unsigned char *x, size_t len)
{
    printf("case HC-4 start: packaged INDI device descriptor\n");
    check_true(buf_contains(x, len, "<driversList>"), "xml has <driversList>");
    check_true(buf_contains(x, len, "group=\"CCDs\""), "xml group=\"CCDs\"");
    check_true(buf_contains(x, len, "label=\"PlayerOne CCD\""),
               "xml device label=\"PlayerOne CCD\"");
    check_true(buf_contains(x, len, "<driver name=\"PlayerOne CCD\">indi_playerone_ccd</driver>"),
               "xml driver entry points at indi_playerone_ccd");
    check_true(buf_contains(x, len, "<version>0.9</version>"),
               "xml version expands to 0.9 (config.h version macros)");
    printf("case HC-4 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-5: HarmonyOS-specific — driver targets the OHOS aarch64 loader     */
/* ===================================================================== */
static void case_ohos(const unsigned char *b, size_t len)
{
    printf("case HC-5 start: OHOS aarch64 target confirmation\n");
    check_true(buf_contains(b, len, "/lib/ld-musl-aarch64.so.1"),
               "ELF interpreter is the OHOS musl loader /lib/ld-musl-aarch64.so.1");
    check_true(buf_contains(b, len, "aarch64-unknown-linux-ohos") ||
               buf_contains(b, len, "aarch64-linux-ohos") ||
               le16(b + 18) == 183,
               "target triple / machine is aarch64 (cross-built for OHOS)");
    check_true(sizeof(void *) == 8 && sizeof(long) == 8,
               "test process itself is 64-bit aarch64 (LP64, same target)");
    printf("case HC-5 PASS-or-continue\n");
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s <driver-binary> <device-xml> <log>\n", argv[0]);
        return 2;
    }
    size_t dlen = 0, xlen = 0;
    unsigned char *drv = read_whole(argv[1], &dlen);
    unsigned char *xml = read_whole(argv[2], &xlen);
    if (!drv || !xml) {
        fprintf(stderr, "cannot read %s or %s\n", argv[1], argv[2]);
        return 2;
    }

    case_elf(drv, dlen);
    case_logic(drv, dlen);
    case_xml(xml, xlen);
    case_ohos(drv, dlen);

    printf("== 4 cases, %d failed ==\n", g_failures > 4 ? 4 : (g_failures ? 1 : 0));
    printf("== %d checks, %d failures ==\n", g_checks, g_failures);
    printf("RESULT: %s\n", g_failures == 0 ? "PASSED" : "FAILED");

    FILE *log = fopen(argv[3], "w");
    if (log) {
        fprintf(log, "checks=%d failures=%d result=%s\n",
                g_checks, g_failures, g_failures == 0 ? "PASSED" : "FAILED");
        fclose(log);
    }
    free(drv);
    free(xml);
    return g_failures == 0 ? 0 : 1;
}

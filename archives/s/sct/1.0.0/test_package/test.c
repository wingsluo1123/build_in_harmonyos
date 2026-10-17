/*
 * sct 1.0.0 consumer test.
 *
 * Upstream ships no automated test suite, so this test exercises the packaged
 * binary end to end:
 *   1. CLI error contract without an X display (rc=1, diagnostic message).
 *   2. HarmonyOS platform markers of the shipped ELF (aarch64 musl/PIE,
 *      OHOS note, X11/XRandR NEEDED entries, no glibc dependency).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static void check(int cond, const char *msg) {
    if (cond) {
        printf("PASS: %s\n", msg);
    } else {
        fprintf(stderr, "FAIL: %s\n", msg);
        failures++;
    }
}

/* Run a shell command, capture stdout+stderr, return raw wait status parts. */
static int run_capture(const char *cmd, char *out, size_t out_sz, int *exit_code) {
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        if (out_sz) out[0] = '\0';
        *exit_code = -1;
        return -1;
    }
    size_t n = fread(out, 1, out_sz - 1, fp);
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) {
        *exit_code = -1;
        return -1;
    }
    *exit_code = (rc & 0x7f) ? -1 : ((rc >> 8) & 0xff);
    return 0;
}

int main(void) {
    char out[8192];
    char bin[512] = {0};
    int rc = 0;

    /* Locate the packaged binary through the conanrun PATH. */
    if (run_capture("command -v sct 2>/dev/null", out, sizeof(out), &rc) != 0 ||
        rc != 0 || out[0] == '\0') {
        fprintf(stderr, "FAIL: sct binary not found on PATH\n");
        return 1;
    }
    out[strcspn(out, "\r\n")] = '\0';
    snprintf(bin, sizeof(bin), "%s", out);
    printf("sct binary: %s\n", bin);
    check(1, "packaged sct binary is on PATH");

    /* 1. No X display: the tool must fail cleanly, not crash (HarmonyOS PC
     *    images do not run an X server by default). Upstream opens the display
     *    before parsing argv, so the 1000..10000 range clamp is only reachable
     *    with a live X server; conanfile.py covers that path when one exists. */
    run_capture("DISPLAY= sct 3000 2>&1", out, sizeof(out), &rc);
    check(rc == 1, "no DISPLAY -> exit code 1");
    check(strstr(out, "Failed to open X display") != NULL,
          "no DISPLAY -> diagnostic message");

    run_capture("DISPLAY=:65535 sct 2>&1", out, sizeof(out), &rc);
    check(rc == 1, "unreachable DISPLAY -> exit code 1");
    check(strstr(out, ":65535") != NULL,
          "unreachable DISPLAY -> display name echoed");

    run_capture("DISPLAY=:65535 sct not-a-number 2>&1", out, sizeof(out), &rc);
    check(rc == 1, "unreachable DISPLAY + invalid temperature -> clean exit, no crash");

    run_capture("DISPLAY=:65535 sct 1000 2>&1", out, sizeof(out), &rc);
    check(rc == 1, "unreachable DISPLAY + below-range temperature -> clean exit, no crash");

    run_capture("DISPLAY=:65535 sct 10001 2>&1", out, sizeof(out), &rc);
    check(rc == 1, "unreachable DISPLAY + above-range temperature -> clean exit, no crash");

    /* 2. HarmonyOS platform markers. */
    {
        char cmd[1024];
        snprintf(cmd, sizeof(cmd), "readelf -h '%s' 2>&1", bin);
        run_capture(cmd, out, sizeof(out), &rc);
        check(rc == 0, "readelf -h succeeds");
        check(strstr(out, "ELF64") != NULL, "ELF is 64-bit");
        check(strstr(out, "little endian") != NULL, "ELF is little endian");
        check(strstr(out, "AArch64") != NULL, "ELF target is AArch64");
        check(strstr(out, "DYN") != NULL, "ELF is position independent (PIE)");

        snprintf(cmd, sizeof(cmd), "readelf -l '%s' 2>&1", bin);
        run_capture(cmd, out, sizeof(out), &rc);
        check(strstr(out, "/lib/ld-musl-aarch64.so.1") != NULL,
              "interpreter is OHOS musl loader");

        snprintf(cmd, sizeof(cmd), "readelf -d '%s' 2>&1", bin);
        run_capture(cmd, out, sizeof(out), &rc);
        check(strstr(out, "libX11.so.6") != NULL, "NEEDED libX11.so.6");
        check(strstr(out, "libXrandr.so.2") != NULL, "NEEDED libXrandr.so.2");
        check(strstr(out, "libc.so.6") == NULL, "no glibc dependency");

        snprintf(cmd, sizeof(cmd), "readelf -S '%s' 2>&1", bin);
        run_capture(cmd, out, sizeof(out), &rc);
        check(strstr(out, ".note.ohos.ident") != NULL,
              "OHOS identity note present");
    }

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("all sct consumer/platform checks passed\n");
    return 0;
}

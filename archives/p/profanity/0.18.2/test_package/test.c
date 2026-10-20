#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Static verification of the installed profanity binary (no exec).
 *
 * Device constraint (preflight 2026-10-19, two rounds of evidence):
 * executing the installed ELF fails with EPERM ("Operation not permitted",
 * shell exit 126) both from the conan cache and from a copy relocated
 * into the exec-allowed test build tree, while a locally $CC-built helper
 * in that same directory runs fine. This is the OHOS executable-signature
 * gate (same fingerprint as the gammastep wayland-scanner EPERM entry and
 * qastools/1.4.0 P6 HMDFS cache-noexec): chmod/copy/relocate do not help,
 * so test_package verifies the artifact statically instead of running it:
 *  check 1: valid non-empty 64-bit AArch64 ELF (magic + class + e_machine);
 *  check 2: embedded "0.18.2" version string present in the binary image
 *           (baked via config.h PACKAGE_VERSION, the same string
 *           `profanity --version` prints at runtime).
 * Either check fails on a missing/truncated/wrong-arch install, so a pass
 * cannot be faked by an empty or foreign file.
 */
static long file_size(const char *path, FILE **out_fp) {
    FILE *fp = fopen(path, "rb");
    long size;
    if (fp == NULL)
        return -1;
    if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        return -1;
    }
    size = ftell(fp);
    if (out_fp != NULL) {
        rewind(fp);
        *out_fp = fp;
    } else {
        fclose(fp);
    }
    return size;
}

static int contains_bytes(const char *path, const char *needle) {
    FILE *fp = NULL;
    long size = file_size(path, &fp);
    unsigned char *buf;
    size_t nlen, i;
    int found = 0;
    if (size <= 0)
        return 0;
    if (size > (long)(64 * 1024 * 1024)) {
        fclose(fp);
        return 0;
    }
    buf = (unsigned char *)malloc((size_t)size);
    if (buf == NULL) {
        fclose(fp);
        return 0;
    }
    if (fread(buf, 1, (size_t)size, fp) != (size_t)size) {
        free(buf);
        fclose(fp);
        return 0;
    }
    fclose(fp);
    nlen = strlen(needle);
    for (i = 0; i + nlen <= (size_t)size; i++) {
        if (memcmp(buf + i, needle, nlen) == 0) {
            found = 1;
            break;
        }
    }
    free(buf);
    return found;
}

int main(int argc, char *argv[]) {
    const char *profanity_bin = (argc > 1) ? argv[1] : "profanity";
    FILE *fp = NULL;
    long size;
    unsigned char hdr[20];
    unsigned machine;

    printf("Testing profanity binary: %s\n", profanity_bin);

    /* Check 1: valid non-empty 64-bit AArch64 ELF */
    size = file_size(profanity_bin, &fp);
    if (size <= 0 || fp == NULL) {
        fprintf(stderr, "FAIL: cannot open binary '%s'\n", profanity_bin);
        if (fp != NULL)
            fclose(fp);
        return 1;
    }
    if (fread(hdr, 1, sizeof(hdr), fp) != sizeof(hdr)) {
        fprintf(stderr, "FAIL: binary '%s' smaller than ELF header\n", profanity_bin);
        fclose(fp);
        return 1;
    }
    fclose(fp);
    if (!(hdr[0] == 0x7f && hdr[1] == 'E' && hdr[2] == 'L' && hdr[3] == 'F')) {
        fprintf(stderr, "FAIL: '%s' has no ELF magic\n", profanity_bin);
        return 1;
    }
    if (hdr[4] != 2) {
        fprintf(stderr, "FAIL: '%s' is not 64-bit ELF (class=%u)\n",
                profanity_bin, hdr[4]);
        return 1;
    }
    machine = (unsigned)hdr[18] | ((unsigned)hdr[19] << 8);
    if (machine != 183) {
        fprintf(stderr, "FAIL: '%s' e_machine=%u, expected 183 (AArch64)\n",
                profanity_bin, machine);
        return 1;
    }
    printf("PASS: valid 64-bit AArch64 ELF, size %ld bytes\n", size);

    /* Check 2: packaged version string embedded in the image */
    if (!contains_bytes(profanity_bin, "0.18.2")) {
        fprintf(stderr, "FAIL: binary image lacks version string 0.18.2\n");
        return 1;
    }
    printf("PASS: binary image contains version 0.18.2\n");

    printf("All tests passed\n");
    return 0;
}

/*
 * HarmonyOS PC (OHOS aarch64) native checks for the packaged gawkpn.so.
 *
 *   1. OHOS toolchain identity: CMakeToolchain maps os=OHOS to
 *      CMAKE_SYSTEM_NAME=HarmonyOS, which turns on OHOS_TARGET.  On any other
 *      platform the whole test skips.
 *   2. The packaged extension is an AArch64 OHOS shared object (ELF machine
 *      183, ET_DYN) that needs the OHOS musl libc.
 *   3. dlopen() of the packaged extension resolves the gawk entry point
 *      dl_load -- i.e. the artifact can be loaded by the OHOS dynamic loader.
 *   4. The extension still loads after being copied to $HOME/tmp (HMDFS, the
 *      only writable scratch area on HarmonyOS PC, where users install their
 *      AWK extensions); /tmp itself is read-only, as asserted.
 */

#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static const char *extension_dir(void)
{
    const char *dir = getenv("PNC_GAWK_EXTENSION_DIR");
    return dir ? dir : "";
}

/* [1/4] Build-time platform identification. */
static int test_ohos_identity(void)
{
#if defined(OHOS_TARGET)
    printf("  [1/4] OHOS toolchain identity: CMAKE_SYSTEM_NAME=HarmonyOS -> OHOS_TARGET=1\n");
    return 0;
#else
    printf("  [1/4] SKIP: not an OHOS (HarmonyOS) build\n");
    return -1;
#endif
}

/* [2/4] The packaged extension is an AArch64 OHOS shared object. */
static int test_elf_identity(const char *so_path)
{
    Elf64_Ehdr ehdr;
    FILE *fp = fopen(so_path, "rb");
    if (!fp) {
        printf("  [2/4] FAIL: cannot open %s (errno=%d)\n", so_path, errno);
        return 1;
    }
    if (fread(&ehdr, sizeof(ehdr), 1, fp) != 1) {
        printf("  [2/4] FAIL: cannot read ELF header of %s\n", so_path);
        fclose(fp);
        return 1;
    }
    fclose(fp);

    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        printf("  [2/4] FAIL: %s is not an ELF file\n", so_path);
        return 1;
    }
    if (ehdr.e_machine != EM_AARCH64) {
        printf("  [2/4] FAIL: ELF machine=%u, expected EM_AARCH64(%u)\n",
               (unsigned)ehdr.e_machine, (unsigned)EM_AARCH64);
        return 1;
    }
    if (ehdr.e_type != ET_DYN) {
        printf("  [2/4] FAIL: ELF type=%u, expected ET_DYN(%u) shared object\n",
               (unsigned)ehdr.e_type, (unsigned)ET_DYN);
        return 1;
    }
    printf("  [2/4] packaged extension is ELF64 AArch64 ET_DYN: %s\n", so_path);
    return 0;
}

/* [3/4] dlopen() the packaged extension and resolve the gawk entry point. */
static int test_dlopen(const char *so_path, void **handle_out)
{
    void *handle = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        printf("  [3/4] FAIL: dlopen(%s): %s\n", so_path, dlerror());
        return 1;
    }
    if (!dlsym(handle, "dl_load")) {
        printf("  [3/4] FAIL: dl_load symbol missing: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }
    printf("  [3/4] dlopen + dlsym(dl_load) OK\n");
    *handle_out = handle;
    return 0;
}

/* [4/4] /tmp is read-only (HMDFS); the extension loads from $HOME/tmp. */
static int test_home_tmp_load(const char *so_path)
{
    char probe[256];
    snprintf(probe, sizeof(probe), "/tmp/pnc_gawk_probe.%d", (int)getpid());
    int fd = open(probe, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    int saved = errno;
    if (fd >= 0) {
        close(fd);
        remove(probe);
        printf("  [4/4] FAIL: /tmp is writable, expected read-only (HMDFS)\n");
        return 1;
    }
    if (saved != EROFS) {
        printf("  [4/4] FAIL: /tmp open failed with errno=%d, expected EROFS(%d)\n",
               saved, EROFS);
        return 1;
    }

    const char *home = getenv("HOME");
    if (!home)
        home = ".";
    char scratch_dir[256];
    char scratch_so[512];
    snprintf(scratch_dir, sizeof(scratch_dir), "%s/tmp", home);
    mkdir(scratch_dir, 0700);
    snprintf(scratch_so, sizeof(scratch_so), "%s/pnc_gawk_test_%d.so",
             scratch_dir, (int)getpid());

    FILE *src = fopen(so_path, "rb");
    FILE *dst = src ? fopen(scratch_so, "wb") : NULL;
    if (!src || !dst) {
        printf("  [4/4] FAIL: cannot copy extension to %s (errno=%d)\n",
               scratch_so, errno);
        if (src)
            fclose(src);
        if (dst)
            fclose(dst);
        return 1;
    }
    char buf[65536];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), src)) > 0)
        fwrite(buf, 1, n, dst);
    fclose(src);
    fclose(dst);

    void *handle = dlopen(scratch_so, RTLD_NOW | RTLD_LOCAL);
    int ok = handle && dlsym(handle, "dl_load");
    if (handle)
        dlclose(handle);
    remove(scratch_so);

    if (!ok) {
        printf("  [4/4] FAIL: extension does not load from HMDFS path %s\n", scratch_dir);
        return 1;
    }
    printf("  [4/4] /tmp EROFS + extension loads from $HOME/tmp (HMDFS) OK\n");
    return 0;
}

int main(void)
{
    printf("test_ohos: HarmonyOS PC native checks for pnc-gawk\n");

    if (test_ohos_identity() < 0) {
        printf("test_ohos: SKIP (non-OHOS platform)\n");
        return 0;
    }

    const char *dir = extension_dir();
    if (dir[0] == '\0') {
        printf("test_ohos: FAIL: PNC_GAWK_EXTENSION_DIR is not set\n");
        return 1;
    }
    char so_path[512];
    snprintf(so_path, sizeof(so_path), "%s/gawkpn.so", dir);

    int failures = test_elf_identity(so_path);
    void *handle = NULL;
    if (!failures)
        failures += test_dlopen(so_path, &handle);
    if (handle)
        dlclose(handle);
    if (!failures)
        failures += test_home_tmp_load(so_path);

    if (failures) {
        printf("test_ohos: FAIL (%d check(s))\n", failures);
        return 1;
    }
    printf("test_ohos: PASS (4 checks)\n");
    return 0;
}

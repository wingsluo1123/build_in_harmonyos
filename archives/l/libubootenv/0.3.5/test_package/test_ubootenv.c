#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libuboot.h"

/* Consumer test: exercise the public API via dynamic context.
 * No MTD/UBI devices are used — envdevs=NULL means in-memory only.
 */
static int test_version_info(void)
{
    const struct uboot_version_info *ver = libuboot_version_info();
    if (!ver) {
        fprintf(stderr, "FAIL: libuboot_version_info returned NULL\n");
        return 1;
    }
    printf("OK: version = %s (num=0x%08x)\n", ver->version, ver->version_num);
    return 0;
}

static int test_init_exit(void)
{
    struct uboot_ctx *ctx = NULL;
    int ret = libuboot_initialize(&ctx, NULL);
    if (ret != 0 || ctx == NULL) {
        fprintf(stderr, "FAIL: libuboot_initialize ret=%d ctx=%p\n", ret, (void*)ctx);
        return 1;
    }
    printf("OK: initialize with NULL devices\n");
    libuboot_exit(ctx);
    printf("OK: exit\n");
    return 0;
}

static int test_env_set_get(void)
{
    struct uboot_ctx *ctx = NULL;
    int ret = libuboot_initialize(&ctx, NULL);
    if (ret != 0 || ctx == NULL) {
        fprintf(stderr, "FAIL: init ret=%d\n", ret);
        return 1;
    }

    ret = libuboot_set_env(ctx, "testvar", "testvalue");
    if (ret != 0) {
        fprintf(stderr, "FAIL: set_env ret=%d\n", ret);
        libuboot_exit(ctx);
        return 1;
    }

    char *val = libuboot_get_env(ctx, "testvar");
    if (!val || strcmp(val, "testvalue") != 0) {
        fprintf(stderr, "FAIL: get_env returned '%s'\n", val ? val : "(NULL)");
        free(val);
        libuboot_exit(ctx);
        return 1;
    }
    printf("OK: set/get roundtrip '%s'='%s'\n", "testvar", val);
    free(val);

    /* Delete by setting NULL */
    ret = libuboot_set_env(ctx, "testvar", NULL);
    if (ret != 0) {
        fprintf(stderr, "FAIL: delete ret=%d\n", ret);
        libuboot_exit(ctx);
        return 1;
    }
    val = libuboot_get_env(ctx, "testvar");
    if (val != NULL) {
        fprintf(stderr, "FAIL: get after delete returned '%s'\n", val);
        free(val);
        libuboot_exit(ctx);
        return 1;
    }
    printf("OK: delete by setting NULL\n");

    libuboot_exit(ctx);
    return 0;
}

static int test_iterator(void)
{
    struct uboot_ctx *ctx = NULL;
    int ret = libuboot_initialize(&ctx, NULL);
    if (ret != 0 || ctx == NULL) return 1;

    libuboot_set_env(ctx, "alpha", "1");
    libuboot_set_env(ctx, "bravo", "2");
    libuboot_set_env(ctx, "charlie", "3");

    int count = 0;
    void *entry = NULL;
    while ((entry = libuboot_iterator(ctx, entry)) != NULL) {
        const char *name = libuboot_getname(entry);
        const char *value = libuboot_getvalue(entry);
        printf("  iter: %s = %s\n", name ? name : "(NULL)", value ? value : "(NULL)");
        count++;
    }

    libuboot_exit(ctx);
    if (count < 3) {
        fprintf(stderr, "FAIL: expected >=3 entries, got %d\n", count);
        return 1;
    }
    printf("OK: iterator returned %d entries\n", count);
    return 0;
}

int main(int argc, char **argv)
{
    int failures = 0;
    failures += test_version_info();
    failures += test_init_exit();
    failures += test_env_set_get();
    failures += test_iterator();

    if (failures > 0) {
        fprintf(stderr, "FAILED: %d test(s) failed\n", failures);
        return 1;
    }
    printf("ALL TESTS PASSED\n");
    return 0;
}

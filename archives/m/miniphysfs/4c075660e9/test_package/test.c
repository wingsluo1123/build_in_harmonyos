/*
 * test.c — Conan L1 consumer test + HarmonyOS-specific behavior test.
 *
 * 调用当前库（miniphysfs/4c075660e9 单头文件 PhysFS）：
 *   - 版本查询（PHYSFS_getLinkedVersion / PHYSFS_getVersion）
 *   - 初始化/反初始化（PHYSFS_init / PHYSFS_deinit）
 *   - 平台路径查询（PHYSFS_getBaseDir / PHYSFS_getUserDir / PHYSFS_getDirSeparator）
 *   - 文件系统真实写入/读取/枚举（PHYSFS_mkdir / PHYSFS_write / PHYSFS_read / PHYSFS_enumerateFiles）
 *   - 符号链接策略（PHYSFS_permitSymbolicLinks）
 *
 * 在 OHOS 目标上验证：库能初始化、能解析宿主平台基础目录、能通过
 * 真实文件系统做写入-读取-枚举闭环，均返回成功。
 */
#define PHYSFS_IMPL
#define PHYSFS_PLATFORM_IMPL
#include "miniphysfs.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, what)                                              \
    do {                                                               \
        if (cond) {                                                    \
            printf("PASS: %s\n", what);                                \
        } else {                                                       \
            printf("FAIL: %s (%s)\n", what,                             \
                   PHYSFS_getErrorByCode(PHYSFS_getLastErrorCode()));   \
            failures++;                                                \
        }                                                              \
    } while (0)

int main(void)
{
    PHYSFS_Version linked;

    PHYSFS_getLinkedVersion(&linked);
    printf("linked PhysFS %u.%u.%u\n",
           (unsigned)linked.major, (unsigned)linked.minor, (unsigned)linked.patch);
    CHECK(linked.major >= 3, "PHYSFS_getLinkedVersion reports major >= 3");

    CHECK(PHYSFS_init("test_miniphysfs") != 0, "PHYSFS_init");
    /* PHYSFS_permitSymbolicLinks 返回 void（策略设置型 API），仅调用验证不崩溃。 */
    PHYSFS_permitSymbolicLinks(0);

    /* 平台路径：OHOS 宿主必须有基础目录与用户目录。 */
    {
        const char *base = PHYSFS_getBaseDir();
        const char *user = PHYSFS_getUserDir();
        const char *sep = PHYSFS_getDirSeparator();
        CHECK(base != NULL && *base != '\0', "PHYSFS_getBaseDir non-empty");
        CHECK(user != NULL && *user != '\0', "PHYSFS_getUserDir non-empty");
        CHECK(sep != NULL && *sep != '\0', "PHYSFS_getDirSeparator non-empty");
        printf("  basedir=%s userdir=%s sep=%s\n", base, user, sep);
    }

    /* 真实文件系统闭环：setWriteDir → mkdir → write → 枚举 → read → delete。 */
    {
        const char *dir = "ohos-test-dir";
        const char *file = "ohos-test-dir/hello.txt";
        const char payload[] = "miniphysfs-on-ohos\n";
        char buf[64];

        /* PhysFS 写入类操作必须先设置写入目录（否则报 "write directory is not set"）；
           读取/枚举走搜索路径，需把写入目录加入搜索路径。 */
        const char *base = PHYSFS_getBaseDir();
        CHECK(PHYSFS_setWriteDir(base) != 0, "PHYSFS_setWriteDir(base)");
        CHECK(PHYSFS_addToSearchPath(base, 1) != 0, "PHYSFS_addToSearchPath(base, 1)");

        CHECK(PHYSFS_mkdir(dir) != 0, "PHYSFS_mkdir(ohos-test-dir)");

        PHYSFS_File *fh = PHYSFS_openWrite(file);
        CHECK(fh != NULL, "PHYSFS_openWrite(hello.txt)");
        if (fh) {
            PHYSFS_uint64 n = PHYSFS_write(fh, payload, 1, sizeof(payload) - 1);
            CHECK(n == sizeof(payload) - 1, "PHYSFS_write full payload");
            CHECK(PHYSFS_close(fh) != 0, "PHYSFS_close(write)");
        }

        char **listing = PHYSFS_enumerateFiles(dir);
        CHECK(listing != NULL, "PHYSFS_enumerateFiles");
        if (listing) {
            int found = 0;
            char **it;
            for (it = listing; *it != NULL; it++) {
                printf("  entry: %s\n", *it);
                if (strcmp(*it, "hello.txt") == 0) found = 1;
            }
            CHECK(found == 1, "enumerate finds hello.txt");
            PHYSFS_freeList(listing);
        }

        fh = PHYSFS_openRead(file);
        CHECK(fh != NULL, "PHYSFS_openRead(hello.txt)");
        if (fh) {
            PHYSFS_uint64 n = PHYSFS_read(fh, buf, 1, sizeof(buf) - 1);
            buf[n] = '\0';
            CHECK(n == sizeof(payload) - 1, "PHYSFS_read full payload");
            CHECK(memcmp(buf, payload, sizeof(payload) - 1) == 0,
                  "read-back payload identical");
            CHECK(PHYSFS_close(fh) != 0, "PHYSFS_close(read)");
        }

        CHECK(PHYSFS_delete(file) != 0, "PHYSFS_delete(hello.txt)");
        CHECK(PHYSFS_delete(dir) != 0, "PHYSFS_delete(ohos-test-dir)");
    }

    CHECK(PHYSFS_deinit() != 0, "PHYSFS_deinit");

    if (failures > 0) {
        printf("RESULT: %d FAILURES\n", failures);
        return 1;
    }
    printf("RESULT: all OHOS behavior checks passed\n");
    return 0;
}
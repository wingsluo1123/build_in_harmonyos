/*
 * test_e2e.c — miniphysfs 端到端消费者用例（rule12 补全）
 *
 * 真正跑通 miniphysfs 核心流程，在 OHOS 目标上验证库 API 的实际行为：
 *   1. PHYSFS_init 初始化成功；
 *   2. 创建真实数据目录并写入真实文件（遵守 $TMPDIR / $HOME/tmp 平台约束，
 *      不假定 /tmp 可写，写入前先删除可能残留的旧文件 —— HMDfs 软链接先删后建规则）；
 *   3. PHYSFS_mount 挂载该真实目录；
 *   4. PHYSFS_enumerateFiles 枚举挂载点，确认能列出真实写入的文件；
 *   5. PHYSFS_openRead + PHYSFS_readBytes 打开读取，校验读回内容与写入内容逐字一致；
 *   6. PHYSFS_close / PHYSFS_unmount / PHYSFS_deinit 清理，整个进程 exit 0。
 *
 * 上述步骤全部通过真实文件系统 + 库 API 完成（非纯内存断言、非仅打印字符串）。
 */
#define PHYSFS_IMPL
#define PHYSFS_PLATFORM_IMPL
#include "miniphysfs.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failures = 0;

#define STEP(cond, what)                                                    \
    do {                                                                    \
        if (cond) {                                                         \
            printf("PASS: %s\n", what);                                     \
        } else {                                                            \
            printf("FAIL: %s (%s)\n", what,                                 \
                   PHYSFS_getErrorByCode(PHYSFS_getLastErrorCode()));       \
            failures++;                                                     \
        }                                                                   \
    } while (0)

/* 平台约束：临时目录取 $TMPDIR，缺省回退 $HOME/tmp（不假定 /tmp 可写）。 */
static void get_work_base(char *buf, size_t size)
{
    const char *tmpdir = getenv("TMPDIR");
    if (tmpdir && *tmpdir) {
        snprintf(buf, size, "%s", tmpdir);
        return;
    }
    const char *home = getenv("HOME");
    if (home && *home) {
        snprintf(buf, size, "%s/tmp", home);
        return;
    }
    snprintf(buf, size, "/storage/Users/currentUser/tmp");
}

int main(void)
{
    char base[512];
    char mountdir[600];
    char mountfile[600];
    char readfile[600];
    const char expected[] = "miniphysfs-e2e-on-ohos: hello from a real mounted file\n";
    char readbuf[256];
    char **listing;
    int found = 0;
    char **it;
    PHYSFS_File *ph;
    FILE *sio;
    PHYSFS_uint64 n;

    get_work_base(base, sizeof(base));

    /* ---- 准备真实数据目录与文件（真实文件系统写入） ---- */
    snprintf(mountdir, sizeof(mountdir), "%s/miniphysfs-e2e-mount-%ld",
             base, (long)getpid());
    snprintf(mountfile, sizeof(mountfile), "%s/greeting.txt", mountdir);

    /* HMDfs：先删后建，避免残留/软链接覆盖问题 */
    unlink(mountfile);
    remove(mountdir);
    STEP(mkdir(mountdir, 0700) == 0, "mkdir real mount dir");

    sio = fopen(mountfile, "wb");
    STEP(sio != NULL, "fopen real data file for writing");
    if (sio) {
        size_t w = fwrite(expected, 1, sizeof(expected) - 1, sio);
        STEP(w == sizeof(expected) - 1, "fwrite real payload");
        fclose(sio);
    }

    /* ---- 库流程起点 ---- */
    STEP(PHYSFS_init("test_miniphysfs_e2e") != 0, "PHYSFS_init");

    /* 挂载真实目录到虚拟根 /（appendToPath=1） */
    STEP(PHYSFS_mount(mountdir, "/", 1) != 0, "PHYSFS_mount(real dir, /, append=1)");

    /* 枚举挂载点，确认能看到真实写入的 greeting.txt */
    listing = PHYSFS_enumerateFiles("/");
    STEP(listing != NULL, "PHYSFS_enumerateFiles(/)");
    if (listing) {
        for (it = listing; *it != NULL; it++) {
            printf("  entry: %s\n", *it);
            if (strcmp(*it, "greeting.txt") == 0) found = 1;
        }
        STEP(found == 1, "enumerate lists greeting.txt from real dir");
        PHYSFS_freeList(listing);
    }

    /* 通过库 API 打开并读取挂载文件，逐字校验内容 */
    snprintf(readfile, sizeof(readfile), "/greeting.txt");
    ph = PHYSFS_openRead(readfile);
    STEP(ph != NULL, "PHYSFS_openRead(/greeting.txt)");
    if (ph) {
        memset(readbuf, 0, sizeof(readbuf));
        n = PHYSFS_readBytes(ph, readbuf, sizeof(expected) - 1);
        STEP(n == (PHYSFS_uint64)(sizeof(expected) - 1),
             "PHYSFS_readBytes read full payload length");
        STEP(memcmp(readbuf, expected, sizeof(expected) - 1) == 0,
             "read-back content identical to written payload");
        printf("  read-back: %.40s...\n", readbuf);
        STEP(PHYSFS_close(ph) != 0, "PHYSFS_close(read handle)");
    }

    /* 清理：unmount + deinit + 删除临时真实文件 */
    STEP(PHYSFS_unmount(mountdir) != 0, "PHYSFS_unmount(real dir)");
    STEP(PHYSFS_deinit() != 0, "PHYSFS_deinit");

    unlink(mountfile);
    remove(mountdir);

    if (failures > 0) {
        printf("RESULT: %d FAILURES\n", failures);
        return 1;
    }
    printf("RESULT: e2e consumer test passed (init/mount/enumerate/read/verify/cleanup)\n");
    return 0;
}
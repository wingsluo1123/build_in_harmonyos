/*
 * test_vlc.c — libvlc 3.0.23_2 真实调用测试
 *
 * 调用 libvlc 公共 API：
 *   - libvlc_get_version()：版本字符串非空且以 "3.0" 开头
 *   - libvlc_new(0, NULL) + libvlc_release()：实例创建/销毁
 *     （内部初始化线程系统/插件缓存，验证 libc 适配的完整性）
 *   - libvlc_get_compiler()：编译器串非空
 *
 * 鸿蒙特有断言（平台前提 + 插件树运行时完整性）：
 *   - 编译目标为 HarmonyOS（__OHOS__ 已定义，OHOS clang 工具链注入）
 *   - libc 为 musl（无 __GLIBC__）——vlc 的 POSIX 适配（posix_close/
 *     pthread_cancel 能力宏 fallback）依赖此前提
 *   - VLC_PLUGIN_PATH 已注入且插件树（lib/vlc/plugins）存在 *_plugin.so
 *     ——libvlc_new 的插件发现是 OHOS 上动态加载适配的关键面
 *
 * 退出码 0 = 全部断言通过；非 0 = 失败。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dirent.h>
#include <sys/stat.h>
#include <vlc/vlc.h>

static int failures = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL: %s\n", (msg));                   \
            failures++;                                    \
        } else {                                           \
            printf("PASS: %s\n", (msg));                   \
        }                                                  \
    } while (0)

static int count_plugins(const char *dir)
{
    DIR *d = opendir(dir);
    int n = 0;
    if (d == NULL) {
        return -1;
    }
    struct dirent *e;
    while ((e = readdir(d)) != NULL) {
        if (strstr(e->d_name, "_plugin.so") != NULL) {
            n++;
        } else if (e->d_name[0] != '.') {
            /* vlc 插件按类别子目录组织（access/ codec/ filter/ ...），递归计数 */
            char path[4096];
            struct stat st;
            if (snprintf(path, sizeof(path), "%s/%s", dir, e->d_name)
                    >= (int)sizeof(path)) {
                continue;
            }
            if (stat(path, &st) == 0 && S_ISDIR(st.st_mode)) {
                n += count_plugins(path);
            }
        }
    }
    closedir(d);
    return n;
}

int main(void)
{
    /* 1. 版本字符串 */
    const char *ver = libvlc_get_version();
    CHECK(ver != NULL && ver[0] != '\0', "libvlc_get_version() returns non-empty string");
    CHECK(ver != NULL && strncmp(ver, "3.0", 3) == 0, "libvlc_get_version() starts with 3.0");

    /* 2. 编译器串 */
    const char *cc = libvlc_get_compiler();
    CHECK(cc != NULL && cc[0] != '\0', "libvlc_get_compiler() returns non-empty string");

    /* 3. 实例创建/销毁（初始化线程系统 + 插件缓存） */
    libvlc_instance_t *vlc = libvlc_new(0, NULL);
    CHECK(vlc != NULL, "libvlc_new(0, NULL) returns non-NULL instance");
    if (vlc != NULL) {
        libvlc_release(vlc);
        printf("PASS: libvlc_release() completed\n");
    }

    /* 4. 鸿蒙特有：编译目标平台前提（OHOS 工具链定义 __OHOS__） */
#ifdef __OHOS__
    printf("PASS: compiled for HarmonyOS (__OHOS__ defined)\n");
#else
    printf("FAIL: NOT compiled for HarmonyOS (__OHOS__ undefined)\n");
    failures++;
#endif

    /* 5. 鸿蒙特有：libc 为 musl（OHOS musl 无 glibc；vlc 的
     *    posix_close/pthread_cancel 能力宏 fallback 依赖此前提） */
#ifndef __GLIBC__
    printf("PASS: libc is musl (__GLIBC__ undefined)\n");
#else
    printf("FAIL: libc is glibc (__GLIBC__ defined) — not the OHOS musl premise\n");
    failures++;
#endif

    /* 6. 鸿蒙特有：插件树运行时完整性（libvlc_new 的插件发现面） */
    const char *pp = getenv("VLC_PLUGIN_PATH");
    if (pp == NULL || pp[0] == '\0') {
        printf("FAIL: VLC_PLUGIN_PATH is not set (plugin discovery premise missing)\n");
        failures++;
    } else {
        int n = count_plugins(pp);
        printf("PASS: VLC_PLUGIN_PATH set (%s)\n", pp);
        CHECK(n > 0, "plugin tree contains *_plugin.so files (dynamic loading intact)");
    }

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
    }
    return failures;
}

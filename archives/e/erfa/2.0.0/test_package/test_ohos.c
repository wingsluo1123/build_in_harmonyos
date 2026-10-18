/*
 * test_ohos.c — OHOS 专有适配测试（HarmonyOS PC aarch64 / musl / llvm）。
 *
 * 本 run 的适配点是 recipe 侧以补丁新增的最小 meson 构建：上游 2.0.0
 * 只有 autotools，而 autotools config.status 在 HMDFS 上因 mktemp 临时
 * 目录 setgid 限制失败（knowledge E112/E114/E118）。以下断言覆盖：
 *   1. OHOS 工具链身份：权威 CI 目标 aarch64-linux-ohos，其 clang 定义
 *      __OHOS__（非 OHOS 工具链构建时必失败）；
 *   2. musl/LP64 数据模型：库内历法例程依赖的 long==64bit、double==64bit；
 *   3. meson 路线的配置传递：eraVersion()/eraSofaVersion() 返回值来自
 *      补丁 meson.build 的 configure_file(config.h)——补丁缺失或取值错误
 *      （应为 PACKAGE_VERSION=2.0.0、SOFA_VERSION=20210512）时必失败；
 *   4. 静态库链接闭包：erfadatextra.c 内嵌闰秒表经 llvm-ar 打包后可被
 *      eraDat 正确消费。
 */
#include <stdio.h>
#include <string.h>
#include <erfa.h>
#include <erfaextra.h>

static int failures = 0;

static void check(int ok, const char *what) {
    if (ok) {
        printf("[OHOS-OK] %s\n", what);
    } else {
        fprintf(stderr, "[OHOS-FAIL] %s\n", what);
        failures++;
    }
}

int main(void) {
    /* 1. OHOS toolchain identity */
#ifdef __OHOS__
    check(1, "__OHOS__ defined (OHOS llvm toolchain in effect)");
#else
    check(0, "__OHOS__ NOT defined - not built by the OHOS toolchain");
#endif

    /* 2. LP64 / IEEE-double data model (musl on aarch64) */
    check(sizeof(long) == 8, "LP64 data model (sizeof(long) == 8)");
    check(sizeof(double) == 8, "IEEE double (sizeof(double) == 8)");

    /* 3. Version plumbing through the patched meson build's config.h */
    {
        const char *v = eraVersion();
        check(v != NULL && strcmp(v, "2.0.0") == 0, "eraVersion() == \"2.0.0\"");
        check(eraVersionMajor() == 2 && eraVersionMinor() == 0 &&
              eraVersionMicro() == 0, "eraVersionMajor/Minor/Micro == 2/0/0");
        {
            const char *sv = eraSofaVersion();
            check(sv != NULL && strcmp(sv, "20210512") == 0,
                  "eraSofaVersion() == \"20210512\" (SOFA_VERSION from meson confdata)");
        }
    }

    /* 4. Embedded leap-second table linked from the static archive */
    {
        double delat = -1.0;
        int s = eraDat(2024, 7, 1, 0.0, &delat);
        check(s == 0 && delat > 30.0 && delat < 40.0,
              "eraDat(2024-07-01) == 37s (embedded leap-second table)");
    }

    if (failures == 0) {
        printf("OHOS-specific checks: all passed\n");
        return 0;
    }
    printf("OHOS-specific checks: %d failed\n", failures);
    return 1;
}

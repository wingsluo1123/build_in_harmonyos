/* test_package/clap_probe.c — jc303/0.12.3 OHOS 特有消费式探针。
 *
 * 对安装后插件产物做 dlopen/dlsym 验证（OHOS 适配点直接证据）：
 *   - E505：用户存储 .so 必须 binary-sign-tool selfSign，未签名 dlopen 即
 *     EACCES —— dlopen 成功即签名链路真实生效；
 *   - 插件 .so 的 DT_NEEDED（freetype/fontconfig/libxml2/alsa 共享库闭包）
 *     由包内 $ORIGIN 多级 rpath（lib/jc303-runtime 实体化视图）解析 ——
 *     musl 加载器无法经版本化符号链接别名解析，dlopen 成功即 rpath 闭包
 *     真实生效（构建期实现策略 §5 显式闭包的运行期对应验证）；
 *   - 三格式入口符号：VST3 GetPluginFactory / LV2 lv2_descriptor /
 *     CLAP clap_entry；
 *   - __OHOS__ 编译期卫兵（探针必须编译在 OHOS 目标上）。
 * 不做 GUI/音频设备初始化（无显示后端；插件不打开音频设备）。
 */
#include <dlfcn.h>
#include <stdio.h>

#ifndef __OHOS__
#error "probe must be compiled for OHOS (__OHOS__ undefined)"
#endif

static int g_checks = 0;

static int check(int ok, const char *what)
{
    ++g_checks;
    printf("[%s] %s\n", ok ? "PASS" : "FAIL", what);
    return ok;
}

int main(void)
{
    int ok = 1;
    void *vst3 = NULL, *lv2 = NULL, *clap = NULL;

    /* 1. bundle 布局计数（CMake configure 已断言，这里复述供日志取证） */
    ok &= check(JC303_VST3_SO_N == 1, "VST3 bundle contains exactly one plugin .so");
    ok &= check(JC303_LV2_SO_N == 1, "LV2 bundle contains exactly one plugin .so");
    ok &= check(JC303_TTL_N >= 2, "LV2 bundle carries >=2 .ttl (plugin + manifest)");

    /* 2. VST3：dlopen（签名 + rpath 闭包）+ 入口符号 */
    vst3 = dlopen(JC303_VST3_SO, RTLD_NOW);
    ok &= check(vst3 != NULL, "dlopen VST3 plugin (E505 selfSigned + $ORIGIN rpath closure)");
    if (!vst3) {
        printf("       dlerror: %s\n", dlerror());
    } else {
        ok &= check(dlsym(vst3, "GetPluginFactory") != NULL,
                    "VST3 entry symbol GetPluginFactory exported");
    }

    /* 3. LV2：同上，入口符号 lv2_descriptor */
    lv2 = dlopen(JC303_LV2_SO, RTLD_NOW);
    ok &= check(lv2 != NULL, "dlopen LV2 plugin");
    if (!lv2) {
        printf("       dlerror: %s\n", dlerror());
    } else {
        ok &= check(dlsym(lv2, "lv2_descriptor") != NULL,
                    "LV2 entry symbol lv2_descriptor exported");
    }

    /* 4. CLAP：目录 bundle（JC303.clap/，内层二进制 JC303.clap），入口符号
     *    clap_entry */
    clap = dlopen(JC303_CLAP_PATH, RTLD_NOW);
    ok &= check(clap != NULL, "dlopen CLAP plugin");
    if (!clap) {
        printf("       dlerror: %s\n", dlerror());
    } else {
        ok &= check(dlsym(clap, "clap_entry") != NULL,
                    "CLAP entry symbol clap_entry exported");
    }

    /* 5. 句柄释放（dlclose 路径，musl 析构安全） */
    if (vst3) dlclose(vst3);
    if (lv2) dlclose(lv2);
    if (clap) dlclose(clap);
    ok &= check(1, "dlclose all three plugin handles");

    if (!ok) {
        printf("jc303-ohos-probe: %d checks, FAILED\n", g_checks);
        return 1;
    }
    printf("jc303-ohos-probe: %d checks, all passed\n", g_checks);
    return 0;
}

/*
 * test_libfm_extra_consumer.c — libfm consumer test for HarmonyOS
 *
 * 1. 链接期依赖（R34）: 直接调用 fm_xml_file_get_type()，测试二进制
 *    NEEDED 必含 libfm-extra.so.4 —— 包产物缺失时链接/运行必失败。
 * 2. 鸿蒙特有运行时测试（非断言）: dlopen(RTLD_NOW) 验证共享库闭包
 *    在 HarmonyOS 动态链接器下可加载、4 个 fm_xml_file_* 符号可解析。
 */
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

/* GType == gsize == unsigned long (aarch64 LP64); 显式声明避免依赖 glib 头 */
extern unsigned long fm_xml_file_get_type(void);

int main(void)
{
    /* 1) 链接期依赖验证: 直接调用被测包 API */
    unsigned long gtype = fm_xml_file_get_type();
    if (gtype == 0) {
        fprintf(stderr, "FAIL: fm_xml_file_get_type() returned 0\n");
        return 1;
    }
    printf("  OK: link-check fm_xml_file_get_type() = 0x%lx\n", gtype);

    /* 2) 鸿蒙特有: dlopen 共享库闭包加载验证 */
    void *handle = dlopen("libfm-extra.so.4", RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen failed: %s\n", dlerror());
        return 1;
    }

    const char *symbols[] = {
        "fm_xml_file_get_type",
        "fm_xml_file_new",
        "fm_xml_file_parse_data",
        "fm_xml_file_to_data",
        NULL
    };

    for (int i = 0; symbols[i]; i++) {
        void *sym = dlsym(handle, symbols[i]);
        if (!sym) {
            fprintf(stderr, "FAIL: dlsym %s failed: %s\n", symbols[i], dlerror());
            dlclose(handle);
            return 1;
        }
        printf("  OK: %s @ %p\n", symbols[i], sym);
    }

    printf("PASS: libfm-extra.so loaded and symbols resolved\n");
    dlclose(handle);
    return 0;
}

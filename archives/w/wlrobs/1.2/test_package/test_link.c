/*
 * test_package/test_link.c — libwlrobs.so 链接期 ABI 探针（鸿蒙消费者用例）。
 *
 * 以消费者身份引用 OBS 插件契约入口 obs_module_load 并与打包产物链接，
 * 由链接器解析符号——证明打包插件的动态符号表导出了 OBS 插件 ABI。
 * 注意：不在运行期 exec/dlopen 该二进制——DT_NEEDED 会要求加载
 * /storage 用户区的 .so，而本平台对未签名 ELF 的 dlopen/动态映射一律
 * EACCES（E258/E077：binary-sign-tool 签名是唯一通行证，依赖包整链
 * 签名不属本包职责）。运行期验证由 test_elf.sh 的 ELF 结构断言承担。
 */
#include <stdio.h>

extern void obs_module_load(void);

int main(void) {
    /* 只取地址验证可解析，不调用（无 OBS 运行时上下文） */
    void *entry = (void *)&obs_module_load;
    if (!entry) {
        fprintf(stderr, "obs_module_load unresolved\n");
        return 1;
    }
    printf("WLROBS_LINK_ABI_OK %p\n", entry);
    return 0;
}

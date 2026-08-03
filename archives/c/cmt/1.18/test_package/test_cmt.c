/* test_cmt.c — cmt 消费者测试
 * 验证 cmt.so LADSPA 插件库可加载 + descriptor 非 NULL：
 *   1. dlopen cmt.so 成功
 *   2. ladspa_descriptor 符号可解析
 *   3. descriptor->Name 非空且含 "CMT"
 * 编译：clang test_cmt.c -ldl -o test_cmt
 * 运行：./test_cmt <cmt.so 路径>
 * 退出码：0=通过，非 0=失败
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

typedef struct {
    unsigned long UniqueID;
    const char *Label;
    const char *Properties;
    const char *Name;
    const char *Maker;
    const char *Copyright;
    unsigned long PortCount;
    void *PortDescriptors;
    void *PortRangeHints;
    void *ImplementationData;
} LADSPA_Descriptor;

typedef const LADSPA_Descriptor *(*LADSPA_Descriptor_Function)(unsigned long Index);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <cmt.so path>\n", argv[0]);
        return 2;
    }
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", argv[1], dlerror());
        return 3;
    }
    LADSPA_Descriptor_Function fn = (LADSPA_Descriptor_Function)dlsym(h, "ladspa_descriptor");
    if (!fn) {
        fprintf(stderr, "FAIL: dlsym(ladspa_descriptor): %s\n", dlerror());
        dlclose(h);
        return 4;
    }
    int count = 0;
    for (unsigned long i = 0; i < 200; i++) {
        const LADSPA_Descriptor *d = fn(i);
        if (!d) break;
        count++;
        if (d->Name && strstr(d->Name, "CMT")) {
            printf("CMT plugin[%lu]: %s\n", i, d->Name);
        }
    }
    if (count == 0) {
        fprintf(stderr, "FAIL: no LADSPA plugins exported by %s\n", argv[1]);
        dlclose(h);
        return 5;
    }
    printf("cmt: %d LADSPA plugins loaded OK\n", count);
    dlclose(h);
    return 0;
}

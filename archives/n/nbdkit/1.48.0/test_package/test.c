/*
 * test_nbdkit_consumer.c — nbdkit 1.48.0 消费者验证源
 *
 * 模拟依赖 nbdkit 服务器进程的上层组件（如 libnbd 测试套件）：
 *   1. 使用公开插件 ABI 头文件契约 dlopen 安装的插件，调用 plugin_init()
 *      并读取公开字段（_struct_size / name / version）。
 *   2. 通过公开插件 API 验证插件可加载、标识字段可读。
 *
 * 只使用 nbdkit 安装产物（插件 .so + 公开 ABI 契约），不包含库私有头文件。
 * 由 test_package/conanfile.py 的 test() 编译并运行。
 */
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

/* 公开插件 ABI 前缀（与安装的 nbdkit-plugin.h 契约一致） */
struct nbdkit_plugin {
    int _struct_size;
    void *reserved;
    const char *name;
    const char *longname;
    const char *version;
    void *load;
    void *unload;
    void *config;
    void *config_help;
    void *config_complete;
    void *open;
    void *close;
    void *get_size;
    void *pread;
    void *pwrite;
    void *trim;
    void *zero;
    void *flush;
    void *can_write;
    void *can_flush;
    void *can_trim;
    void *can_zero;
    void *thread_model;
    void *errno_is_preserved;
    void *cache;
    void *extents;
    void *pread_structured;
    void *dump_plugin;
    void *get_ready;
    void *after_fork;
    void *preconnect;
    void *magic_config_key;
    void *get_ready_again;
    void *list_exports;
    void *default_export;
    void *export_description;
    void *block_size;
};

typedef struct nbdkit_plugin *(*plugin_init_fn)(void);

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <plugin.so>\n", argv[0]);
        return 2;
    }

    void *h = dlopen(argv[1], RTLD_NOW);
    if (!h) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    plugin_init_fn init = (plugin_init_fn)dlsym(h, "plugin_init");
    if (!init) {
        fprintf(stderr, "dlsym plugin_init failed: %s\n", dlerror());
        return 1;
    }

    struct nbdkit_plugin *p = init();
    if (!p || p->_struct_size <= 0 || !p->name) {
        fprintf(stderr, "plugin_init returned invalid struct\n");
        return 1;
    }

    printf("consumer loaded plugin: name=%s struct_size=%d",
           p->name, p->_struct_size);
    if (p->version)
        printf(" version=%s", p->version);
    printf("\n");

    if (strcmp(p->name, "example1") != 0) {
        fprintf(stderr, "unexpected plugin name: %s\n", p->name);
        return 1;
    }

    dlclose(h);
    return 0;
}

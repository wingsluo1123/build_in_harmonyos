/* test.c — abiword-plugin-docbook 3.0.8 L1 smoke test
 *
 * Verifies the AbiWord plugin ABI symbols of the docbook plugin .so:
 * abi_plugin_register/unregister/supports_version, and that
 * abi_plugin_supports_version(3,0,0) returns 1.
 *
 * 审查意见(R34)修复: 不在独立加载失败时直接 PASS。
 * - dlopen 成功路径: 真实调用 abi_plugin_supports_version(3,0,0) 断言 ==1,
 *   dlsym 断言 register/unregister 存在 (真实 API 调用)。
 * - dlopen 失败路径(缺 AbiWord 宿主符号, 插件架构预期): 改用
 *   readelf --dyn-syms 校验导出符号并断言 (审查认可的静态校验路径),
 *   readelf 也找不到符号时返回非零 FAIL。
 *
 * Compile with -DTARGET_SO=<path-to-docbook.so> passed from CMake.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <unistd.h>

typedef int (*supports_version_fn)(unsigned, unsigned, unsigned);
typedef int (*register_fn)(void);
typedef int (*unregister_fn)(void);

/* 查找 readelf: 优先 hnp 工具链绝对路径, 否则裸名(由 popen 的 shell 按
 * PATH 搜索——裸名不能 [ -x ] 检查当前目录, 但 C 的 popen 走 shell PATH)。 */
static const char *find_readelf(void) {
    static const char *cands[] = {
        "/data/service/hnp/bin/readelf",
        "/data/service/hnp/bin/llvm-readelf",
        NULL,
    };
    for (int i = 0; cands[i]; i++) {
        if (access(cands[i], X_OK) == 0) {
            return cands[i];
        }
    }
    return "readelf"; /* fallback: shell PATH 搜索 */
}

/* 用 readelf --dyn-syms 校验三个 ABI 导出符号。返回 0=通过, 1=失败。 */
static int verify_exports_via_readelf(const char *so_path) {
    const char *re = find_readelf();
    char cmd[1536];
    int n = snprintf(cmd, sizeof(cmd), "%s --dyn-syms -W \"%s\" 2>/dev/null",
                     re, so_path);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command too long\n");
        return 1;
    }
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run readelf (%s)\n", re);
        return 1;
    }
    char line[1024];
    int found_reg = 0, found_unreg = 0, found_sup = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "abi_plugin_register"))      found_reg = 1;
        if (strstr(line, "abi_plugin_unregister"))    found_unreg = 1;
        if (strstr(line, "abi_plugin_supports_version")) found_sup = 1;
    }
    pclose(fp);

    if (found_reg && found_unreg && found_sup) {
        printf("[ok] readelf --dyn-syms verified exports: "
               "abi_plugin_register / unregister / supports_version\n");
        return 0;
    }
    fprintf(stderr, "FAIL: readelf --dyn-syms missing ABI symbols "
            "(register=%d unregister=%d supports_version=%d)\n",
            found_reg, found_unreg, found_sup);
    return 1;
}

int main(void) {
    const char *so_path = TARGET_SO;

    /* AbiWord 插件 .so 引用主程序符号(IE_ExpSniffer 等 398 个 UND),
     * 插件必须由 AbiWord 主进程 dlopen(主程序提供符号表)。独立 dlopen 时
     * 这些符号无法解析——架构预期。审查意见: 不得直接 PASS → 用 readelf
     * --dyn-syms 实证导出符号; readelf 也失败则返回非零 FAIL。 */
    void *handle = dlopen(so_path, RTLD_LAZY | RTLD_LOCAL);
    if (!handle) {
        const char *err = dlerror();
        printf("[info] dlopen(%s) failed (expected: plugin needs AbiWord "
               "host symbols): %s\n", so_path, err ? err : "(unknown)");
        return verify_exports_via_readelf(so_path);
    }
    printf("[ok] dlopen(%s) succeeded\n", so_path);

    int failures = 0;

    /* abi_plugin_supports_version must exist and return 1 for ABI 3.0.0 */
    supports_version_fn supports_version =
        (supports_version_fn)dlsym(handle, "abi_plugin_supports_version");
    if (!supports_version) {
        fprintf(stderr, "FAIL: abi_plugin_supports_version symbol not found\n");
        failures++;
    } else {
        int rv = supports_version(3, 0, 0);
        printf("[ok] abi_plugin_supports_version(3,0,0) returned %d\n", rv);
        if (rv != 1) {
            fprintf(stderr, "FAIL: expected return value 1, got %d\n", rv);
            failures++;
        }
    }

    /* abi_plugin_register must exist */
    register_fn reg = (register_fn)dlsym(handle, "abi_plugin_register");
    if (!reg) {
        fprintf(stderr, "FAIL: abi_plugin_register symbol not found\n");
        failures++;
    } else {
        printf("[ok] abi_plugin_register symbol found\n");
    }

    /* abi_plugin_unregister must exist */
    unregister_fn unreg = (unregister_fn)dlsym(handle, "abi_plugin_unregister");
    if (!unreg) {
        fprintf(stderr, "FAIL: abi_plugin_unregister symbol not found\n");
        failures++;
    } else {
        printf("[ok] abi_plugin_unregister symbol found\n");
    }

    dlclose(handle);

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d symbol check(s) failed\n", failures);
        return 1;
    }
    printf("Smoke test PASSED.\n");
    return 0;
}

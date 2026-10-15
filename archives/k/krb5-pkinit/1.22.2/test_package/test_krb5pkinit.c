/* krb5-pkinit 测试：
 * 1) 链接 krb5 库集，krb5_init_context 验证库可用；
 * 2) dlopen 包内 pkinit.so 插件（LibreSSL 静态链入），
 *    dlsym 验证客户端 clpreauth 与 KDC kdcpreauth 插件接口符号。
 * 插件路径通过环境变量 KRB5_PKINIT_PLUGIN 传入。 */
#include <dlfcn.h>
#include <krb5.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    krb5_context ctx;
    krb5_error_code ret = krb5_init_context(&ctx);
    if (ret) {
        fprintf(stderr, "krb5_init_context failed: %d\n", ret);
        return 1;
    }
    printf("krb5_init_context: OK\n");
    krb5_free_context(ctx);

    const char *plugin = getenv("KRB5_PKINIT_PLUGIN");
    if (plugin == NULL) {
        fprintf(stderr, "KRB5_PKINIT_PLUGIN not set\n");
        return 1;
    }
    void *h = dlopen(plugin, RTLD_NOW);
    if (h == NULL) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", plugin, dlerror());
        return 1;
    }
    if (dlsym(h, "clpreauth_pkinit_initvt") == NULL) {
        fprintf(stderr, "clpreauth_pkinit_initvt not found: %s\n", dlerror());
        return 1;
    }
    if (dlsym(h, "kdcpreauth_pkinit_initvt") == NULL) {
        fprintf(stderr, "kdcpreauth_pkinit_initvt not found: %s\n", dlerror());
        return 1;
    }
    printf("pkinit.so plugin (clpreauth + kdcpreauth): OK\n");
    return 0;
}

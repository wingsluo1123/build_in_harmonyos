/* krb5-server 服务端库集链接测试：
 * 链接 libkrb5/libkadm5srv/libkdb5 等，krb5_init_context 验证库可用。 */
#include <krb5.h>

#include <stdio.h>

int main(void) {
    krb5_context ctx;
    krb5_error_code ret = krb5_init_context(&ctx);
    if (ret) {
        fprintf(stderr, "krb5_init_context failed: %d\n", ret);
        return 1;
    }
    printf("krb5_init_context: OK\n");
    krb5_free_context(ctx);
    printf("krb5-server library test OK\n");
    return 0;
}

/* test_sofia.c — sofia-sip 1.13.17 消费者冒烟：
 * 包含公共头 <sofia-sip/su.h>，调用 su_init()/su_deinit() 验证
 * 库可编译、链接、运行（su 层生命周期）。
 */
#include <stdio.h>
#include <sofia-sip/su.h>

int main(void)
{
    int rc = su_init();
    if (rc != 0) {
        fprintf(stderr, "su_init failed: %d\n", rc);
        return 1;
    }
    su_deinit();
    printf("sofia su_init/su_deinit OK\n");
    return 0;
}

/* test_ming.c — ming 0.4.8 消费者冒烟：
 * 包含公共头 <ming.h>，调用 Ming_init()/Ming_setSWFCompression()/
 * Ming_cleanup() 验证库可编译、链接、运行。
 */
#include <stdio.h>
#include <ming.h>

int main(void)
{
    int rc = Ming_init();
    if (rc != 0) {
        fprintf(stderr, "Ming_init failed: %d\n", rc);
        return 1;
    }
    /* 设置 SWF 压缩级别（zlib 压缩，Ming 内部 API） */
    Ming_setSWFCompression(9);
    Ming_cleanup();
    printf("ming Ming_init/cleanup OK\n");
    return 0;
}

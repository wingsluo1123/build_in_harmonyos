/* gcc 16.1.0 -fgnu-tm C 消费者测试。
 * 验证安装后的 GCC C 前端（cc1）+ libitm 能用 -fgnu-tm 编译并运行事务代码。
 */
#include <stdlib.h>
#include <stdio.h>

static int x;

static void start(void)
{
    __transaction_atomic { x++; }
}

int main(void)
{
    int failures = 0;

    /* 1. 两次顺序事务应得到 x == 2（对应上游 simple-1.c） */
    x = 0;
    start();
    start();
    if (x != 2) {
        printf("FAIL: x=%d after two transactions\n", x);
        failures++;
    }

    /* 2. 事务内分配 + cancel 回滚（对应上游 alloc-1.c） */
    {
        int leaked = 0;
        __transaction_atomic {
            void *p = malloc(23);
            if (p == NULL) leaked = 1;
            __transaction_cancel;
        }
        if (leaked) {
            printf("FAIL: malloc failed in transaction\n");
            failures++;
        }
    }

    if (failures == 0) {
        printf("C TM ALL PASSED\n");
        return 0;
    }
    printf("C TM %d FAILURE(S)\n", failures);
    return 1;
}

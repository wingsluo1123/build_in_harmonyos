#include <stdio.h>

/* valgrind memcheck 冒烟测试程序：无内存错误时 valgrind -q 应无输出 */
int main(void)
{
    printf("smoke\n");
    return 0;
}

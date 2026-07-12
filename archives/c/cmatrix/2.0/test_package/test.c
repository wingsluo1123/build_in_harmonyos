#include <stdlib.h>

int main(void) {
    /* 验证 cmatrix 二进制可执行且 --version 返回成功 */
    return system("cmatrix --version > /dev/null 2>&1") == 0 ? 0 : 1;
}
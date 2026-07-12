#include <stdlib.h>

int main(void) {
    /* cmatrix 是 CLI 工具，通过 system() 调用二进制验证可执行性 */
    return system("cmatrix --version > /dev/null 2>&1");
}
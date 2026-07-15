#include "spirv/unified1/spirv.h"
#include <stdio.h>

int main(void) {
    /* 验证 SPIR-V 头文件能正常包含并使用基本常量 */
    if (SpvMagicNumber == 0x07230203u && SpvVersion > 0) {
        printf("spirv-headers test OK: SpvMagicNumber=0x%08x, SpvVersion=0x%08x\n",
               SpvMagicNumber, SpvVersion);
        return 0;
    }
    printf("spirv-headers test FAIL\n");
    return 1;
}

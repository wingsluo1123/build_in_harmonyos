#include <stdio.h>
#include "binaryen-c.h"

int main(void) {
    BinaryenModuleRef mod = BinaryenModuleCreate();
    printf("binaryen module: %s\n", mod ? "OK" : "FAIL");
    if (mod) BinaryenModuleDispose(mod);
    return 0;
}

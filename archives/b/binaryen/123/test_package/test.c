#include <stdio.h>
#include <stdlib.h>

/* Test that links against binaryen's C API */
#include "binaryen-c.h"

int main(void) {
    /* Create a minimal WebAssembly module using binaryen's C API */
    BinaryenModuleRef module = BinaryenModuleCreate();
    if (module == NULL) {
        fprintf(stderr, "FAIL: BinaryenModuleCreate returned NULL\n");
        return 1;
    }

    /* Verify the module is valid by printing it (produces empty module text) */
    BinaryenModulePrint(module);

    printf("test binaryen 123: BinaryenModuleCreate + BinaryenModulePrint OK\n");
    BinaryenModuleDispose(module);
    return 0;
}

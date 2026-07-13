#include <stdio.h>
#include "wasm_export.h"

int main(void) {
    bool interp_supported = wasm_runtime_is_running_mode_supported(Mode_Interp);
    if (!interp_supported) {
        fprintf(stderr, "WAMR interpreter mode should be supported\n");
        return 1;
    }
    printf("WAMR interpreter mode is supported\n");

    bool fast_jit_supported = wasm_runtime_is_running_mode_supported(Mode_Fast_JIT);
    if (fast_jit_supported) {
        fprintf(stderr, "WAMR fast-jit should not be supported in this build\n");
        return 1;
    }
    printf("WAMR fast-jit mode is correctly disabled\n");

    return 0;
}

/*
 * Test: verify apitrace CLI tools are installed and functional.
 * Tests both apitrace and gltrim binaries.
 *
 * Note (R40): EGL tracing (egltrace.so) requires a running OHOS graphics
 * stack with EGL context to fully verify. This test validates CLI tools
 * which are the primary user-facing interface. EGL wrapper verification
 * should be done manually on a real OHOS device with a graphics stack.
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Verify apitrace CLI tool responds to help */
    int ret = system("apitrace help > /dev/null 2>&1");
    if (ret == 0) {
        /* Verify gltrim frame trimmer also works */
        ret = system("gltrim --help > /dev/null 2>&1");
    }
    if (ret == 0) {
        printf("test apitrace 14.0: OK (apitrace + gltrim respond)\n");
        return 0;
    } else {
        printf("test apitrace 14.0: FAIL (binary not responding)\n");
        return 1;
    }
}

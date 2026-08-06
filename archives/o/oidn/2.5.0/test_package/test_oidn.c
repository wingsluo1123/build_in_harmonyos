#include <OpenImageDenoise/oidn.h>
#include <stdio.h>

int main() {
    /* Check if OIDN is available and CPU device is supported */
    int supported = oidnIsCPUDeviceSupported();
    printf("OIDN CPU device supported: %s\n", supported ? "yes" : "no");

    if (supported) {
        OIDNDevice device = oidnNewDevice(OIDN_DEVICE_TYPE_CPU);
        if (device) {
            oidnCommitDevice(device);
            printf("OIDN device created and committed successfully\n");
            oidnReleaseDevice(device);
        } else {
            const char* msg = oidnGetDeviceError(device);
            printf("Failed to create device: %s\n", msg);
        }
    }

    printf("OIDN test passed\n");
    return 0;
}

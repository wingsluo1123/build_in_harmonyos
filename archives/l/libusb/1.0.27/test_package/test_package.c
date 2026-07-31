#include <stdio.h>
#include <libusb.h>

int main(void) {
    /* 实质测试: 验证 libusb 库已正确链接并可调用 API */
    const struct libusb_version *ver = libusb_get_version();
    if (!ver) {
        fprintf(stderr, "libusb_get_version() returned NULL\n");
        return 1;
    }
    printf("libusb %d.%d.%d linked and callable\n",
           ver->major, ver->minor, ver->micro);
    /* 不初始化设备发现 (OHOS 沙箱无 sysfs), 仅验证库可用 */
    return 0;
}

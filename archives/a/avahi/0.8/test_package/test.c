#include <stdio.h>
#include <avahi-common/address.h>

int main(void) {
    /* 调用 avahi-common 真实 API: 解析 + 格式化地址 */
    AvahiAddress a;
    char buf[AVAHI_ADDRESS_STR_MAX];
    if (avahi_address_parse("127.0.0.1", AVAHI_IF_UNSPEC, &a) == NULL) {
        printf("test avahi 0.8: address_parse FAILED\n");
        return 1;
    }
    if (avahi_address_snprint(buf, sizeof(buf), &a) == NULL) {
        printf("test avahi 0.8: address_snprint FAILED\n");
        return 1;
    }
    printf("test avahi 0.8: OK (addr=%s)\n", buf);
    return 0;
}

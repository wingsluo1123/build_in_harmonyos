#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libmnl/libmnl.h>

int main(void) {
    /* Test mnl_nlmsg_size: compute total message size for a given payload */
    size_t sz = mnl_nlmsg_size(32);
    if (sz == 0) {
        fprintf(stderr, "FAIL: mnl_nlmsg_size returned 0\n");
        return 1;
    }
    printf("mnl_nlmsg_size(32) = %zu\n", sz);

    /* Test mnl_nlmsg_put_header: build a netlink header in a buffer */
    char buf[256];
    memset(buf, 0, sizeof(buf));
    struct nlmsghdr *nlh = mnl_nlmsg_put_header(buf);
    if (nlh == NULL) {
        fprintf(stderr, "FAIL: mnl_nlmsg_put_header returned NULL\n");
        return 1;
    }
    printf("mnl_nlmsg_put_header OK: nlmsg_len=%u\n", nlh->nlmsg_len);

    /* Test mnl_nlmsg_get_payload_len: verify payload length calculation */
    size_t plen = mnl_nlmsg_get_payload_len(nlh);
    printf("mnl_nlmsg_get_payload_len = %zu\n", plen);

    printf("test libmnl 1.0.5: PASS\n");
    return 0;
}

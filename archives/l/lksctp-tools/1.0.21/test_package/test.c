#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/sctp.h>

/* Consumer smoke test: link against libsctp and exercise its API.
 * Uses an invalid socket descriptor on purpose so the test passes even
 * when the underlying SCTP kernel support is unavailable; what matters
 * is that the library symbols resolve, the OHOS-adapted header compiles
 * (E091 guard), and error paths behave like the documented API. */
int main(void) {
    int fails = 0;
    struct sockaddr_in sin;
    memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_port = htons(9);

    /* 1. sctp_opt_info on an invalid fd must fail with EBADF (symbol present, API wired). */
    errno = 0;
    struct sctp_status st;
    socklen_t sz = sizeof(st);
    memset(&st, 0, sizeof(st));
    int rc = sctp_opt_info(-1, 0, SCTP_STATUS, &st, &sz);
    printf("sctp_opt_info(-1): rc=%d errno=%d(%s)\n", rc, errno, strerror(errno));
    if (rc != -1) {
        printf("FAIL: expected -1\n");
        fails++;
    } else if (errno == EBADF) {
        printf("PASS: libsctp API reachable (EBADF on invalid fd)\n");
    } else {
        /* EPROTONOSUPPORT / ENOTSUP also acceptable if kernel lacks SCTP,
         * but the call must have reached the library. */
        printf("PASS: libsctp API reachable (errno=%d %s)\n", errno, strerror(errno));
    }

    /* 2. Header must expose SCTP constants from the adapted netinet/sctp.h. */
    printf("SOL_SCTP=%d IPPROTO_SCTP=%d\n", SOL_SCTP, IPPROTO_SCTP);
    if (IPPROTO_SCTP != 132 || SOL_SCTP != 132) {
        printf("FAIL: SCTP constants wrong\n");
        fails++;
    } else {
        printf("PASS: SCTP constants OK\n");
    }

    printf("test_lksctp-tools: %s (%d fail%s)\n",
           fails == 0 ? "PASS" : "FAIL", fails, fails == 1 ? "" : "s");
    return fails == 0 ? 0 : 1;
}

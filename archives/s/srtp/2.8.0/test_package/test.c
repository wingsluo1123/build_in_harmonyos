#include <stdio.h>
#include <stdlib.h>
#include <srtp2/srtp.h>

int main(void) {
    srtp_err_status_t status;

    status = srtp_init();
    if (status != srtp_err_status_ok) {
        fprintf(stderr, "srtp_init failed: %d\n", status);
        return 1;
    }

    printf("srtp_init: OK\n");

    status = srtp_shutdown();
    if (status != srtp_err_status_ok) {
        fprintf(stderr, "srtp_shutdown failed: %d\n", status);
        return 1;
    }

    printf("test srtp 2.8.0: OK\n");
    return 0;
}
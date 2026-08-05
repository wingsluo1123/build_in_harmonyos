#include <zmq.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Check library version */
    int major, minor, patch;
    zmq_version(&major, &minor, &patch);
    if (major < 4) {
        printf("FAIL: zeromq version too old: %d.%d.%d\n", major, minor, patch);
        return 1;
    }
    printf("zeromq version: %d.%d.%d\n", major, minor, patch);

    /* Create a context */
    void *ctx = zmq_ctx_new();
    if (!ctx) {
        printf("FAIL: zmq_ctx_new returned NULL\n");
        return 1;
    }

    /* Create a REP socket */
    void *sock = zmq_socket(ctx, ZMQ_REP);
    if (!sock) {
        printf("FAIL: zmq_socket returned NULL\n");
        zmq_ctx_term(ctx);
        return 1;
    }

    /* Bind to inproc endpoint */
    int rc = zmq_bind(sock, "inproc://test");
    if (rc != 0) {
        printf("FAIL: zmq_bind failed: %s\n", zmq_strerror(zmq_errno()));
        zmq_close(sock);
        zmq_ctx_term(ctx);
        return 1;
    }

    /* Clean up */
    zmq_close(sock);
    zmq_ctx_term(ctx);

    printf("test zeromq 4.3.5: OK\n");
    return 0;
}

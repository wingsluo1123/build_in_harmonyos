#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <raft.h>

int main(void) {
    raft_configuration config;
    unsigned id;
    char *address;
    int rv;

    /* Test: raft_configuration_init + raft_configuration_add */
    raft_configuration_init(&config);
    rv = raft_configuration_add(&config, 1, "127.0.0.1:9090", RAFT_STANDBY);
    if (rv != 0) {
        fprintf(stderr, "raft_configuration_add failed: %s\n", raft_errmsg(rv));
        return 1;
    }

    /* Test: raft_configuration_get */
    rv = raft_configuration_get(&config, 1, &id, &address);
    if (rv != 0 || id != 1 || strcmp(address, "127.0.0.1:9090") != 0) {
        fprintf(stderr, "raft_configuration_get failed or returned wrong values\n");
        return 1;
    }

    /* Test: raft_configuration_encode */
    raft_buffer buf;
    raft_configuration_encode(&config, &buf);
    if (buf.len == 0) {
        fprintf(stderr, "raft_configuration_encode produced empty buffer\n");
        return 1;
    }
    raft_free(buf.base);

    /* Test: raft_vsnprintf (internal error handling) */
    char msg[256];
    raft_errmsg_print(msg, sizeof msg, "raft test: %s", "OK");

    raft_configuration_close(&config);

    printf("test raft 0.18.1: OK\n");
    return 0;
}
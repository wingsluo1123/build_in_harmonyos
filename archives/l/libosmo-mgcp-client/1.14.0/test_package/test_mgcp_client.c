#include <stdio.h>
#include <string.h>

#include <talloc.h>

#include <osmocom/mgcp_client/mgcp_client.h>

int main(void) {
    void *ctx = talloc_named_const(NULL, 1, "mgcp-client-consumer");
    if (ctx == NULL)
        return 1;

    struct mgcp_client_conf *conf = mgcp_client_conf_alloc(ctx);
    if (conf == NULL)
        return 2;
    if (conf->local_port != -1 || conf->remote_port != -1 ||
        conf->remote_addr != NULL)
        return 3;

    struct mgcp_client *client = mgcp_client_init(ctx, conf);
    if (client == NULL)
        return 4;
    if (mgcp_client_endpoint_domain(client) == NULL)
        return 5;

    talloc_free(ctx);
    puts("LIBOSMO_MGCP_CLIENT_CONSUMER_OK");
    return 0;
}

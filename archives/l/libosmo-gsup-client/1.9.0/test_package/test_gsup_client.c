#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <talloc.h>

#include <osmocom/gsupclient/gsup_req.h>

int main(void) {
    void *ctx = talloc_named_const(NULL, 1, "gsup-client-consumer");
    if (ctx == NULL)
        return 1;

    struct osmo_gsup_message request = {
        .message_type = OSMO_GSUP_MSGT_UPDATE_LOCATION_REQUEST,
        .imsi = "123456789012345",
        .session_id = 42,
        .session_state = OSMO_GSUP_SESSION_STATE_BEGIN,
    };
    struct osmo_gsup_message response;
    memset(&response, 0, sizeof(response));

    if (osmo_gsup_make_response(&response, &request, 0, 1) < 0)
        return 2;
    if (response.message_type == request.message_type)
        return 3;
    if (response.session_id != request.session_id)
        return 4;
    if (response.session_state != OSMO_GSUP_SESSION_STATE_END)
        return 5;

    talloc_free(ctx);
    puts("LIBOSMO_GSUP_CLIENT_CONSUMER_OK");
    return 0;
}

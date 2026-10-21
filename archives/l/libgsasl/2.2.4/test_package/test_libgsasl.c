#include <gsasl.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    Gsasl *context = NULL;
    Gsasl_session *session = NULL;
    char *response = NULL;
    size_t response_len = 0;
    static const char expected[] = "\0jas\0secret";
    int result = gsasl_init(&context);
    if (result != GSASL_OK || context == NULL) {
        fprintf(stderr, "gsasl_init failed: %s\n", gsasl_strerror(result));
        return 1;
    }
    if (!gsasl_client_support_p(context, "PLAIN")) {
        fprintf(stderr, "PLAIN client mechanism is unavailable\n");
        gsasl_done(context);
        return 2;
    }
    result = gsasl_client_start(context, "PLAIN", &session);
    if (result != GSASL_OK || session == NULL) {
        fprintf(stderr, "PLAIN session start failed: %s\n", gsasl_strerror(result));
        gsasl_done(context);
        return 3;
    }
    result = gsasl_property_set(session, GSASL_AUTHID, "jas");
    if (result == GSASL_OK) {
        result = gsasl_property_set(session, GSASL_PASSWORD, "secret");
    }
    if (result != GSASL_OK) {
        fprintf(stderr, "PLAIN property setup failed: %s\n", gsasl_strerror(result));
        gsasl_finish(session);
        gsasl_done(context);
        return 4;
    }
    result = gsasl_step(session, "", 0, &response, &response_len);
    if (result != GSASL_OK || response_len != sizeof(expected) - 1 ||
        response == NULL || memcmp(response, expected, sizeof(expected) - 1) != 0) {
        fprintf(stderr, "PLAIN wire response mismatch: %s\n", gsasl_strerror(result));
        gsasl_free(response);
        gsasl_finish(session);
        gsasl_done(context);
        return 5;
    }
    gsasl_free(response);
    gsasl_finish(session);
    gsasl_done(context);
    return 0;
}

#include <sofia-sip/nua.h>
#include <sofia-sip/nua_tag.h>
#include <sofia-sip/su.h>

#include <stdio.h>
#include <stdlib.h>

static int shutdown_complete;

static void on_nua_event(nua_event_t event, int status, char const *phrase,
                         nua_t *nua, nua_magic_t *magic, nua_handle_t *handle,
                         nua_hmagic_t *handle_magic, sip_t const *sip,
                         tagi_t tags[])
{
    int *shutdown_seen = magic;
    (void)phrase;
    (void)nua;
    (void)handle;
    (void)handle_magic;
    (void)sip;
    (void)tags;

    if (event == nua_r_shutdown && status >= 200 && shutdown_seen != NULL)
        *shutdown_seen = 1;
}

int main(void)
{
    su_root_t *root = NULL;
    nua_t *nua = NULL;
    nua_handle_t *handle = NULL;
    int su_initialized = 0;
    int result = EXIT_FAILURE;

    if (su_init() != 0) {
        fputs("su_init failed\n", stderr);
        goto cleanup;
    }
    su_initialized = 1;

    root = su_root_create(NULL);
    if (root == NULL) {
        fputs("su_root_create failed\n", stderr);
        goto cleanup;
    }

    nua = nua_create(root, on_nua_event, &shutdown_complete,
                     NUTAG_URL("sip:127.0.0.1:*"), TAG_END());
    if (nua == NULL) {
        fputs("nua_create failed\n", stderr);
        goto cleanup;
    }

    handle = nua_handle(nua, NULL, TAG_END());
    if (handle == NULL) {
        fputs("nua_handle failed\n", stderr);
        goto cleanup;
    }

    result = EXIT_SUCCESS;

cleanup:
    if (handle != NULL) {
        nua_handle_destroy(handle);
        handle = NULL;
    }
    if (nua != NULL && root != NULL) {
        shutdown_complete = 0;
        nua_shutdown(nua);
        for (unsigned int attempt = 0;
             attempt < 100 && !shutdown_complete; attempt++)
            su_root_step(root, 100);
        if (shutdown_complete) {
            nua_destroy(nua);
            nua = NULL;
        } else {
            fputs("nua_shutdown did not complete\n", stderr);
            result = EXIT_FAILURE;
        }
    }
    if (nua == NULL && root != NULL)
        su_root_destroy(root);
    if (su_initialized && nua == NULL)
        su_deinit();

    if (result == EXIT_SUCCESS)
        puts("SOFIA_SIP_CONSUMER_OK");
    return result;
}

#define _POSIX_C_SOURCE 200809L

#include <glib.h>
#include <sofia-sip/nua.h>
#include <sofia-sip/nua_tag.h>
#include <sofia-sip/su.h>
#include <sofia-sip/su_glib.h>

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

enum { SIP_BUFFER_SIZE = 8192, LOOP_TIMEOUT_SECONDS = 8 };

typedef struct {
    int socket_fd;
    unsigned int requests_received;
    unsigned int responses_sent;
    char error[192];
} udp_responder_t;

typedef struct {
    GMainLoop *loop;
    int callback_seen;
    int callback_status;
    int timed_out;
    int shutdown_complete;
} sip_client_t;

static int contains_case_insensitive(char const *text, char const *needle)
{
    size_t needle_length = strlen(needle);
    for (; *text != '\0'; text++) {
        if (strncasecmp(text, needle, needle_length) == 0)
            return 1;
    }
    return 0;
}

static int append_text(char *buffer, size_t capacity, size_t *used,
                       char const *format, ...)
{
    va_list arguments;
    int written;

    if (*used >= capacity)
        return -1;
    va_start(arguments, format);
    written = vsnprintf(buffer + *used, capacity - *used, format, arguments);
    va_end(arguments);
    if (written < 0 || (size_t)written >= capacity - *used)
        return -1;
    *used += (size_t)written;
    return 0;
}

static int append_sip_header(char const *request, char const *name,
                             char *response, size_t capacity, size_t *used,
                             int add_to_tag)
{
    size_t name_length = strlen(name);
    char const *line = request;
    int found = 0;

    while (*line != '\0') {
        char const *end = strstr(line, "\r\n");
        size_t line_length;
        if (end == NULL || end == line)
            break;
        line_length = (size_t)(end - line);
        if (line_length >= name_length &&
            strncasecmp(line, name, name_length) == 0) {
            if (add_to_tag && !contains_case_insensitive(line, "tag=")) {
                if (append_text(response, capacity, used,
                                "%.*s;tag=ohos-test\r\n",
                                (int)line_length, line) != 0)
                    return -1;
            } else if (append_text(response, capacity, used, "%.*s\r\n",
                                   (int)line_length, line) != 0) {
                return -1;
            }
            found++;
            if (strcasecmp(name, "Via:") != 0)
                return found;
        }
        line = end + 2;
    }
    return found;
}

static void *answer_one_options(void *argument)
{
    udp_responder_t *responder = argument;
    struct sockaddr_in peer;
    socklen_t peer_length = sizeof(peer);
    char request[SIP_BUFFER_SIZE];
    char response[SIP_BUFFER_SIZE];
    ssize_t received;
    size_t used = 0;

    received = recvfrom(responder->socket_fd, request, sizeof(request) - 1, 0,
                        (struct sockaddr *)&peer, &peer_length);
    if (received < 0) {
        snprintf(responder->error, sizeof(responder->error),
                 "recvfrom failed: %s", strerror(errno));
        return NULL;
    }
    request[received] = '\0';
    responder->requests_received++;
    if (strncmp(request, "OPTIONS ", 8) != 0) {
        snprintf(responder->error, sizeof(responder->error),
                 "expected SIP OPTIONS, received: %.80s", request);
        return NULL;
    }

    if (append_text(response, sizeof(response), &used, "SIP/2.0 200 OK\r\n") != 0 ||
        append_sip_header(request, "Via:", response, sizeof(response), &used, 0) < 1 ||
        append_sip_header(request, "From:", response, sizeof(response), &used, 0) != 1 ||
        append_sip_header(request, "To:", response, sizeof(response), &used, 1) != 1 ||
        append_sip_header(request, "Call-ID:", response, sizeof(response), &used, 0) != 1 ||
        append_sip_header(request, "CSeq:", response, sizeof(response), &used, 0) != 1 ||
        append_text(response, sizeof(response), &used,
                    "Content-Length: 0\r\n\r\n") != 0) {
        snprintf(responder->error, sizeof(responder->error),
                 "OPTIONS request did not contain required SIP transaction headers");
        return NULL;
    }

    if (sendto(responder->socket_fd, response, used, 0,
               (struct sockaddr *)&peer, peer_length) != (ssize_t)used) {
        snprintf(responder->error, sizeof(responder->error),
                 "sendto failed: %s", strerror(errno));
        return NULL;
    }
    responder->responses_sent++;
    return NULL;
}

static void on_nua_event(nua_event_t event, int status, char const *phrase,
                         nua_t *nua, nua_magic_t *magic, nua_handle_t *handle,
                         nua_hmagic_t *handle_magic, sip_t const *sip,
                         tagi_t tags[])
{
    sip_client_t *client = magic;
    (void)phrase;
    (void)nua;
    (void)handle;
    (void)handle_magic;
    (void)sip;
    (void)tags;

    if (event == nua_r_options && status >= 200) {
        client->callback_seen = 1;
        client->callback_status = status;
        g_main_loop_quit(client->loop);
    } else if (event == nua_r_shutdown && status >= 200) {
        client->shutdown_complete = 1;
        g_main_loop_quit(client->loop);
    }
}

static gboolean on_loop_timeout(gpointer argument)
{
    sip_client_t *client = argument;
    client->timed_out = 1;
    g_main_loop_quit(client->loop);
    return G_SOURCE_REMOVE;
}

int main(void)
{
    struct sockaddr_in server_address;
    socklen_t server_address_length = sizeof(server_address);
    struct timeval receive_timeout = { 10, 0 };
    udp_responder_t responder = { -1, 0, 0, "" };
    sip_client_t client = { NULL, 0, 0, 0, 0 };
    GSource *sofia_source = NULL;
    guint timeout_source = 0;
    pthread_t responder_thread;
    int responder_started = 0;
    int su_initialized = 0;
    su_root_t *root = NULL;
    nua_t *nua = NULL;
    nua_handle_t *handle = NULL;
    char target[96];
    int result = EXIT_FAILURE;
    gint64 started_at;
    gint64 elapsed_ms;

    responder.socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (responder.socket_fd < 0) {
        perror("socket");
        goto cleanup;
    }
    if (setsockopt(responder.socket_fd, SOL_SOCKET, SO_RCVTIMEO,
                   &receive_timeout, sizeof(receive_timeout)) != 0) {
        perror("setsockopt(SO_RCVTIMEO)");
        goto cleanup;
    }
    memset(&server_address, 0, sizeof(server_address));
    server_address.sin_family = AF_INET;
    server_address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    server_address.sin_port = 0;
    if (bind(responder.socket_fd, (struct sockaddr *)&server_address,
             sizeof(server_address)) != 0 ||
        getsockname(responder.socket_fd, (struct sockaddr *)&server_address,
                    &server_address_length) != 0) {
        perror("bind/getsockname");
        goto cleanup;
    }
    snprintf(target, sizeof(target), "sip:127.0.0.1:%u",
             (unsigned int)ntohs(server_address.sin_port));

    if (su_init() != 0) {
        fputs("su_init failed\n", stderr);
        goto cleanup;
    }
    su_initialized = 1;
    client.loop = g_main_loop_new(NULL, FALSE);
    if (client.loop == NULL) {
        fputs("g_main_loop_new failed\n", stderr);
        goto cleanup;
    }
    root = su_glib_root_create(NULL);
    if (root == NULL) {
        fputs("su_glib_root_create failed\n", stderr);
        goto cleanup;
    }
    sofia_source = su_glib_root_gsource(root);
    if (sofia_source == NULL) {
        fputs("failed to create Sofia GLib source\n", stderr);
        goto cleanup;
    }
    g_source_ref(sofia_source);
    if (g_source_attach(sofia_source,
                        g_main_loop_get_context(client.loop)) == 0) {
        fputs("failed to attach Sofia root source to GLib context\n", stderr);
        goto cleanup;
    }
    nua = nua_create(root, on_nua_event, &client,
                     NUTAG_URL("sip:127.0.0.1:*"), TAG_END());
    if (nua == NULL) {
        fputs("nua_create failed\n", stderr);
        goto cleanup;
    }
    handle = nua_handle(nua, NULL, NUTAG_URL(target), TAG_END());
    if (handle == NULL) {
        fputs("nua_handle failed\n", stderr);
        goto cleanup;
    }
    if (pthread_create(&responder_thread, NULL, answer_one_options, &responder) != 0) {
        fputs("pthread_create failed\n", stderr);
        goto cleanup;
    }
    responder_started = 1;
    timeout_source = g_timeout_add_seconds(LOOP_TIMEOUT_SECONDS,
                                           on_loop_timeout, &client);
    if (timeout_source == 0) {
        fputs("failed to install GLib timeout\n", stderr);
        goto cleanup;
    }

    started_at = g_get_monotonic_time();
    nua_options(handle, TAG_END());
    g_main_loop_run(client.loop);
    elapsed_ms = (g_get_monotonic_time() - started_at) / 1000;

    if (!client.timed_out)
        g_source_remove(timeout_source);
    timeout_source = 0;
    if (pthread_join(responder_thread, NULL) != 0) {
        fputs("pthread_join failed\n", stderr);
        responder_started = 0;
        goto cleanup;
    }
    responder_started = 0;

    if (client.callback_seen && client.callback_status == 200 &&
        responder.requests_received == 1 && responder.responses_sent == 1 &&
        elapsed_ms >= 0) {
        result = EXIT_SUCCESS;
    } else {
        fprintf(stderr,
                "SIP OPTIONS exchange failed: callback=%d status=%d timeout=%d "
                "requests=%u responses=%u elapsed_ms=%lld server_error=%s\n",
                client.callback_seen, client.callback_status, client.timed_out,
                responder.requests_received, responder.responses_sent,
                (long long)elapsed_ms, responder.error);
    }

cleanup:
    if (responder_started)
        pthread_join(responder_thread, NULL);
    if (timeout_source != 0) {
        g_source_remove(timeout_source);
        timeout_source = 0;
    }
    if (handle != NULL) {
        nua_handle_destroy(handle);
        handle = NULL;
    }
    if (nua != NULL) {
        client.shutdown_complete = 0;
        client.timed_out = 0;
        nua_shutdown(nua);
        timeout_source = g_timeout_add_seconds(LOOP_TIMEOUT_SECONDS,
                                               on_loop_timeout, &client);
        if (timeout_source != 0 && client.loop != NULL)
            g_main_loop_run(client.loop);
        if (timeout_source != 0) {
            if (!client.timed_out)
                g_source_remove(timeout_source);
            timeout_source = 0;
        }
        if (client.shutdown_complete) {
            nua_destroy(nua);
            nua = NULL;
        } else {
            fputs("nua_shutdown did not complete\n", stderr);
            result = EXIT_FAILURE;
        }
    }
    if (nua == NULL && sofia_source != NULL) {
        g_source_destroy(sofia_source);
        g_source_unref(sofia_source);
    }
    if (nua == NULL && root != NULL)
        su_root_destroy(root);
    if (nua == NULL && client.loop != NULL)
        g_main_loop_unref(client.loop);
    if (su_initialized && nua == NULL)
        su_deinit();
    if (responder.socket_fd >= 0)
        close(responder.socket_fd);

    if (result == EXIT_SUCCESS)
        printf("SOFIA_SIP_HARMONYOS_OPTIONS_OK requests=%u responses=%u "
               "status=%d shutdown=%d elapsed_ms=%lld\n",
               responder.requests_received, responder.responses_sent,
               client.callback_status, client.shutdown_complete,
               (long long)elapsed_ms);
    return result;
}

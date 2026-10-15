#include <tlsrpt.h>
#include <errno.h>
#include <poll.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr, "line %d: %s (errno=%d)\n", __LINE__, #x, errno); \
    return 1; } } while (0)
#define OK(x) do { int rc_ = (x); if (rc_) { \
    fprintf(stderr, "line %d: %s returned %d: %s\n", \
        __LINE__, #x, rc_, tlsrpt_strerror(rc_)); return 1; } } while (0)

static void *no_memory(size_t size) {
    (void)size;
    errno = ENOMEM;
    return NULL;
}

int main(int argc, char **argv) {
    struct tlsrpt_connection_t *con = NULL;
    struct tlsrpt_dr_t *dr = NULL;
    const char *mode = argc > 1 ? argv[1] : "version";
    if (!strcmp(mode, "version")) {
        CHECK(!strcmp(tlsrpt_version(), "0.5.0"));
        CHECK(tlsrpt_version_check(0, 5, 0));
        CHECK(tlsrpt_version_check(0, 4, 0));
        CHECK(!tlsrpt_version_check(0, 6, 0));
        CHECK(!tlsrpt_version_check(1, 5, 0));
        return 0;
    }
    if (!strcmp(mode, "errors")) {
        CHECK(tlsrpt_error_code_is_internal(TLSRPT_ERR_TLSRPT_CANCELLED));
        CHECK(!tlsrpt_error_code_is_internal(TLSRPT_ERR_SENDTO + ENOENT));
        CHECK(tlsrpt_errno_from_error_code(TLSRPT_ERR_SENDTO + ENOENT) == ENOENT);
        CHECK(strstr(tlsrpt_strerror(TLSRPT_ERR_TLSRPT_CANCELLED), "cancelled"));
        CHECK(strstr(tlsrpt_strerror(TLSRPT_ERR_SENDTO + ENOENT), "sendto"));
        return 0;
    }
    if (!strcmp(mode, "allocator")) {
        tlsrpt_set_malloc_and_free(no_memory, free);
        CHECK(tlsrpt_open(&con, "unused.sock") == TLSRPT_ERR_MALLOC_OPENCON + ENOMEM);
        CHECK(con == NULL);
        tlsrpt_set_malloc_and_free(malloc, free);
        OK(tlsrpt_open(&con, "unused.sock"));
        tlsrpt_set_malloc_and_free(no_memory, free);
        CHECK(tlsrpt_init_delivery_request(&dr, con, "example.org", "v=TLSRPTv1")
              == TLSRPT_ERR_MALLOC_OPENDR + ENOMEM);
        CHECK(dr == NULL);
        tlsrpt_set_malloc_and_free(malloc, free);
        OK(tlsrpt_close(&con));
        return 0;
    }
    if (!strcmp(mode, "no_connection")) {
        CHECK(tlsrpt_init_delivery_request(&dr, NULL, "example.org", "v=TLSRPTv1")
              == TLSRPT_ERR_TLSRPT_NOCONNECTION);
        CHECK(dr == NULL);
        return 0;
    }
    if (!strcmp(mode, "long_path")) {
        char path[256];
        memset(path, 'x', sizeof(path) - 1);
        path[sizeof(path) - 1] = 0;
        CHECK(tlsrpt_open(&con, path) == TLSRPT_ERR_TLSRPT_SOCKETNAMETOOLONG);
        CHECK(con == NULL);
        return 0;
    }

    char path[64];
    snprintf(path, sizeof(path), "tlsrpt-%ld.sock", (long)getpid());
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strcpy(addr.sun_path, path);
    int receiver = socket(AF_UNIX, SOCK_DGRAM, 0);
    CHECK(receiver >= 0);
    int abstract = 0;
    if (bind(receiver, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        CHECK(errno == EPERM || errno == EACCES || errno == EROFS);
        abstract = 1;
        path[0] = '@';
        strcpy(addr.sun_path, path);
        addr.sun_path[0] = 0;
        socklen_t size = offsetof(struct sockaddr_un, sun_path) + strlen(path);
        CHECK(bind(receiver, (struct sockaddr *)&addr, size) == 0);
    }
    char destination[80];
    strcpy(destination, path);
    if (!strcmp(mode, "missing_receiver")) strcat(destination, ".missing");
    OK(tlsrpt_open(&con, destination));
    CHECK(tlsrpt_get_socket(con) >= 0);
    tlsrpt_set_blocking();
    tlsrpt_set_nonblocking();
    if (!strcmp(mode, "connection")) {
        OK(tlsrpt_close(&con));
        CHECK(con == NULL);
        close(receiver);
        if (!abstract) unlink(path);
        return 0;
    }
    OK(tlsrpt_init_delivery_request(&dr, con, "example.org", "v=TLSRPTv1; rua=mailto:r@example.org"));
    int expected = 0;
    int receive_report = 0;
    if (!strcmp(mode, "no_policies")) {
        expected = TLSRPT_ERR_TLSRPT_NOPOLICIES;
    } else if (!strcmp(mode, "cancel")) {
        OK(tlsrpt_init_policy(dr, TLSRPT_POLICY_STS, "example.org"));
        OK(tlsrpt_add_policy_string(dr, "version: STSv1"));
        OK(tlsrpt_cancel_delivery_request(&dr));
    } else {
        OK(tlsrpt_init_policy(dr, TLSRPT_POLICY_STS, "example.org"));
        if (!strcmp(mode, "nested")) {
            CHECK(tlsrpt_init_policy(dr, TLSRPT_POLICY_TLSA, NULL) == TLSRPT_ERR_TLSRPT_NESTEDPOLICY);
            expected = TLSRPT_ERR_TLSRPT_NESTEDPOLICY;
        } else if (!strcmp(mode, "unfinished")) {
            expected = TLSRPT_ERR_TLSRPT_UNFINISHEDPOLICY;
        } else {
            OK(tlsrpt_add_policy_string(dr, "version: STSv1"));
            OK(tlsrpt_add_policy_string(dr, "mode: enforce"));
            OK(tlsrpt_add_mx_host_pattern(dr, "*.example.org"));
            if (!strcmp(mode, "failure")) {
                OK(tlsrpt_add_delivery_request_failure(dr, TLSRPT_CERTIFICATE_EXPIRED,
                    "192.0.2.1", "mx.example.org", "mail.example.org", "192.0.2.2",
                    "quote\" slash\\ line\n tab\t", "certificate-expired"));
                OK(tlsrpt_finish_policy(dr, TLSRPT_FINAL_FAILURE));
            } else {
                OK(tlsrpt_finish_policy(dr, TLSRPT_FINAL_SUCCESS));
            }
            if (!strcmp(mode, "multiple")) {
                OK(tlsrpt_init_policy(dr, TLSRPT_POLICY_TLSA, NULL));
                OK(tlsrpt_add_delivery_request_failure(dr, TLSRPT_DNSSEC_INVALID,
                    NULL, NULL, NULL, NULL, NULL, NULL));
                OK(tlsrpt_finish_policy(dr, TLSRPT_FINAL_FAILURE));
                OK(tlsrpt_init_policy(dr, TLSRPT_NO_POLICY_FOUND, NULL));
                OK(tlsrpt_finish_policy(dr, TLSRPT_FINAL_SUCCESS));
            }
            receive_report = 1;
        }
    }
    if (!strcmp(mode, "missing_receiver")) {
        expected = TLSRPT_ERR_SENDTO + (abstract ? ECONNREFUSED : ENOENT);
        receive_report = 0;
    }
    if (dr) CHECK(tlsrpt_finish_delivery_request(&dr) == expected);
    CHECK(dr == NULL);
    struct pollfd pfd = {receiver, POLLIN, 0};
    if (receive_report) {
        CHECK(poll(&pfd, 1, 2000) == 1);
        char buffer[65001];
        ssize_t size = recv(receiver, buffer, sizeof(buffer) - 1, 0);
        CHECK(size > 0);
        buffer[size] = 0;
        puts(buffer);
    } else {
        CHECK(poll(&pfd, 1, 0) == 0);
    }
    OK(tlsrpt_close(&con));
    CHECK(con == NULL);
    close(receiver);
    if (!abstract) unlink(path);
    return 0;
}

/*
 * Installed-package consumer for libircclient 1.10.
 *
 * Two layers, in increasing strength:
 *
 *   A. API conformance -- session lifetime, user-context slot, option flags,
 *      error mapping.  Catches ABI drift from the compiled-in ENABLE_THREADS
 *      layout and any missing symbol at link time.
 *
 *   B. End-to-end protocol flow -- a fake IRC server is started on loopback
 *      inside this process; the packaged library really connects to it,
 *      performs the NICK/USER registration handshake, receives a 001 welcome
 *      (which must fire the event_connect callback) and answers a server PING
 *      with PONG.  Nothing here is a mock of the library: bytes travel over a
 *      real TCP socket and the library's own parser/dispatcher handles them.
 *      The server then closes the connection, which must drive irc_run() out
 *      of its loop with an error recorded on the session.
 *
 * Layer B needs no external network and no display: loopback only.
 */
#include <libircclient.h>

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

static int failures = 0;

static void check(int condition, const char *what)
{
    if (condition) {
        printf("ok   %s\n", what);
    } else {
        printf("FAIL %s\n", what);
        failures++;
    }
}

/* ---------------------------------------------------------------- server -- */

typedef struct {
    int listen_fd;
    unsigned short port;
    int accepted;
    int saw_nick;
    int saw_user;
    int saw_pong;
    int handshake_sent;
} fake_server_t;

static int wait_readable(int fd, int seconds)
{
    fd_set readable;
    struct timeval timeout;

    FD_ZERO(&readable);
    FD_SET(fd, &readable);
    timeout.tv_sec = seconds;
    timeout.tv_usec = 0;
    return select(fd + 1, &readable, NULL, NULL, &timeout) > 0;
}

static void *server_main(void *argument)
{
    fake_server_t *server = (fake_server_t *) argument;
    char buffer[4096];
    size_t used = 0;
    int rounds = 0;
    int connection;

    if (!wait_readable(server->listen_fd, 20)) {
        return NULL;
    }
    connection = accept(server->listen_fd, NULL, NULL);
    if (connection < 0) {
        return NULL;
    }
    server->accepted = 1;

    while (rounds++ < 40) {
        ssize_t received;

        if (!wait_readable(connection, 2)) {
            break;
        }
        received = recv(connection, buffer + used, sizeof(buffer) - used - 1, 0);
        if (received <= 0) {
            break;
        }
        used += (size_t) received;
        buffer[used] = '\0';

        if (strstr(buffer, "NICK testnick") != NULL) {
            server->saw_nick = 1;
        }
        if (strstr(buffer, "USER testuser") != NULL) {
            server->saw_user = 1;
        }
        if (strstr(buffer, "PONG") != NULL) {
            server->saw_pong = 1;
        }

        /* Register first, then ask the client to prove it parses input. */
        if (!server->handshake_sent && server->saw_nick && server->saw_user) {
            const char *welcome =
                ":fake.irc.server 001 testnick :Welcome to the consumer test\r\n"
                "PING :e2e-round-trip\r\n";
            send(connection, welcome, strlen(welcome), 0);
            server->handshake_sent = 1;
        }
        if (server->saw_pong) {
            break;
        }
    }

    /* Let the library drain the welcome before it observes end-of-file. */
    usleep(200000);
    close(connection);
    return NULL;
}

/* ------------------------------------------------------------- callbacks -- */

static int connect_events = 0;

static void on_connect(irc_session_t *session, const char *event,
                       const char *origin, const char **params,
                       unsigned int count)
{
    (void) session;
    (void) event;
    (void) origin;
    (void) params;
    (void) count;
    connect_events++;
}

/* ------------------------------------------------------------------ main -- */

static int start_listener(fake_server_t *server)
{
    struct sockaddr_in address;
    socklen_t length = sizeof(address);
    int enable = 1;

    server->listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server->listen_fd < 0) {
        return 0;
    }
    setsockopt(server->listen_fd, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable));

    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = 0; /* ephemeral */

    if (bind(server->listen_fd, (struct sockaddr *) &address, sizeof(address)) != 0) {
        return 0;
    }
    if (listen(server->listen_fd, 1) != 0) {
        return 0;
    }
    if (getsockname(server->listen_fd, (struct sockaddr *) &address, &length) != 0) {
        return 0;
    }
    server->port = ntohs(address.sin_port);
    return 1;
}

int main(void)
{
    irc_callbacks_t callbacks;
    irc_session_t *session;
    fake_server_t server;
    pthread_t server_thread;
    unsigned short port;
    int cookie = 1234;
    const char *message;
    int rc;

    /* ---- A. API conformance ------------------------------------------- */

    memset(&callbacks, 0, sizeof(callbacks));
    session = irc_create_session(&callbacks);
    check(session != NULL, "irc_create_session returns a session");
    if (session == NULL) {
        return 1;
    }

    check(irc_get_ctx(session) == NULL, "fresh session has a null user context");
    irc_set_ctx(session, &cookie);
    check(irc_get_ctx(session) == &cookie,
          "user context round trips through irc_set_ctx/irc_get_ctx");

    irc_option_set(session, LIBIRC_OPTION_DEBUG);
    irc_option_reset(session, LIBIRC_OPTION_DEBUG);
    check(1, "irc_option_set/irc_option_reset are callable");

    check(irc_errno(session) == 0, "fresh session reports no pending error");

    message = irc_strerror(0);
    check(message != NULL && strcmp(message, "No error") == 0,
          "irc_strerror(0) maps to \"No error\"");

    message = irc_strerror(LIBIRC_ERR_SOCKET);
    check(message != NULL && strlen(message) > 0,
          "irc_strerror maps a non-zero code to a message");

    irc_destroy_session(session);
    check(1, "irc_destroy_session returns without crashing");

    /* ---- B. End-to-end protocol flow ---------------------------------- */

    memset(&server, 0, sizeof(server));
    server.listen_fd = -1;
    check(start_listener(&server), "fake IRC server listens on loopback");
    if (server.listen_fd < 0 || server.port == 0) {
        return 2;
    }
    port = server.port;

    memset(&callbacks, 0, sizeof(callbacks));
    callbacks.event_connect = on_connect;

    session = irc_create_session(&callbacks);
    check(session != NULL, "irc_create_session for the end-to-end session");
    if (session == NULL) {
        close(server.listen_fd);
        return 2;
    }

    if (pthread_create(&server_thread, NULL, server_main, &server) != 0) {
        check(0, "fake IRC server thread starts");
        close(server.listen_fd);
        irc_destroy_session(session);
        return 2;
    }

    rc = irc_connect(session, "127.0.0.1", port, NULL,
                     "testnick", "testuser", "Consumer Test");
    check(rc == 0, "irc_connect to the packaged library reaches the server");

    /* Blocks until the server closes the connection. */
    rc = irc_run(session);
    check(rc != 0, "irc_run leaves its loop when the peer closes");
    /*
     * Upstream maps a peer close to LIBIRC_ERR_TERMINATED, not LIBIRC_ERR_CLOSED:
     * libircclient.c:903 tests `length < 0` and then libircclient.c:906 compares
     * that same negative value against 0, so the CLOSED arm is unreachable.
     * Assert what the library actually does (measured on aarch64 OHOS) rather
     * than what its comment says.
     */
    printf("     peer-close errno = %d (expected %d)\n",
           irc_errno(session), LIBIRC_ERR_TERMINATED);
    check(irc_errno(session) == LIBIRC_ERR_TERMINATED,
          "the peer close is reported as LIBIRC_ERR_TERMINATED");

    pthread_join(server_thread, NULL);
    close(server.listen_fd);

    check(server.accepted == 1, "the library really opened a TCP connection");
    check(server.saw_nick, "the library sent NICK testnick");
    check(server.saw_user, "the library sent USER testuser");
    check(server.saw_pong, "the library answered the server PING with PONG");
    check(connect_events >= 1, "the 001 welcome fired event_connect");
    check(irc_is_connected(session) == 0,
          "irc_is_connected is false after the peer closed");

    irc_destroy_session(session);

    if (failures != 0) {
        printf("libircclient installed-package test failed: %d check(s)\n", failures);
        return 2;
    }
    printf("libircclient installed-package test passed\n");
    return 0;
}

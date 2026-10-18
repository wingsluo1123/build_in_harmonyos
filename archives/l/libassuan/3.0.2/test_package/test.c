/* Consumer test for libassuan 3.0.2 on HarmonyOS.
 *
 * Builds a real Assuan client/server pair over a Unix-domain socketpair and
 * exercises the packaged library's public API end to end:
 *   - assuan_check_version: header/ABI version compatibility
 *   - assuan_new / assuan_init_socket_server / assuan_register_command
 *   - assuan_socket_connect_fd
 *   - assuan_transact with ECHO (data round-trip) and BYE (clean close)
 *
 * Each distinct functional check prints a "CASE PASS" line on success;
 * test_package/conanfile.py counts exactly those lines as the deterministic
 * executed/passed figure for HMBS_TEST_PACKAGE_RESULT.  A failure returns a
 * non-zero exit status and prints "CASE FAIL".
 */
#include <assuan.h>
#include <gpg-error.h>

#include <signal.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int cases = 0;

static void case_pass(const char *name) {
    cases++;
    printf("CASE PASS: %s\n", name);
}

static void case_fail(const char *name, const char *detail) {
    printf("CASE FAIL: %s (%s)\n", name, detail);
}

static gpg_error_t echo_handler(assuan_context_t ctx, char *line) {
    return assuan_send_data(ctx, line, strlen(line));
}

struct response_buffer {
    char data[64];
    size_t length;
};

static gpg_error_t collect_data(void *opaque, const void *buffer, size_t length) {
    struct response_buffer *output = opaque;

    if (!buffer) {
        return 0;
    }
    if (length > sizeof(output->data) - output->length - 1) {
        return gpg_error(GPG_ERR_TOO_LARGE);
    }
    memcpy(output->data + output->length, buffer, length);
    output->length += length;
    output->data[output->length] = '\0';
    return 0;
}

static int run_server(int fd) {
    assuan_context_t ctx = NULL;
    gpg_error_t err;
    int context_owns_fd = 0;

    err = assuan_new(&ctx);
    if (!err) {
        assuan_fd_t assuan_fd = assuan_fd_from_posix_fd(fd);
        err = assuan_init_socket_server(ctx, assuan_fd, ASSUAN_SOCKET_SERVER_ACCEPTED);
        context_owns_fd = !err;
    }
    if (!err) {
        err = assuan_register_command(ctx, "ECHO", echo_handler, NULL);
    }
    if (!err) {
        err = assuan_accept(ctx);
    }
    if (!err) {
        err = assuan_process(ctx);
    }

    assuan_release(ctx);
    if (!context_owns_fd) {
        close(fd);
    }
    return err ? 1 : 0;
}

int main(void) {
    const char *version;
    assuan_context_t ctx = NULL;
    gpg_error_t err;
    int sockets[2];
    pid_t child;
    int status;
    struct response_buffer response = {{0}, 0};
    int context_owns_fd = 0;

    alarm(30);
    signal(SIGPIPE, SIG_IGN);

    /* 1. Version / ABI compatibility */
    version = assuan_check_version("3.0.2");
    if (!version || strcmp(version, "3.0.2") < 0) {
        case_fail("version", version ? version : "null");
        return 1;
    }
    case_pass("version");

    /* 2. Create a local Unix socketpair for the client/server pair */
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) != 0) {
        int saved_errno = errno;
        case_fail("socketpair", strerror(saved_errno));
        return 2;
    }
    case_pass("socketpair");

    /* 3. Spawn the Assuan server (socket server over the accepted fd) */
    child = fork();
    if (child < 0) {
        perror("fork");
        case_fail("fork-server", "fork failed");
        close(sockets[0]);
        close(sockets[1]);
        return 3;
    }
    if (child == 0) {
        close(sockets[0]);
        _exit(run_server(sockets[1]));
    }
    case_pass("fork-server");

    /* 4. Client: ECHO data round-trip over the Assuan socket */
    close(sockets[1]);
    err = assuan_new(&ctx);
    if (!err) {
        context_owns_fd = 1;
        err = assuan_socket_connect_fd(ctx, assuan_fd_from_posix_fd(sockets[0]), 0);
    }
    if (!err) {
        err = assuan_transact(
            ctx, "ECHO OpenHarmony", collect_data, &response, NULL, NULL, NULL, NULL
        );
    }
    if (!err && strcmp(response.data, "OpenHarmony") != 0) {
        err = gpg_error(GPG_ERR_BAD_DATA);
    }
    if (!err) {
        case_pass("echo-transaction");
    } else {
        case_fail("echo-transaction", gpg_strerror(err));
        assuan_release(ctx);
        if (!context_owns_fd) {
            close(sockets[0]);
        }
        return 4;
    }

    /* 5. Client: clean BYE close; server must exit 0 */
    err = assuan_transact(ctx, "BYE", NULL, NULL, NULL, NULL, NULL, NULL);

    assuan_release(ctx);
    if (!context_owns_fd) {
        close(sockets[0]);
    }
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status)) {
        case_fail("bye-close", "server did not exit cleanly");
        return 5;
    }
    if (err) {
        case_fail("bye-close", gpg_strerror(err));
        return 5;
    }
    case_pass("bye-close");

    alarm(0);
    printf("libassuan client/server transaction passed: %d cases\n", cases);
    return 0;
}

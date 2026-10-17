/* End-to-end consumer for pwauth on HarmonyOS PC.
 *
 * This program does exactly what Apache mod_authnz_external does with pwauth:
 * it spawns the installed authenticator, writes "<login>\n<password>\n" to its
 * stdin and takes the exit status as the authentication result.  The test
 * driver (test.sh) uses it to verify a complete authentication flow, including
 * a successful login through PAM.
 *
 * usage: test_consumer <pwauth-binary> <login> <password>
 * exit : the exit status reported by pwauth (127 when pwauth cannot be
 *        executed, 128+N when it was killed by signal N, 126 on internal
 *        errors such as pipe()/fork()/waitpid() failures).
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int run_authenticator(const char *binary, const char *login, const char *password)
{
    int fds[2];
    pid_t pid;
    int status;
    int written;
    char credentials[1024];
    size_t len;

    if (pipe(fds) != 0) {
        fprintf(stderr, "consumer: pipe: %s\n", strerror(errno));
        return 126;
    }

    pid = fork();
    if (pid < 0) {
        fprintf(stderr, "consumer: fork: %s\n", strerror(errno));
        return 126;
    }
    if (pid == 0) {
        /* child: pwauth reads the credentials from stdin */
        close(fds[1]);
        if (dup2(fds[0], STDIN_FILENO) < 0) {
            _exit(126);
        }
        close(fds[0]);
        execl(binary, binary, (char *)0);
        _exit(127);
    }

    /* parent: send the credentials and collect the exit status */
    close(fds[0]);
    len = (size_t)snprintf(credentials, sizeof(credentials), "%s\n%s\n", login, password);
    if (len >= sizeof(credentials)) {
        len = sizeof(credentials) - 1;
    }
    written = (int)write(fds[1], credentials, len);
    if (written < 0) {
        /* pwauth may already have exited (e.g. on a usage error); the exit
         * status below is what matters, so this is not fatal. */
        fprintf(stderr, "consumer: write to pwauth stdin: %s\n", strerror(errno));
    }
    close(fds[1]);

    if (waitpid(pid, &status, 0) < 0) {
        fprintf(stderr, "consumer: waitpid: %s\n", strerror(errno));
        return 126;
    }
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    return 126;
}

int main(int argc, char **argv)
{
    const char *binary;
    const char *login;
    const char *password;
    int rc;

    if (argc != 4) {
        fprintf(stderr, "usage: %s <pwauth-binary> <login> <password>\n", argv[0]);
        return 2;
    }
    binary = argv[1];
    login = argv[2];
    password = argv[3];

    rc = run_authenticator(binary, login, password);
    printf("consumer: authenticated '%s' via %s -> pwauth exit %d\n", login, binary, rc);
    return rc;
}

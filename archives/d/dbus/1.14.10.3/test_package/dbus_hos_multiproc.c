/* HarmonyOS-specific multi-process D-Bus integration test — orchestrator.
 *
 * Runs the *shipped package artifacts* in a real, sandbox-local D-Bus setup:
 *   - dbus-daemon from the package, listening on a pathname AF_UNIX socket
 *     created in a directory this run has just probed (the platform only
 *     allows pathname AF_UNIX in some sandbox directories);
 *   - a separate service process (dbus_hos_service) owning a well-known name;
 *   - separate client processes (dbus_hos_client), each with its own D-Bus
 *     connection and its own PID.
 *
 * The test only passes when the whole business chain executes:
 *   probe dir -> start daemon (EXTERNAL auth) -> service owns name ->
 *   client request with a run-unique token -> service-processed reply matches
 *   -> service-emitted signal with the token arrives at the client ->
 *   service exits gracefully -> name released -> a later client call gets the
 *   explicit org.freedesktop.DBus.Error.ServiceUnknown error (no hang, no
 *   stale reply) -> cleanup of every process/socket/temp file this run made.
 *
 * Every wait has a timeout; any failure -> non-zero exit.  Nothing outside
 * this run's own directory and own PIDs is ever touched.
 *
 * Usage:   ./dbus_hos_multiproc [<path-to-dbus-daemon>]
 *   env HOS_DBUS_DAEMON      path to the packaged dbus-daemon (fallback)
 *   env HOS_DBUS_SERVICE_BIN path to dbus_hos_service  (default: next to us)
 *   env HOS_DBUS_CLIENT_BIN  path to dbus_hos_client   (default: next to us)
 *   env HOS_DBUS_PW_SHIM     optional getpwuid/getpwuid_r LD_PRELOAD shim,
 *                            given to the daemon only (see the runner notes)
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define HOS_NAME "org.ohos.HosDbusTest"
#define HOS_PATH "/org/ohos/HosDbusTest"

static char g_token[128];
static int g_failures;
static pid_t g_daemon_child = -1;
static pid_t g_service_child = -1;

static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
    fflush(stdout);
}

static void fail(const char *fmt, ...) {
    va_list ap;
    printf("HOS-FAIL ");
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
    fflush(stdout);
    g_failures++;
}

static void check(const char *what, int ok) {
    say("HOS-CHECK %-58s %s", what, ok ? "ok" : "FAIL");
    if (!ok)
        g_failures++;
}

static long long now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static void sleep_ms(int ms) {
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

static int is_dir(const char *p) {
    struct stat st;
    return stat(p, &st) == 0 && S_ISDIR(st.st_mode);
}

static int rm_rf(const char *path) {
    DIR *d = opendir(path);
    struct dirent *e;
    if (d == NULL)
        return errno == ENOENT ? 0 : -1;
    while ((e = readdir(d)) != NULL) {
        char child[PATH_MAX];
        struct stat st;
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, ".."))
            continue;
        snprintf(child, sizeof(child), "%s/%s", path, e->d_name);
        if (lstat(child, &st) == 0 && S_ISDIR(st.st_mode))
            rm_rf(child);
        else
            unlink(child);
    }
    closedir(d);
    return rmdir(path);
}

/* ---- signal handling: never leave our own children behind --------------- */
static void on_term(int sig) {
    (void)sig;
    if (g_service_child > 0)
        kill(g_service_child, SIGKILL);
    if (g_daemon_child > 0)
        kill(g_daemon_child, SIGKILL);
    _exit(130);
}

/* ---- pathname AF_UNIX probe --------------------------------------------- */
/* The device does not allow pathname AF_UNIX everywhere: /tmp is a read-only
 * erofs, hmdfs ($HOME, and $TMPDIR points into it in the login session)
 * answers bind() with EPERM, while the app-sandbox dirs under
 * /data/storage/el2/base/ do accept sockets.  So probe instead of assuming:
 * bind + listen + connect + accept a real socket, and read SO_PEERCRED. */
static int probe_dir(const char *dir, char *why, size_t whylen) {
    char pdir[PATH_MAX], spath[PATH_MAX];
    struct sockaddr_un sa;
    struct ucred cr;
    socklen_t crlen = sizeof(cr);
    int srv = -1, cli = -1, acc = -1, rc = -1;

    if (snprintf(pdir, sizeof(pdir), "%s/hos-dbus-probe-%s", dir, g_token)
            >= (int)sizeof(pdir)) {
        snprintf(why, whylen, "path too long");
        return -1;
    }
    rm_rf(pdir);
    if (mkdir(pdir, 0700) != 0) {
        snprintf(why, whylen, "mkdir errno=%d (%s)", errno, strerror(errno));
        return -1;
    }
    snprintf(spath, sizeof(spath), "%s/sock", pdir);

    srv = socket(AF_UNIX, SOCK_STREAM, 0);
    if (srv < 0) {
        snprintf(why, whylen, "socket errno=%d (%s)", errno, strerror(errno));
        goto out;
    }
    memset(&sa, 0, sizeof(sa));
    sa.sun_family = AF_UNIX;
    strncpy(sa.sun_path, spath, sizeof(sa.sun_path) - 1);
    unlink(spath);
    if (bind(srv, (struct sockaddr *)&sa, sizeof(sa)) != 0) {
        snprintf(why, whylen, "bind errno=%d (%s)", errno, strerror(errno));
        goto out;
    }
    if (listen(srv, 4) != 0) {
        snprintf(why, whylen, "listen errno=%d (%s)", errno, strerror(errno));
        goto out;
    }
    cli = socket(AF_UNIX, SOCK_STREAM, 0);
    if (cli < 0 || connect(cli, (struct sockaddr *)&sa, sizeof(sa)) != 0) {
        snprintf(why, whylen, "connect errno=%d (%s)", errno, strerror(errno));
        goto out;
    }
    acc = accept(srv, NULL, NULL);
    if (acc < 0) {
        snprintf(why, whylen, "accept errno=%d (%s)", errno, strerror(errno));
        goto out;
    }
    if (getsockopt(acc, SOL_SOCKET, SO_PEERCRED, &cr, &crlen) == 0)
        snprintf(why, whylen, "peer_pid=%d peer_uid=%u peer_gid=%u",
                 (int)cr.pid, (unsigned)cr.uid, (unsigned)cr.gid);
    else
        snprintf(why, whylen, "peercred errno=%d (%s)", errno, strerror(errno));
    rc = 0;
out:
    if (acc >= 0) close(acc);
    if (cli >= 0) close(cli);
    if (srv >= 0) close(srv);
    unlink(spath);
    rmdir(pdir);
    return rc;
}

/* ---- child output capture (service/daemon pipes) ------------------------ */
struct cap {
    int fd;
    char buf[16384];   /* full captured text, for cross-checks */
    size_t len;
    char line[1024];   /* partially received line */
    size_t line_len;
    int ready;
    const char *prefix;
};

static void cap_echo_line(struct cap *c, const char *line) {
    if (strstr(line, "READY"))
        c->ready = 1;
    say("%s| %s", c->prefix, line);
}

static void cap_drain(struct cap *c) {
    char tmp[1024];
    ssize_t n;
    int eof = 0;
    if (c->fd < 0)
        return;
    while ((n = read(c->fd, tmp, sizeof(tmp))) > 0) {
        size_t i;
        for (i = 0; i < (size_t)n; i++) {
            char ch = tmp[i];
            if (c->len < sizeof(c->buf) - 1)
                c->buf[c->len++] = ch;
            if (ch == '\n') {
                c->line[c->line_len] = '\0';
                cap_echo_line(c, c->line);
                c->line_len = 0;
            } else if (c->line_len < sizeof(c->line) - 1) {
                c->line[c->line_len++] = ch;
            }
        }
    }
    if (n == 0)
        eof = 1;
    if (eof && c->line_len > 0) {   /* flush a final unterminated line */
        c->line[c->line_len] = '\0';
        cap_echo_line(c, c->line);
        c->line_len = 0;
    }
}

static int wait_child(pid_t pid, int timeout_ms, int *exit_code,
                      void (*tick)(void)) {
    long long deadline = now_ms() + timeout_ms;
    for (;;) {
        int st;
        pid_t r = waitpid(pid, &st, WNOHANG);
        if (r == pid) {
            *exit_code = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
            return 0;
        }
        if (now_ms() >= deadline)
            return -1;
        if (tick)
            tick();
        sleep_ms(50);
    }
}

static struct cap g_daemon_cap;
static struct cap *g_service_cap;   /* for the tick below */
static void drain_service_tick(void) {
    if (g_service_cap)
        cap_drain(g_service_cap);
    if (g_daemon_cap.fd > 0)
        cap_drain(&g_daemon_cap);
}

/* ---- daemon start -------------------------------------------------------- */
static pid_t start_daemon(const char *daemon, const char *conf,
                          char *addr, size_t addr_len, int *daemon_pid) {
    int fds[2];
    pid_t pid;
    struct cap *c = &g_daemon_cap;

    if (pipe(fds) != 0)
        return -1;
    pid = fork();
    if (pid == 0) {
        const char *shim = getenv("HOS_DBUS_PW_SHIM");
        dup2(fds[1], 1);
        close(fds[0]);
        close(fds[1]);
        if (shim && *shim)
            setenv("LD_PRELOAD", shim, 1);
        execl(daemon, daemon, "--config-file", conf,
              "--print-address=1", "--print-pid=1", "--nofork", (char *)NULL);
        _exit(127);
    }
    close(fds[1]);
    if (pid < 0)
        return -1;

    memset(c, 0, sizeof(*c));
    c->fd = fds[0];
    c->prefix = "DAEMON";
    fcntl(c->fd, F_SETFL, O_NONBLOCK);
    {
        long long deadline = now_ms() + 10000;
        while (now_ms() < deadline && (!addr[0] || *daemon_pid <= 0)) {
            cap_drain(c);
            /* first line = address, second = pid; both end in c->buf */
            if (!addr[0]) {
                char *nl = strchr(c->buf, '\n');
                if (nl) {
                    *nl = '\0';
                    snprintf(addr, addr_len, "%s", c->buf);
                    memmove(c->buf, nl + 1,
                            c->len - (size_t)(nl + 1 - c->buf) + 1);
                    c->len = strlen(c->buf);
                }
            }
            if (addr[0] && *daemon_pid <= 0) {
                char *nl = strchr(c->buf, '\n');
                if (nl) {
                    *nl = '\0';
                    *daemon_pid = atoi(c->buf);
                    memmove(c->buf, nl + 1,
                            c->len - (size_t)(nl + 1 - c->buf) + 1);
                    c->len = strlen(c->buf);
                }
            }
            if (!addr[0] || *daemon_pid <= 0)
                sleep_ms(100);
        }
    }
    /* keep the pipe open: closing it would turn any later daemon write into
     * SIGPIPE; the fd is drained from the tick below instead */
    return pid;
}

/* ---- clients ------------------------------------------------------------- */
/* extra[] is a NULL-terminated argument list for the client binary. */
static int run_client(const char *bin, const char *tag,
                      char *const extra[], int timeout_ms) {
    pid_t pid = fork();
    int code = -1;
    if (pid == 0) {
        char *argv[10];
        int argc = 0;
        argv[argc++] = (char *)bin;
        while (extra[argc - 1] != NULL && argc < 9) {
            argv[argc] = extra[argc - 1];
            argc++;
        }
        argv[argc] = NULL;
        execv(bin, argv);
        _exit(127);
    }
    if (pid < 0) {
        fail("fork client %s: %s", tag, strerror(errno));
        return -1;
    }
    if (wait_child(pid, timeout_ms, &code, drain_service_tick) != 0) {
        kill(pid, SIGKILL);
        wait_child(pid, 2000, &code, NULL);
        fail("client %s timed out after %d ms (killed)", tag, timeout_ms);
        return -1;
    }
    say("HOS-CLIENT-%s pid=%d exit=%d", tag, (int)pid, code);
    return code;
}

/* ---- main ---------------------------------------------------------------- */
int main(int argc, char **argv) {
    const char *daemon = (argc > 1) ? argv[1] : getenv("HOS_DBUS_DAEMON");
    const char *svc_bin = getenv("HOS_DBUS_SERVICE_BIN");
    const char *cli_bin = getenv("HOS_DBUS_CLIENT_BIN");
    char self_dir[PATH_MAX], buf[PATH_MAX];
    char chosen[PATH_MAX] = "";
    char rundir[PATH_MAX] = "", conf[PATH_MAX] = "", sock[PATH_MAX] = "";
    char address[512] = "";
    int daemon_self_pid = -1;
    int svc_code = -1;
    int daemon_code = -1;
    const char *cands[8];
    char tok_sig[160];
    int i, n = 0, chosen_ok = 0;
    FILE *f;

    signal(SIGTERM, on_term);
    signal(SIGINT, on_term);

    /* run-unique token: pid + time + urandom */
    {
        unsigned int r = 0;
        FILE *rnd = fopen("/dev/urandom", "rb");
        if (rnd) {
            if (fread(&r, 1, sizeof(r), rnd) != sizeof(r))
                r = 0;
            fclose(rnd);
        }
        snprintf(g_token, sizeof(g_token), "hosdbus-%d-%ld-%08x",
                 (int)getpid(), (long)time(NULL), r);
    }
    say("HOS-RUN token=%s", g_token);

    /* resolve binaries */
    {
        ssize_t l = readlink("/proc/self/exe", self_dir, sizeof(self_dir) - 1);
        if (l <= 0) {
            say("HOS-RESULT FAIL cannot resolve /proc/self/exe");
            return 2;
        }
        self_dir[l] = '\0';
        { char *slash = strrchr(self_dir, '/');
          if (slash) *slash = '\0'; else strcpy(self_dir, "."); }
    }
    if (!svc_bin || !*svc_bin) {
        snprintf(buf, sizeof(buf), "%s/dbus_hos_service", self_dir);
        svc_bin = buf;
    }
    if (!cli_bin || !*cli_bin) {
        static char clip[PATH_MAX];
        snprintf(clip, sizeof(clip), "%s/dbus_hos_client", self_dir);
        cli_bin = clip;
    }
    if (!daemon || !*daemon) {
        say("HOS-RESULT FAIL no dbus-daemon path (argv[1] or HOS_DBUS_DAEMON)");
        return 2;
    }
    say("HOS-TOOLS daemon=%s service=%s client=%s", daemon, svc_bin, cli_bin);
    check("package dbus-daemon is executable", access(daemon, X_OK) == 0);
    check("service binary is executable", access(svc_bin, X_OK) == 0);
    check("client binary is executable", access(cli_bin, X_OK) == 0);
    if (g_failures)
        goto verdict;

    /* 1. probe for a directory that really supports pathname AF_UNIX */
    cands[n++] = getenv("TMPDIR");
    cands[n++] = "/data/storage/el2/base/tmp";
    cands[n++] = "/data/storage/el2/base/cache";
    cands[n++] = "/data/storage/el2/base/files";
    for (i = 0; i < n; i++) {
        char why[256] = "";
        int j, dup = 0;
        if (!cands[i] || !*cands[i])
            continue;
        for (j = 0; j < i; j++)
            if (cands[j] && !strcmp(cands[j], cands[i]))
                dup = 1;
        if (dup)
            continue;
        if (!is_dir(cands[i])) {
            say("HOS-PROBE dir=%s result=SKIP (does not exist)", cands[i]);
            continue;
        }
        if (probe_dir(cands[i], why, sizeof(why)) == 0) {
            say("HOS-PROBE dir=%s result=OK %s", cands[i], why);
            snprintf(chosen, sizeof(chosen), "%s", cands[i]);
            chosen_ok = 1;
            break;
        }
        say("HOS-PROBE dir=%s result=FAIL %s", cands[i], why);
    }
    check("sandbox dir supports pathname AF_UNIX (bind+listen+connect)", chosen_ok);
    if (!chosen_ok)
        goto verdict;
    say("HOS-CHOSEN rundir-base=%s", chosen);

    /* 2. this run's private directory, config, socket */
    snprintf(rundir, sizeof(rundir), "%s/hos-dbus-run-%s", chosen, g_token);
    snprintf(conf, sizeof(conf), "%s/bus.conf", rundir);
    snprintf(sock, sizeof(sock), "%s/bus.sock", rundir);
    if (mkdir(rundir, 0700) != 0) {
        fail("mkdir %s: %s", rundir, strerror(errno));
        goto verdict;
    }
    say("HOS-RUNDIR %s", rundir);

    f = fopen(conf, "w");
    if (f == NULL) {
        fail("cannot write bus config: %s", strerror(errno));
        goto cleanup;
    }
    fprintf(f,
        "<!DOCTYPE busconfig PUBLIC \"-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN\"\n"
        " \"http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd\">\n"
        "<busconfig>\n"
        "  <type>session</type>\n"
        "  <keep_umask/>\n"
        "  <listen>unix:path=%s</listen>\n"
        "  <auth>EXTERNAL</auth>\n"
        "  <policy context=\"default\">\n"
        "    <allow send_destination=\"*\" eavesdrop=\"true\"/>\n"
        "    <allow eavesdrop=\"true\"/>\n"
        "    <allow own=\"*\"/>\n"
        "  </policy>\n"
        "</busconfig>\n", sock);
    fclose(f);
    say("HOS-BUSCONF %s auth=EXTERNAL (no ANONYMOUS, no allow_anonymous)", conf);

    /* 3. start the packaged daemon on our socket */
    g_daemon_child = start_daemon(daemon, conf, address, sizeof(address),
                                  &daemon_self_pid);
    if (g_daemon_child <= 0 || !address[0] || daemon_self_pid <= 0) {
        fail("dbus-daemon did not announce an address+pid (child=%d)",
             (int)g_daemon_child);
        goto cleanup;
    }
    check("packaged dbus-daemon announced a real socket address",
          strncmp(address, "unix:path=", 10) == 0 &&
          strstr(address, sock) != NULL && kill(daemon_self_pid, 0) == 0);
    say("HOS-DAEMON child=%d pid=%d address=%s",
        (int)g_daemon_child, daemon_self_pid, address);

    /* 4. start the service process */
    {
        int fds[2];
        static struct cap scap;
        if (pipe(fds) != 0) {
            fail("pipe: %s", strerror(errno));
            goto cleanup;
        }
        g_service_child = fork();
        if (g_service_child == 0) {
            dup2(fds[1], 1);
            dup2(fds[1], 2);
            close(fds[0]);
            close(fds[1]);
            execl(svc_bin, svc_bin, address, g_token, (char *)NULL);
            _exit(127);
        }
        close(fds[1]);
        if (g_service_child < 0) {
            fail("fork service: %s", strerror(errno));
            goto cleanup;
        }
        memset(&scap, 0, sizeof(scap));
        scap.fd = fds[0];
        scap.prefix = "SERVICE";
        fcntl(scap.fd, F_SETFL, O_NONBLOCK);
        g_service_cap = &scap;

        {
            long long deadline = now_ms() + 10000;
            int alive = 1;
            while (now_ms() < deadline) {
                int st;
                cap_drain(&scap);
                if (scap.ready)
                    break;
                if (waitpid(g_service_child, &st, WNOHANG) == g_service_child) {
                    alive = 0;
                    break;
                }
                sleep_ms(50);
            }
            cap_drain(&scap);
            check("service process reached READY (name owned, object registered)",
                  alive && scap.ready);
            if (!alive || !scap.ready)
                goto cleanup;
        }
        say("HOS-SERVICE child=%d", (int)g_service_child);
    }

    /* 5. client A: full cross-process round trip */
    {
        char pidarg[32];
        char *args[7];
        snprintf(pidarg, sizeof(pidarg), "%d", (int)g_service_child);
        args[0] = "full";
        args[1] = address;
        args[2] = (char *)HOS_NAME;
        args[3] = (char *)HOS_PATH;
        args[4] = g_token;
        args[5] = pidarg;
        args[6] = NULL;
        check("client process A: request+signal+shutdown chain exits 0",
              run_client(cli_bin, "A", args, 30000) == 0);
    }

    /* 6. the service must now have exited on its own (graceful) */
    {
        int r = wait_child(g_service_child, 15000, &svc_code, drain_service_tick);
        cap_drain(g_service_cap);
        check("service process exited gracefully (exit code 0)", r == 0 && svc_code == 0);
        if (r != 0) {
            kill(g_service_child, SIGKILL);
            wait_child(g_service_child, 2000, &svc_code, NULL);
        }
        g_service_child = -1;
    }
    {
        snprintf(tok_sig, sizeof(tok_sig), "%s-sig", g_token);
        {
            char needle[256];
            snprintf(needle, sizeof(needle), "Echo request='%s'", g_token);
            check("service log shows it handled the run-unique request",
                  g_service_cap && strstr(g_service_cap->buf, needle) != NULL);
            snprintf(needle, sizeof(needle), "Pong emitted payload='%s'", tok_sig);
            check("service log shows it emitted the run-unique signal",
                  g_service_cap && strstr(g_service_cap->buf, needle) != NULL);
        }
    }

    /* 7. client B: the name is released */
    {
        char *args[4];
        args[0] = "name-gone";
        args[1] = address;
        args[2] = (char *)HOS_NAME;
        args[3] = NULL;
        check("client process B: well-known name has no owner after exit",
              run_client(cli_bin, "B", args, 15000) == 0);
    }

    /* 8. client C: an explicit no-service error, no hang and no stale reply */
    {
        char *args[6];
        args[0] = "call-after-exit";
        args[1] = address;
        args[2] = (char *)HOS_NAME;
        args[3] = (char *)HOS_PATH;
        args[4] = g_token;
        args[5] = NULL;
        check("client process C: explicit no-service error (not a timeout)",
              run_client(cli_bin, "C", args, 15000) == 0);
    }

cleanup:
    /* 9. cleanup: our daemon, our socket, our files — nothing else */
    if (g_service_child > 0) {
        kill(g_service_child, SIGKILL);
        wait_child(g_service_child, 2000, &svc_code, NULL);
        g_service_child = -1;
    }
    if (g_daemon_child > 0) {
        kill(g_daemon_child, SIGTERM);
        if (wait_child(g_daemon_child, 5000, &daemon_code, NULL) != 0) {
            kill(g_daemon_child, SIGKILL);
            wait_child(g_daemon_child, 2000, &daemon_code, NULL);
        }
        say("HOS-CLEANUP daemon pid=%d exit=%d", (int)g_daemon_child, daemon_code);
        g_daemon_child = -1;
    }
    if (rundir[0]) {
        if (g_failures == 0) {
            if (rm_rf(rundir) != 0 && errno != ENOENT)
                fail("rundir removal: %s", strerror(errno));
            check("rundir/socket/config removed", access(rundir, F_OK) != 0);
        } else {
            /* keep the evidence of a failed run for inspection */
            say("HOS-NOTE rundir kept for inspection (failures=%d): %s",
                g_failures, rundir);
        }
    }

verdict:
    if (g_failures == 0) {
        say("HOS-RESULT PASS (probe, daemon, service, client, signal, "
            "release, no-service error, cleanup)");
        return 0;
    }
    say("HOS-RESULT FAIL failed-checks=%d", g_failures);
    if (chosen[0] && rundir[0] && access(rundir, F_OK) == 0)
        say("HOS-NOTE rundir kept for inspection: %s", rundir);
    return 1;
}

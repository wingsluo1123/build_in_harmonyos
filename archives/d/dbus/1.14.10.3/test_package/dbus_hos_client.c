/* D-Bus client process for the HarmonyOS multi-process integration test.
 *
 * Every invocation is a separate process with its own D-Bus connection.  The
 * client never calls into the service directly: all traffic goes through the
 * packaged dbus-daemon, which routes it to the service process.
 *
 * Modes:
 *   full <address> <name> <path> <token> <expected-service-pid>
 *       Connect, Hello, then
 *         - ask the daemon for the owner PID/UID of <name> and check the PID
 *           is <expected-service-pid> and differs from our own PID;
 *         - ask the daemon for our *own* uid to prove this connection carries
 *           real uid credentials (EXTERNAL auth, not anonymous);
 *         - subscribe to the Pong signal;
 *         - call Echo(<token>) and require the reply to be "svc-ack:<token>";
 *         - call EmitPong(<token>-sig) and require the signal to arrive with
 *           that exact payload;
 *         - call Shutdown() so the service exits.
 *   name-gone <address> <name>
 *       Require org.freedesktop.DBus.NameHasOwner(<name>) == false.
 *   call-after-exit <address> <name> <path> <token>
 *       Call Echo again; require an explicit ServiceUnknown/NameHasNoOwner
 *       error reply instead of a hang or a stale answer.
 *
 * Exit codes: 0 all checks passed; 1 any check failed; 2 connect/Hello failed;
 *             64 usage error.
 */
#define _GNU_SOURCE
#include <dbus/dbus.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define HOS_IFACE "org.ohos.HosDbusTest"
#define HOS_BUS_IFACE "org.freedesktop.DBus"
#define HOS_BUS_PATH "/org/freedesktop/DBus"

static int g_failures;
static char g_signal_payload[512];
static int g_signal_seen;

static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
    fflush(stdout);
}

static void check(const char *what, int ok) {
    say("CLIENT-CHECK %-52s %s", what, ok ? "ok" : "FAIL");
    if (!ok)
        g_failures++;
}

static long long now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

/* ---- incoming signal filter --------------------------------------------- */
static DBusHandlerResult signal_filter(DBusConnection *conn, DBusMessage *msg,
                                       void *user_data) {
    (void)conn;
    (void)user_data;
    if (dbus_message_is_signal(msg, HOS_IFACE, "Pong")) {
        DBusError err;
        const char *payload = NULL;
        dbus_error_init(&err);
        if (dbus_message_get_args(msg, &err, DBUS_TYPE_STRING, &payload,
                                  DBUS_TYPE_INVALID) && payload) {
            snprintf(g_signal_payload, sizeof(g_signal_payload), "%s", payload);
            g_signal_seen = 1;
        }
        dbus_error_free(&err);
        return DBUS_HANDLER_RESULT_HANDLED;
    }
    return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
}

/* ---- blocking-style call implemented as async + dispatch loop ----------- */
static DBusMessage *call_with_optional_string(DBusConnection *conn,
                                              const char *dest,
                                              const char *path,
                                              const char *iface,
                                              const char *member,
                                              const char *string_arg,
                                              int timeout_ms,
                                              DBusError *err) {
    DBusMessage *msg, *reply = NULL;
    DBusPendingCall *pending = NULL;
    long long deadline;

    msg = dbus_message_new_method_call(dest, path, iface, member);
    if (msg == NULL) {
        dbus_set_error(err, DBUS_ERROR_NO_MEMORY, "new_method_call failed");
        return NULL;
    }
    if (string_arg != NULL) {
        const char *arg = string_arg;
        dbus_message_append_args(msg, DBUS_TYPE_STRING, &arg,
                                 DBUS_TYPE_INVALID);
    }
    if (!dbus_connection_send_with_reply(conn, msg, &pending, timeout_ms)) {
        dbus_message_unref(msg);
        dbus_set_error(err, DBUS_ERROR_NO_MEMORY, "send_with_reply failed");
        return NULL;
    }
    dbus_message_unref(msg);
    if (pending == NULL) {
        dbus_set_error(err, DBUS_ERROR_DISCONNECTED, "no pending call");
        return NULL;
    }
    dbus_connection_flush(conn);
    deadline = now_ms() + timeout_ms;
    while (!dbus_pending_call_get_completed(pending)) {
        if (now_ms() >= deadline)
            break;
        if (!dbus_connection_read_write_dispatch(conn, 100))
            break;
    }
    if (dbus_pending_call_get_completed(pending)) {
        reply = dbus_pending_call_steal_reply(pending);
    } else {
        dbus_set_error(err, DBUS_ERROR_NO_REPLY,
                       "no reply within %d ms (timed out)", timeout_ms);
    }
    dbus_pending_call_unref(pending);
    return reply;
}

static int reply_is_error(DBusMessage *reply) {
    return reply &&
           dbus_message_get_type(reply) == DBUS_MESSAGE_TYPE_ERROR;
}

/* ---- modes --------------------------------------------------------------- */
static int mode_full(const char *address, const char *name, const char *path,
                     const char *token, const char *expected_pid_str) {
    DBusError err;
    DBusConnection *conn;
    const char *unique;
    char sig_payload[160];
    int expected_pid = atoi(expected_pid_str);

    dbus_error_init(&err);
    conn = dbus_connection_open(address, &err);
    if (conn == NULL || !dbus_bus_register(conn, &err)) {
        fprintf(stderr, "client: connect/Hello failed: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        return 2;
    }
    unique = dbus_bus_get_unique_name(conn);
    say("CLIENT pid=%d unique=%s mode=full token=%s", (int)getpid(),
        unique ? unique : "?", token);

    /* the daemon tells us who owns the service name — a different PID must
     * own it than the one this client runs under */
    {
        DBusMessage *reply = call_with_optional_string(
            conn, HOS_BUS_IFACE, HOS_BUS_PATH, HOS_BUS_IFACE,
            "GetConnectionUnixProcessID", name, 5000, &err);
        dbus_uint32_t owner_pid = 0;
        int ok = reply && !reply_is_error(reply) &&
                 dbus_message_get_args(reply, &err, DBUS_TYPE_UINT32, &owner_pid,
                                       DBUS_TYPE_INVALID);
        say("CLIENT service pid (via daemon)=%u own pid=%d expected=%d",
            (unsigned)owner_pid, (int)getpid(), expected_pid);
        check("service runs in a different process (daemon-reported pid)",
              ok && owner_pid != 0 && owner_pid != (dbus_uint32_t)getpid() &&
              owner_pid == (dbus_uint32_t)expected_pid);
        if (!ok)
            fprintf(stderr, "client: GetConnectionUnixProcessID: %s: %s\n",
                    err.name ? err.name : "?", err.message ? err.message : "?");
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
        dbus_error_init(&err);
    }
    {
        DBusMessage *reply = call_with_optional_string(
            conn, HOS_BUS_IFACE, HOS_BUS_PATH, HOS_BUS_IFACE,
            "GetConnectionUnixUser", name, 5000, &err);
        dbus_uint32_t owner_uid = 0;
        int ok = reply && !reply_is_error(reply) &&
                 dbus_message_get_args(reply, &err, DBUS_TYPE_UINT32,
                                       &owner_uid, DBUS_TYPE_INVALID);
        say("CLIENT service uid (via daemon)=%u own uid=%u",
            ok ? (unsigned)owner_uid : 0xffffffffu, (unsigned)getuid());
        check("owner uid reported by the daemon equals ours (EXTERNAL creds)",
              ok && owner_uid == (dbus_uint32_t)getuid());
        if (!ok)
            fprintf(stderr, "client: GetConnectionUnixUser(%s): %s: %s\n",
                    name, err.name ? err.name : "?",
                    err.message ? err.message : "?");
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
        dbus_error_init(&err);
    }
    {
        DBusMessage *reply = call_with_optional_string(
            conn, HOS_BUS_IFACE, HOS_BUS_PATH, HOS_BUS_IFACE,
            "GetConnectionUnixUser", unique, 5000, &err);
        dbus_uint32_t me_uid = 0;
        int ok = reply && !reply_is_error(reply) &&
                 dbus_message_get_args(reply, &err, DBUS_TYPE_UINT32, &me_uid,
                                       DBUS_TYPE_INVALID);
        say("CLIENT own uid reported by daemon=%u",
            ok ? (unsigned)me_uid : 0xffffffffu);
        check("this client connection carries a real uid (not anonymous)",
              ok && me_uid == (dbus_uint32_t)getuid());
        if (!ok)
            fprintf(stderr, "client: GetConnectionUnixUser(%s): %s: %s\n",
                    unique, err.name ? err.name : "?",
                    err.message ? err.message : "?");
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
        dbus_error_init(&err);
    }

    /* subscribe to the service's signal before asking for it */
    dbus_bus_add_match(conn,
                       "type='signal',interface='" HOS_IFACE
                       "',member='Pong'",
                       &err);
    check("client subscribed to the Pong signal", !dbus_error_is_set(&err));
    dbus_error_free(&err);
    dbus_error_init(&err);
    dbus_connection_add_filter(conn, signal_filter, NULL, NULL);

    /* business request with the run-unique token */
    {
        char expected[512];
        DBusMessage *reply = call_with_optional_string(
            conn, name, path, HOS_IFACE, "Echo", token, 8000, &err);
        const char *echoed = NULL;
        int ok = reply && !reply_is_error(reply) &&
                 dbus_message_get_args(reply, &err, DBUS_TYPE_STRING, &echoed,
                                       DBUS_TYPE_INVALID);
        snprintf(expected, sizeof(expected), "svc-ack:%s", token);
        say("CLIENT request Echo('%s') -> reply='%s'", token,
            ok ? echoed : "(error)");
        check("client received the service-processed reply for its request",
              ok && echoed && strcmp(echoed, expected) == 0);
        if (reply) dbus_message_unref(reply);
        if (!ok && dbus_error_is_set(&err))
            fprintf(stderr, "client: Echo: %s: %s\n", err.name, err.message);
        dbus_error_free(&err);
        dbus_error_init(&err);
    }

    /* ask the service to emit the run-unique signal */
    snprintf(sig_payload, sizeof(sig_payload), "%s-sig", token);
    {
        DBusMessage *reply = call_with_optional_string(
            conn, name, path, HOS_IFACE, "EmitPong", sig_payload, 8000, &err);
        check("client asked the service to emit the run-unique signal",
              reply && !reply_is_error(reply));
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
        dbus_error_init(&err);
    }
    {
        long long deadline = now_ms() + 8000;
        while (!g_signal_seen && now_ms() < deadline) {
            if (!dbus_connection_read_write_dispatch(conn, 100))
                break;
        }
        say("CLIENT signal Pong payload='%s' (expected '%s-sig')",
            g_signal_seen ? g_signal_payload : "(none)", token);
        check("client received the run-unique signal from the service",
              g_signal_seen &&
              strcmp(g_signal_payload, sig_payload) == 0);
    }

    /* graceful shutdown of the service */
    {
        DBusMessage *reply = call_with_optional_string(conn, name, path,
                                                       HOS_IFACE, "Shutdown",
                                                       NULL, 8000, &err);
        check("client asked the service to shut down (reply received)",
              reply && !reply_is_error(reply));
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
    }

    dbus_connection_remove_filter(conn, signal_filter, NULL);
    dbus_connection_unref(conn);
    say("CLIENT mode=full done failures=%d", g_failures);
    return g_failures ? 1 : 0;
}

static int mode_name_gone(const char *address, const char *name) {
    DBusError err;
    DBusConnection *conn;
    int ret;

    dbus_error_init(&err);
    conn = dbus_connection_open(address, &err);
    if (conn == NULL || !dbus_bus_register(conn, &err)) {
        fprintf(stderr, "client: connect/Hello failed: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        return 2;
    }
    say("CLIENT pid=%d unique=%s mode=name-gone name=%s", (int)getpid(),
        dbus_bus_get_unique_name(conn), name);
    {
        DBusMessage *reply = call_with_optional_string(
            conn, HOS_BUS_IFACE, HOS_BUS_PATH, HOS_BUS_IFACE, "NameHasOwner",
            name, 5000, &err);
        dbus_bool_t has_owner = 1;
        int ok = reply && !reply_is_error(reply) &&
                 dbus_message_get_args(reply, &err, DBUS_TYPE_BOOLEAN,
                                       &has_owner, DBUS_TYPE_INVALID);
        say("CLIENT NameHasOwner('%s')=%s", name,
            ok ? (has_owner ? "true" : "false") : "(error)");
        check("well-known name is released after the service exited",
              ok && has_owner == 0);
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
    }
    dbus_connection_unref(conn);
    ret = g_failures ? 1 : 0;
    say("CLIENT mode=name-gone done failures=%d", g_failures);
    return ret;
}

static int mode_call_after_exit(const char *address, const char *name,
                                const char *path, const char *token) {
    static const char *const expected_errs[] = {
        "org.freedesktop.DBus.Error.ServiceUnknown",
        "org.freedesktop.DBus.Error.NameHasNoOwner",
        NULL
    };
    DBusError err;
    DBusConnection *conn;
    int i, matched = 0, ret;

    dbus_error_init(&err);
    conn = dbus_connection_open(address, &err);
    if (conn == NULL || !dbus_bus_register(conn, &err)) {
        fprintf(stderr, "client: connect/Hello failed: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        return 2;
    }
    say("CLIENT pid=%d unique=%s mode=call-after-exit name=%s", (int)getpid(),
        dbus_bus_get_unique_name(conn), name);
    {
        long long t0 = now_ms();
        DBusMessage *reply = call_with_optional_string(conn, name, path,
                                                       HOS_IFACE, "Echo", token,
                                                       5000, &err);
        long long elapsed = now_ms() - t0;
        if (reply_is_error(reply)) {
            const char *ename = dbus_message_get_error_name(reply);
            say("CLIENT got error reply name='%s' after %lld ms",
                ename ? ename : "?", elapsed);
            for (i = 0; expected_errs[i]; i++)
                if (ename && strcmp(ename, expected_errs[i]) == 0)
                    matched = 1;
            check("call after exit fails with an explicit no-service error",
                  matched);
        } else if (reply != NULL) {
            const char *payload = NULL;
            (void)dbus_message_get_args(reply, &err, DBUS_TYPE_STRING, &payload,
                                        DBUS_TYPE_INVALID);
            say("CLIENT unexpectedly got a reply (stale service?): '%s'",
                payload ? payload : "?");
            check("no stale reply from the dead service", 0);
        } else {
            say("CLIENT no reply at all after %lld ms (error=%s) — hang",
                elapsed, err.name ? err.name : "?");
            check("no hang: an explicit error arrives quickly", 0);
        }
        if (reply) dbus_message_unref(reply);
        dbus_error_free(&err);
    }
    dbus_connection_unref(conn);
    ret = g_failures ? 1 : 0;
    say("CLIENT mode=call-after-exit done failures=%d", g_failures);
    return ret;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr,
                "usage: %s full|name-gone|call-after-exit <address> ...\n",
                argv[0]);
        return 64;
    }
    if (strcmp(argv[1], "full") == 0 && argc == 7)
        return mode_full(argv[2], argv[3], argv[4], argv[5], argv[6]);
    if (strcmp(argv[1], "name-gone") == 0 && argc == 4)
        return mode_name_gone(argv[2], argv[3]);
    if (strcmp(argv[1], "call-after-exit") == 0 && argc == 6)
        return mode_call_after_exit(argv[2], argv[3], argv[4], argv[5]);
    fprintf(stderr, "client: bad arguments\n");
    return 64;
}

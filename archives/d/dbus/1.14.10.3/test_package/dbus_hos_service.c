/* D-Bus service process for the HarmonyOS multi-process integration test.
 *
 * This is a *separate* process (own PID, own D-Bus connection) from both the
 * daemon and the client.  It owns a well-known name, registers a business
 * object and runs a real message-dispatch loop until it is asked to shut
 * down, at which point it exits 0 so the daemon releases the name.
 *
 * Protocol (interface org.ohos.HosDbusTest, path /org/ohos/HosDbusTest):
 *   Echo(s)      -> s   reply "svc-ack:" + argument (derived from the request)
 *   EmitPong(s)  -> ()  emits signal Pong(s) on the bus
 *   Shutdown()   -> ()  replies, then exits cleanly
 *
 * Usage: dbus_hos_service <bus-address> <run-token>
 * Exit codes: 0 clean shutdown; 2 connect failed; 3 name not acquired;
 *             4 no Shutdown received within 120 s.
 */
#define _GNU_SOURCE
#include <dbus/dbus.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define HOS_NAME "org.ohos.HosDbusTest"
#define HOS_PATH "/org/ohos/HosDbusTest"
#define HOS_IFACE "org.ohos.HosDbusTest"

static const char *g_token = "";
static int g_quit = 0;

static void say(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
    fflush(stdout);
}

static DBusHandlerResult on_message(DBusConnection *conn, DBusMessage *msg,
                                    void *user_data) {
    DBusError err;
    (void)user_data;

    dbus_error_init(&err);

    if (dbus_message_is_method_call(msg, HOS_IFACE, "Echo")) {
        const char *arg = NULL;
        char reply_text[512];
        DBusMessage *reply;
        if (!dbus_message_get_args(msg, &err, DBUS_TYPE_STRING, &arg,
                                   DBUS_TYPE_INVALID)) {
            dbus_error_free(&err);
            return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
        }
        const char *out;
        snprintf(reply_text, sizeof(reply_text), "svc-ack:%s", arg);
        out = reply_text;
        say("SERVICE Echo request='%s' reply='%s'", arg, reply_text);
        reply = dbus_message_new_method_return(msg);
        if (reply == NULL)
            return DBUS_HANDLER_RESULT_NEED_MEMORY;
        dbus_message_append_args(reply, DBUS_TYPE_STRING, &out,
                                 DBUS_TYPE_INVALID);
        dbus_connection_send(conn, reply, NULL);
        dbus_connection_flush(conn);
        dbus_message_unref(reply);
        return DBUS_HANDLER_RESULT_HANDLED;
    }

    if (dbus_message_is_method_call(msg, HOS_IFACE, "EmitPong")) {
        const char *arg = NULL;
        DBusMessage *sig, *reply;
        if (!dbus_message_get_args(msg, &err, DBUS_TYPE_STRING, &arg,
                                   DBUS_TYPE_INVALID)) {
            dbus_error_free(&err);
            return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
        }
        sig = dbus_message_new_signal(HOS_PATH, HOS_IFACE, "Pong");
        if (sig == NULL)
            return DBUS_HANDLER_RESULT_NEED_MEMORY;
        {
            const char *payload = arg;
            dbus_message_append_args(sig, DBUS_TYPE_STRING, &payload,
                                     DBUS_TYPE_INVALID);
        }
        dbus_connection_send(conn, sig, NULL);
        dbus_connection_flush(conn);
        dbus_message_unref(sig);
        say("SERVICE Pong emitted payload='%s'", arg);
        reply = dbus_message_new_method_return(msg);
        if (reply) {
            dbus_connection_send(conn, reply, NULL);
            dbus_connection_flush(conn);
            dbus_message_unref(reply);
        }
        return DBUS_HANDLER_RESULT_HANDLED;
    }

    if (dbus_message_is_method_call(msg, HOS_IFACE, "Shutdown")) {
        DBusMessage *reply = dbus_message_new_method_return(msg);
        if (reply) {
            dbus_connection_send(conn, reply, NULL);
            dbus_connection_flush(conn);
            dbus_message_unref(reply);
        }
        say("SERVICE shutdown requested -> exiting cleanly");
        g_quit = 1;
        return DBUS_HANDLER_RESULT_HANDLED;
    }

    return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
}

static DBusObjectPathVTable vtable = {
    NULL, on_message, NULL, NULL, NULL, NULL
};

int main(int argc, char **argv) {
    const char *address, *unique;
    DBusError err;
    DBusConnection *conn;
    int rc, waited_ms = 0;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <bus-address> <run-token>\n", argv[0]);
        return 64;
    }
    address = argv[1];
    g_token = argv[2];

    dbus_error_init(&err);
    conn = dbus_connection_open(address, &err);
    if (conn == NULL) {
        fprintf(stderr, "service: dbus_connection_open: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        return 2;
    }
    if (!dbus_bus_register(conn, &err)) {
        fprintf(stderr, "service: dbus_bus_register: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        dbus_connection_unref(conn);
        return 2;
    }
    unique = dbus_bus_get_unique_name(conn);
    say("SERVICE pid=%d unique=%s token=%s", (int)getpid(),
        unique ? unique : "?", g_token);

    rc = dbus_bus_request_name(conn, HOS_NAME,
                               DBUS_NAME_FLAG_DO_NOT_QUEUE, &err);
    say("SERVICE name=%s request_rc=%d (PRIMARY_OWNER=%d)", HOS_NAME, rc,
        DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER);
    if (rc != DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER) {
        if (dbus_error_is_set(&err))
            fprintf(stderr, "service: request_name: %s: %s\n", err.name,
                    err.message);
        dbus_error_free(&err);
        dbus_connection_unref(conn);
        return 3;
    }

    if (!dbus_connection_register_object_path(conn, HOS_PATH, &vtable, NULL)) {
        fprintf(stderr, "service: register_object_path failed\n");
        dbus_connection_unref(conn);
        return 3;
    }
    say("SERVICE registered object %s (iface %s) on connection %s",
        HOS_PATH, HOS_IFACE, unique ? unique : "?");
    say("READY");

    while (!g_quit && waited_ms < 120000) {
        if (!dbus_connection_read_write_dispatch(conn, 200))
            break;   /* connection closed */
        waited_ms += 200;
    }
    if (!g_quit) {
        say("SERVICE ERROR no Shutdown within 120s -> exiting rc=4");
        dbus_connection_unregister_object_path(conn, HOS_PATH);
        dbus_connection_unref(conn);
        return 4;
    }

    dbus_connection_unregister_object_path(conn, HOS_PATH);
    dbus_connection_unref(conn);
    say("SERVICE exit rc=0 (name released with the connection)");
    return 0;
}

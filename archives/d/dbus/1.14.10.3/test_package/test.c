#include <dbus/dbus.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 消费方端到端用例（鸿蒙特有）：在真机上用本包产出的 libdbus-1.so 走完一条完整的
 * D-Bus 业务链路，而不是只做链接性/断言性检查：
 *
 *   1. 连接会话总线并 Hello（拿到唯一名）      —— 连接建立
 *   2. 向总线守护进程 Peer.Ping 往返            —— 客户端发起调用并收到回复
 *   3. 申请众所周知名 org.ohos.DbusConsumer     —— 服务方向总线上线
 *   4. 在 /ohos/consumer 注册服务对象（Echo）   —— 服务端对象树
 *   5. 内省守护进程 Introspectable.Introspect  —— 取回真实 XML 数据（非空应答）
 *   6. 以众所周知名为目的地调用自己注册的 Echo —— 调用经守护进程路由回本连接、
 *      由服务对象处理并原样返回参数（参数与返回值逐字节比对）
 *   7. 释放名字                                —— 下线
 *
 * 任一步失败即退出码非 0，并打印失败的那一步；无会话总线地址时如实说明失败原因，
 * 不伪造通过（退出码非 0）。
 */

/* 第 6 步的调用参数，回包必须与它逐字节相同 */
static const char *const kEchoText = "ohos-dbus-consumer-roundtrip";

static int check(const char *what, int ok) {
    printf("  [%s] %s\n", ok ? "ok" : "FAIL", what);
    fflush(stdout);
    return ok ? 0 : 1;
}

static void print_dbus_error(const char *stage, DBusError *err) {
    fprintf(stderr, "  %s failed: %s: %s\n", stage,
            err->name ? err->name : "(no name)",
            err->message ? err->message : "(no message)");
}

/* 服务端：把收到的字符串原样回给调用方 */
static DBusHandlerResult echo_handler(DBusConnection *conn, DBusMessage *msg,
                                      void *user_data) {
    const char *text = NULL;
    DBusMessage *reply = NULL;
    DBusError err;

    (void)user_data;
    if (!dbus_message_is_method_call(msg, "org.ohos.DbusConsumer", "Echo")) {
        return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
    }

    dbus_error_init(&err);
    if (!dbus_message_get_args(msg, &err, DBUS_TYPE_STRING, &text, DBUS_TYPE_INVALID)) {
        /* 参数不对：回一个错误，让调用方看到失败原因而不是超时 */
        reply = dbus_message_new_error(msg, DBUS_ERROR_INVALID_ARGS,
                                       "Echo expects one string");
        print_dbus_error("Echo arguments", &err);
        dbus_error_free(&err);
    } else {
        reply = dbus_message_new_method_return(msg);
        if (reply != NULL) {
            dbus_message_append_args(reply, DBUS_TYPE_STRING, &text, DBUS_TYPE_INVALID);
        }
    }
    if (reply == NULL) {
        return DBUS_HANDLER_RESULT_NEED_MEMORY;
    }
    dbus_connection_send(conn, reply, NULL);
    dbus_connection_flush(conn);
    dbus_message_unref(reply);
    return DBUS_HANDLER_RESULT_HANDLED;
}

static DBusObjectPathVTable echo_vtable = {
    NULL, echo_handler, NULL, NULL, NULL, NULL
};

static int consumer_flow(const char *address) {
    DBusError err;
    DBusConnection *conn = NULL;
    DBusMessage *msg = NULL, *reply = NULL;
    int failures = 0, registered_object = 0, got_name = 0;

    dbus_error_init(&err);
    conn = dbus_connection_open(address, &err);
    if (conn == NULL) {
        print_dbus_error("dbus_connection_open", &err);
        dbus_error_free(&err);
        return 1;
    }
    if (!dbus_bus_register(conn, &err)) {
        print_dbus_error("dbus_bus_register (Hello)", &err);
        dbus_error_free(&err);
        dbus_connection_unref(conn);
        return 1;
    }
    failures += check("connect + Hello (unique name assigned)",
                      dbus_bus_get_unique_name(conn) != NULL);

    /* 2. 客户端往返：Ping 守护进程 */
    msg = dbus_message_new_method_call("org.freedesktop.DBus", "/",
                                       "org.freedesktop.DBus.Peer", "Ping");
    reply = msg ? dbus_connection_send_with_reply_and_block(conn, msg, 5000, &err) : NULL;
    failures += check("client roundtrip: Peer.Ping -> method return",
                      reply != NULL &&
                      dbus_message_get_type(reply) == DBUS_MESSAGE_TYPE_METHOD_RETURN);
    if (reply == NULL) {
        print_dbus_error("Peer.Ping", &err);
        dbus_error_free(&err);
    }
    if (reply) { dbus_message_unref(reply); reply = NULL; }
    if (msg) { dbus_message_unref(msg); msg = NULL; }

    /* 3. 服务方上线：申请众所周知名 */
    {
        int rc = dbus_bus_request_name(conn, "org.ohos.DbusConsumer",
                                       DBUS_NAME_FLAG_DO_NOT_QUEUE, &err);
        got_name = (rc == DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER);
        failures += check("service: own name org.ohos.DbusConsumer (primary owner)",
                          got_name);
        if (!got_name) {
            print_dbus_error("dbus_bus_request_name", &err);
            dbus_error_free(&err);
        }
    }

    /* 4. 注册服务对象 */
    if (got_name) {
        registered_object = dbus_connection_register_object_path(
            conn, "/ohos/consumer", &echo_vtable, NULL);
        failures += check("service: register object /ohos/consumer (Echo)",
                          registered_object);
    }

    /* 5. 内省守护进程：必须是带内容的 XML，不是空应答 */
    msg = dbus_message_new_method_call("org.freedesktop.DBus",
                                       "/org/freedesktop/DBus",
                                       "org.freedesktop.DBus.Introspectable",
                                       "Introspect");
    reply = msg ? dbus_connection_send_with_reply_and_block(conn, msg, 5000, &err) : NULL;
    {
        const char *xml = NULL;
        int ok = reply != NULL &&
                 dbus_message_get_args(reply, &err, DBUS_TYPE_STRING, &xml,
                                       DBUS_TYPE_INVALID) &&
                 xml != NULL && strstr(xml, "<node") != NULL &&
                 strstr(xml, "org.freedesktop.DBus") != NULL;
        failures += check("client: introspect daemon -> XML listing the bus name", ok);
        if (!ok) {
            print_dbus_error("Introspect", &err);
            dbus_error_free(&err);
        }
    }
    if (reply) { dbus_message_unref(reply); reply = NULL; }
    if (msg) { dbus_message_unref(msg); msg = NULL; }

    /* 6. 端到端业务调用：以众所周知名为目的地调用自己注册的 Echo，
     *    消息经守护进程路由回本连接，由服务对象处理后原样返回。 */
    if (got_name && registered_object) {
        const char *echoed = NULL;
        int ok;
        msg = dbus_message_new_method_call("org.ohos.DbusConsumer",
                                           "/ohos/consumer",
                                           "org.ohos.DbusConsumer", "Echo");
        if (msg != NULL) {
            dbus_message_append_args(msg, DBUS_TYPE_STRING, &kEchoText,
                                     DBUS_TYPE_INVALID);
        }
        /* 注意：这一步必须自己跑分发循环。消息先经守护进程路由回本连接，
         * 只有把收到的调用分发给服务对象，Echo 才会应答；
         * dbus_connection_send_with_reply_and_block() 只等回包、不分发收到的调用，
         * 用它在这里会一直等到 NoReply 超时。 */
        if (msg != NULL) {
            DBusPendingCall *pending = NULL;
            int spins;
            if (dbus_connection_send_with_reply(conn, msg, &pending, 5000) && pending) {
                dbus_connection_flush(conn);
                for (spins = 0; spins < 100; spins++) {
                    if (dbus_pending_call_get_completed(pending)) break;
                    if (!dbus_connection_read_write_dispatch(conn, 100)) break;
                }
                if (dbus_pending_call_get_completed(pending)) {
                    reply = dbus_pending_call_steal_reply(pending);
                }
            }
            if (pending) dbus_pending_call_unref(pending);
        }
        ok = reply != NULL &&
             dbus_message_get_type(reply) == DBUS_MESSAGE_TYPE_METHOD_RETURN &&
             dbus_message_get_args(reply, &err, DBUS_TYPE_STRING, &echoed,
                                   DBUS_TYPE_INVALID) &&
             echoed != NULL && strcmp(echoed, kEchoText) == 0;
        failures += check("end-to-end: call own name -> daemon routes to our service "
                          "-> Echo reply matches the argument", ok);
        if (!ok) {
            print_dbus_error("Echo roundtrip", &err);
            dbus_error_free(&err);
        }
        if (reply) { dbus_message_unref(reply); reply = NULL; }
        if (msg) { dbus_message_unref(msg); msg = NULL; }
    }

    /* 7. 下线 */
    if (got_name) {
        int rc = dbus_bus_release_name(conn, "org.ohos.DbusConsumer", &err);
        failures += check("service: release name",
                          rc == DBUS_RELEASE_NAME_REPLY_RELEASED);
        if (rc != DBUS_RELEASE_NAME_REPLY_RELEASED) {
            print_dbus_error("dbus_bus_release_name", &err);
            dbus_error_free(&err);
        }
        if (registered_object) {
            dbus_connection_unregister_object_path(conn, "/ohos/consumer");
        }
    }

    dbus_connection_unref(conn);
    return failures == 0 ? 0 : 1;
}

int main(void) {
    const char *address = getenv("DBUS_SESSION_BUS_ADDRESS");
    DBusError err;
    DBusConnection *conn;
    int failures;

    if (address == NULL || *address == '\0') {
        /* 没有会话总线地址就不存在端到端链路；如实报错，不伪造通过 */
        fprintf(stderr, "FAIL: DBUS_SESSION_BUS_ADDRESS is not set — the consumer "
                        "flow needs a live bus, nothing is verified\n");
        return 1;
    }

    printf("DBUS_SESSION_BUS_ADDRESS=%s\n", address);
    failures = consumer_flow(address);
    if (failures == 0) {
        printf("dbus consumer flow: 7/7 checks passed\n");
    } else {
        printf("dbus consumer flow: %d check(s) FAILED\n", failures);
    }
    return failures == 0 ? 0 : 1;
}

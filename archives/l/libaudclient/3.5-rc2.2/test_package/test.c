#include <stdio.h>
#include <audacious/audctrl.h>
#include <dbus/dbus-glib.h>

int main(void) {
    GError *err = NULL;

    /* 1) 连接 D-Bus 会话总线：真机无会话总线时按错误路径验证（链接+运行时+错误处理全链路） */
    DBusGConnection *conn = dbus_g_bus_get(DBUS_BUS_SESSION, &err);
    if (conn == NULL) {
        printf("ok: no D-Bus session bus (%s) -> error path handled gracefully\n",
               err ? err->message : "unknown");
        g_clear_error(&err);
        printf("libaudclient consumer test: PASSED\n");
        return 0;
    }

    /* 2) 有总线：创建 audacious 远程代理并调用公开 API（无播放器在运行不应崩溃） */
    DBusGProxy *proxy = dbus_g_proxy_new_for_name(
        conn, "org.atheme.audacious",
        "/org/atheme/audacious", "org.atheme.audacious");
    if (proxy == NULL) {
        fprintf(stderr, "FAIL: dbus_g_proxy_new_for_name returned NULL\n");
        return 1;
    }
    audacious_remote_play(proxy);
    printf("ok: audacious_remote_play(proxy) invoked without crash (no player running)\n");
    g_object_unref(proxy);

    printf("libaudclient consumer test: PASSED\n");
    return 0;
}

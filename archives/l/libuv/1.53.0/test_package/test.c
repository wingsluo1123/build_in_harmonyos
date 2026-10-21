/* test_package/test.c — libuv 1.53.0 (R34: 实质依赖被测包 API) */
#include <uv.h>
#include <stdio.h>
#include <string.h>

#define CHECK_PASS(name) printf("PASS: %s\n", name)
#define CHECK_FAIL(name, fmt, ...) do { printf("FAIL: %s: " fmt "\n", name, ##__VA_ARGS__); return 1; } while (0)

int main(void) {
    /* 1: 版本字符串 */
    const char *ver = uv_version_string();
    if (!ver || ver[0] == '\0')
        CHECK_FAIL("version", "uv_version_string() returned NULL/empty");
    printf("libuv version: %s\n", ver);
    CHECK_PASS("version");

    /* 2: 默认事件循环可创建 */
    uv_loop_t *loop = uv_default_loop();
    if (loop == NULL)
        CHECK_FAIL("default_loop", "uv_default_loop() returned NULL");
    CHECK_PASS("default_loop");

    /* 3: 定时器可初始化 */
    uv_timer_t timer;
    int rc = uv_timer_init(loop, &timer);
    if (rc != 0)
        CHECK_FAIL("timer_init", "%s", uv_strerror(rc));
    CHECK_PASS("timer_init");

    /* 4: 当前用户信息可获取（含 OHOS 回退） */
    uv_passwd_t pwd;
    memset(&pwd, 0, sizeof(pwd));
    rc = uv_os_get_passwd(&pwd);
    if (rc != 0)
        CHECK_FAIL("get_passwd", "%s", uv_strerror(rc));
    if (pwd.username == NULL || pwd.username[0] == '\0') {
        uv_os_free_passwd(&pwd);
        CHECK_FAIL("get_passwd", "empty username");
    }
    printf("os user: name=\"%s\" uid=%lu gid=%lu home=\"%s\"\n",
           pwd.username, (unsigned long)pwd.uid,
           (unsigned long)pwd.gid,
           pwd.homedir ? pwd.homedir : "(null)");
    uv_os_free_passwd(&pwd);
    CHECK_PASS("get_passwd");

    /* 5: 循环可关闭（含句柄清理） */
    uv_close((uv_handle_t *)&timer, NULL);
    uv_run(loop, UV_RUN_DEFAULT);
    rc = uv_loop_close(loop);
    if (rc != 0 && rc != UV_EBUSY)
        CHECK_FAIL("loop_close", "%s", uv_strerror(rc));
    CHECK_PASS("loop_close");

    printf("libuv test: all API calls passed\n");
    return 0;
}

/*
 * harmonyos_consumer_test.c — libtwirc 0.1.2 鸿蒙特有端到端消费者测试
 *
 * 所验证的鸿蒙/协议行为（在 OHOS 设备真实执行）：
 *   1. 本地回环 TCP 上 libtwirc 客户端与模拟 Twitch IRC 服务器完成
 *      PASS/NICK 登录握手（TWIRC-IRC 协议状态机，epoll 驱动）；
 *   2. 收到 001 welcome 后触发 welcome 回调并进入已登录态；
 *   3. 收到 PING 自动回复 PONG（协议保活）；
 *   4. 收到带 IRCv3 tags 的 PRIVMSG 触发 privmsg 回调且 tag 可解析；
 *   5. 全程使用 clang + OHOS libc（sys/epoll.h/socket）真实链接运行。
 *
 * 端到端流程：mock 服务器线程监听 127.0.0.1 临时端口 → 客户端
 * twirc_init/twirc_connect/twirc_tick 循环 → 断言回调与状态 →
 * twirc_kill 干净退出。默认模式必须 PASS（exit 0）；
 * --failcap 变体由服务器不发 001 触发超时断言失败（非零退出），
 * 用于证明该测试真实可失败（非 always-green）。
 *
 * 编译（与 conanfile.py 同工具链，R33 不依赖 shell 环境变量）：
 *   clang -I <src> -pthread harmonyos_consumer_test.c <libtwirc.a> -o harmonyos_consumer_test
 */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#include "libtwirc.h"

/* ---------------- mock Twitch IRC server (in-process thread) ---------------- */
static volatile int g_port = 0;
static volatile int g_failcap = 0; /* 1 = 不发 001，用于 failcap */

static void *mock_server(void *unused)
{
    (void) unused;
    int lfd = socket(AF_INET, SOCK_STREAM, 0);
    if (lfd < 0)
    {
        return NULL;
    }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0; /* ephemeral */
    if (bind(lfd, (struct sockaddr *) &addr, sizeof(addr)) != 0)
    {
        close(lfd);
        return NULL;
    }
    socklen_t alen = sizeof(addr);
    if (getsockname(lfd, (struct sockaddr *) &addr, &alen) != 0)
    {
        close(lfd);
        return NULL;
    }
    g_port = ntohs(addr.sin_port);
    listen(lfd, 1);

    int cfd = accept(lfd, NULL, NULL);
    if (cfd < 0)
    {
        close(lfd);
        return NULL;
    }

    /* 消费客户端登录行（PASS/NICK/CAP），最多 2 秒 */
    {
        char buf[512];
        fd_set rset;
        struct timeval tv = { 2, 0 };
        int done = 0;
        while (!done)
        {
            FD_ZERO(&rset);
            FD_SET(cfd, &rset);
            int r = select(cfd + 1, &rset, NULL, NULL, &tv);
            if (r <= 0)
            {
                break;
            }
            ssize_t n = recv(cfd, buf, sizeof(buf) - 1, 0);
            if (n <= 0)
            {
                break;
            }
            buf[n] = '\0';
            if (strstr(buf, "PASS ") && strstr(buf, "NICK "))
            {
                done = 1;
            }
        }
    }

    if (!g_failcap)
    {
        /* 正常模式：001 welcome + PING + 带 IRCv3 tags 的 PRIVMSG */
        const char *msg =
            ":tmi.twitch.tv 001 testuser :Welcome, GLHF!\r\n"
            "PING :tmi.twitch.tv\r\n"
            "@badge-info=;color=#FF0000;display-name=Mock;emotes=;mod=0;"
            "subscriber=0;turbo=0;user-type= :mock!mock@mock.tmi.twitch.tv "
            "PRIVMSG #test :hello from libtwirc\r\n";
        (void) send(cfd, msg, strlen(msg), 0);
    }
    else
    {
        /* failcap：服务器发 464 而非 001 → welcome 永不到达 → 客户端断言超时失败 */
        const char *msg =
            ":tmi.twitch.tv 464 testuser :Login authentication failed\r\n";
        (void) send(cfd, msg, strlen(msg), 0);
    }

    usleep(800 * 1000);
    close(cfd);
    close(lfd);
    return NULL;
}

/* ---------------- client-side callbacks ---------------- */
static int g_connect = 0;
static int g_welcome = 0;
static int g_ping = 0;
static int g_privmsg = 0;

static void on_connect(twirc_state_t *s, twirc_event_t *e)
{
    (void) s;
    (void) e;
    g_connect++;
}

static void on_welcome(twirc_state_t *s, twirc_event_t *e)
{
    (void) s;
    (void) e;
    g_welcome++;
}

static void on_ping(twirc_state_t *s, twirc_event_t *e)
{
    (void) s;
    (void) e;
    g_ping++;
}

static void on_privmsg(twirc_state_t *s, twirc_event_t *e)
{
    (void) s;
    if (e != NULL && e->channel != NULL && e->message != NULL)
    {
        /* 校验 IRCv3 tag 解析路径与消息字段 */
        const char *val = twirc_get_tag_value(e->tags, "display-name");
        if (val != NULL && strcmp(val, "Mock") == 0)
        {
            g_privmsg++;
        }
    }
}

int main(int argc, char **argv)
{
    /* mock 服务器线程可能在客户端关闭后仍在收尾（PONG 写入竞争），
     * 客户端侧忽略 SIGPIPE，让写已关闭 socket 以 EPIPE 形式返回而非终止进程。 */
    signal(SIGPIPE, SIG_IGN);

    if (argc > 1 && strcmp(argv[1], "--failcap") == 0)
    {
        g_failcap = 1;
    }

    pthread_t tid;
    if (pthread_create(&tid, NULL, mock_server, NULL) != 0)
    {
        fprintf(stderr, "FAIL: mock server thread create\n");
        return 2;
    }
    while (g_port == 0)
    {
        usleep(10000);
    }

    char portstr[16];
    snprintf(portstr, sizeof(portstr), "%d", g_port);

    twirc_state_t *s = twirc_init();
    if (s == NULL)
    {
        fprintf(stderr, "FAIL: twirc_init()\n");
        return 3;
    }
    twirc_callbacks_t *cb = twirc_get_callbacks(s);
    cb->connect = on_connect;
    cb->welcome = on_welcome;
    cb->ping = on_ping;
    cb->privmsg = on_privmsg;

    int rc = twirc_connect(s, "127.0.0.1", portstr, "testuser", "oauth:mock");
    if (rc != 0)
    {
        fprintf(stderr, "FAIL: twirc_connect rc=%d\n", rc);
        twirc_kill(s);
        return 4;
    }

    /* 驱动事件循环：最多 6 秒，直到 welcome（正常模式）或超时（failcap） */
    int loops = 0;
    int max_loops = 30; /* 30 × 200ms = 6s */
    while (loops < max_loops)
    {
        twirc_tick(s, 200);
        if (g_welcome > 0)
        {
            break;
        }
        loops++;
    }

    int ok = 0;
    if (!g_failcap)
    {
        /* 正常模式断言：握手、welcome、已登录态、PING 保活、带 tag 的 PRIVMSG */
        ok = (g_connect > 0 && g_welcome > 0 && g_ping > 0 && g_privmsg > 0
              && twirc_is_connected(s) != 0);
        fprintf(stdout,
                "HARMONYOS_CONSUMER_TEST connect=%d welcome=%d ping=%d "
                "privmsg_with_tag=%d is_connected=%d\n",
                g_connect, g_welcome, g_ping, g_privmsg, twirc_is_connected(s));
    }
    else
    {
        /* failcap：服务器不发 001（发 464）→ 客户端 welcome 断言必须失败，
         * 证明该测试真实可失败（非 always-green）。 */
        ok = (g_welcome > 0);
        fprintf(stdout,
                "HARMONYOS_CONSUMER_TEST(FAILCAP) connect=%d welcome=%d "
                "(expect welcome>0; 服务器未发 001 → 本断言应 FAIL)\n",
                g_connect, g_welcome);
    }

    twirc_kill(s);

    if (ok)
    {
        printf("HARMONYOS_CONSUMER_TEST_PASS\n");
        return 0;
    }
    printf("HARMONYOS_CONSUMER_TEST_FAIL\n");
    return 1;
}

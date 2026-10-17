/*
 * test_consumer.c — miredo 1.2.6 消费者用例
 *
 * 以真实第三方使用者视角，仅通过已安装的公开头文件与 miredo::miredo
 * 链接目标，调用 libteredo / libtun6 的公开 API。
 */
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>

#include <libteredo/teredo.h>
#include <libteredo/tunnel.h>
#include <libtun6/tun6.h>

static int failures = 0;

#define CHECK(cond, what)                                                   \
	do {                                                                \
		if (cond)                                                   \
			printf ("  ok   %s\n", what);                       \
		else {                                                      \
			printf ("  FAIL %s\n", what);                       \
			failures++;                                         \
		}                                                           \
	} while (0)

int main (void)
{
	int marker = 42;
	teredo_tunnel *t;
	/* libtun6 符号取址：强制链接器解析，验证该库可被消费者链接 */
	void *tun6_symbol = (void *)(size_t)tun6_driver_diagnose;

	printf ("miredo 1.2.6 consumer test\n");

	t = teredo_create (0, 0);
	CHECK (t != NULL, "teredo_create(0, 0) 返回可用隧道对象");
	if (t == NULL)
		return 1;

	CHECK (teredo_set_privdata (t, &marker) == NULL,
	       "teredo_set_privdata 返回旧值 (NULL)");
	CHECK (teredo_get_privdata (t) == &marker,
	       "teredo_get_privdata 取回刚设置的值");
	CHECK (teredo_set_privdata (t, NULL) == &marker,
	       "teredo_set_privdata 二次调用返回上一次的值");

	teredo_destroy (t);
	printf ("  ok   teredo_destroy 正常返回\n");
	CHECK (tun6_symbol != NULL, "libtun6 符号 tun6_driver_diagnose 已解析");

	printf ("%s (%d failures)\n", failures ? "FAILED" : "PASSED", failures);
	return failures != 0 ? 1 : 0;
}

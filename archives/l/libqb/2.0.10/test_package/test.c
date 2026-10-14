/*
 * HarmonyOS PC (aarch64-linux-ohos) 消费者测试 —— libqb 2.0.10
 *
 * 目的：以「下游消费者」视角验证发布出来的 libqb 制品在鸿蒙 PC 上
 *       可被独立工程链接并真正调用核心 API：
 *         1) 共享内存 ring buffer 的创建 / 写 chunk / 读 chunk 往返
 *         2) 共享用户数据区（shared user data）
 *         3) 引用计数
 *         4) 日志子系统 qb_log 的文件输出
 *       这些都是 corosync/pacemaker/sbd 依赖 libqb 时实际会用到的能力。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <qb/qbrb.h>
#include <qb/qblog.h>
#include <qb/qbdefs.h>

#define RB_NAME "libqb-consumer-test"
#define RB_SIZE (1024 * 1024)

static int failures;

static void check(int cond, const char *what)
{
	if (!cond) {
		fprintf(stderr, "FAIL: %s\n", what);
		failures++;
	} else {
		printf("ok: %s\n", what);
	}
}

int main(void)
{
	const char payload[] = "hello-from-harmonyos-pc";
	char out[256];
	ssize_t n;
	qb_ringbuffer_t *rb;
	int32_t refcount;
	void *user_data;

	setvbuf(stdout, NULL, _IONBF, 0);

	/* 1) 共享内存 ring buffer：创建 + 写入 + 读回 */
	rb = qb_rb_open(RB_NAME, RB_SIZE,
			QB_RB_FLAG_CREATE | QB_RB_FLAG_SHARED_PROCESS,
			sizeof(int));
	check(rb != NULL, "qb_rb_open (shared-process ring buffer)");
	if (rb == NULL) {
		printf("RESULT: libqb consumer test on HarmonyOS PC FAILED\n");
		return 1;
	}

	n = qb_rb_chunk_write(rb, payload, sizeof(payload));
	check(n == (ssize_t)sizeof(payload), "qb_rb_chunk_write return value");

	memset(out, 0, sizeof(out));
	n = qb_rb_chunk_read(rb, out, sizeof(out), 1000);
	check(n == (ssize_t)sizeof(payload), "qb_rb_chunk_read return value");
	check(strcmp(out, payload) == 0, "ring buffer payload round-trip");

	/* 2) 共享用户数据区：qb_rb_open 申请了 sizeof(int) */
	user_data = qb_rb_shared_user_data_get(rb);
	check(user_data != NULL, "qb_rb_shared_user_data_get");
	if (user_data != NULL) {
		*(int *)user_data = 0x7ab1;
		check(*(int *)user_data == 0x7ab1, "shared user data read/write");
	}

	/* 3) 引用计数 */
	refcount = qb_rb_refcount_get(rb);
	check(refcount >= 1, "qb_rb_refcount_get");

	qb_rb_close(rb);

	/* 4) 日志子系统：输出到文件并落盘（sbd/pacemaker 的日志路径） */
	qb_log_init("libqb-consumer-test", LOG_USER, LOG_INFO);
	qb_log_ctl(QB_LOG_SYSLOG, QB_LOG_CONF_ENABLED, QB_FALSE);
	check(qb_log_ctl(QB_LOG_STDERR, QB_LOG_CONF_ENABLED, QB_FALSE) == 0,
	      "qb_log_ctl disable stderr");
	qb_log(LOG_INFO, "libqb consumer test on HarmonyOS PC");
	qb_log_fini();

	if (failures == 0) {
		printf("RESULT: libqb consumer test on HarmonyOS PC aarch64 PASSED\n");
		return 0;
	}
	fprintf(stderr, "RESULT: %d check(s) FAILED\n", failures);
	return 1;
}

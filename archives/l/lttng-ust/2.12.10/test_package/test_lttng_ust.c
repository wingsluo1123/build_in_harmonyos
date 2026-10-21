/*
 * lttng-ust 2.12.10 consumer probe (HarmonyOS / OHOS aarch64).
 *
 * 目的：以**消费者视角**验证本包在设备上真实可用——
 *   1) 公共头 <lttng/*.h> 可包含、版本宏与 2.12.10 一致；
 *   2) liblttng-ust 可链接、共享库可加载（构造函数跑通 ring buffer 初始化）；
 *   3) tracef()/tracelog() 宏在**无 session daemon** 时也不崩溃；
 *   4) 真实 TRACEPOINT_EVENT 走一遍 liblttng-ust-tracepoint 的
 *      dlopen + 探针注册路径（这是 lttng-ust 的常规用法）。
 *
 * 输出 TAP（1..N），全部通过才 rc=0。
 */
#include <stdio.h>
#include <stdlib.h>

#include <lttng/tracef.h>
#include <lttng/tracelog.h>
#include <lttng/ust-version.h>

#define TRACEPOINT_DEFINE
#include "probe_tp.h"

static int planned;
static int failed;

static void check(int cond, const char *msg)
{
	planned++;
	printf("%s - %s\n", cond ? "ok" : "not ok", msg);
	if (!cond) {
		failed++;
	}
}

int main(void)
{
	printf("TAP version 13\n");

	check(LTTNG_UST_MAJOR_VERSION == 2 && LTTNG_UST_MINOR_VERSION == 12,
	      "public header LTTNG_UST_{MAJOR,MINOR}_VERSION == 2.12");
	check(LTTNG_UST_PATCHLEVEL_VERSION == 10,
	      "public header LTTNG_UST_PATCHLEVEL_VERSION == 10");

	/* 无 session daemon：tracef/tracelog 的 tracepoint state==0，走空分支；
	 * 这里验证的是「宏可展开、符号可解析、调用不崩溃」。 */
	tracef("lttng-ust 2.12.10 OHOS consumer probe %d", 42);
	check(1, "tracef() linked and callable without session daemon");
	/* tracelog() 的 level 参数是**裸 enum 记号**（宏里做 ##level 拼接），
	 * 2.12.10 的合法取值是 TRACE_EMERG/ALERT/CRIT/ERR/WARNING/NOTICE/INFO/
	 * DEBUG_*，不是 LTTNG_UST_TRACELOG_LEVEL_*。 */
	tracelog(TRACE_INFO, "probe %d", 42);
	check(1, "tracelog() linked and callable without session daemon");

	/* 真实 tracepoint：构造函数 dlopen liblttng-ust-tracepoint.so */
	tracepoint(lttng_ust_probe, message, "hello from OHOS");
	check(1, "tracepoint(lttng_ust_probe, message) executed");

	printf("1..%d\n", planned);
	printf("# failed: %d\n", failed);
	return failed ? EXIT_FAILURE : EXIT_SUCCESS;
}

/*
 * relic 0.5.0 消费者测试（test_package）
 *
 * 以库使用者身份从**安装后的包**编译、链接并真实调用 relic 公开 API，
 * 用断言决定退出码 —— 不是只 include / 只链接 / 只打印。
 *
 * 断言内容（大整数恒等式，全部走 relic 的 bn_* 公开接口）：
 *   1. (a + b) - b == a            —— 加法/减法往返
 *   2. (a * a) / a == a            —— 平方 + 整除往返
 *   3. a * b != 0                  —— 乘法结果非零（a、b 均非零输入）
 * 任一断言不成立即非零退出。
 */
#include <stdio.h>

#include "relic/relic.h"

static int check(int ok, const char *what) {
	if (!ok) {
		fprintf(stderr, "relic consumer FAILED: %s\n", what);
		return 0;
	}
	printf("relic consumer ok: %s\n", what);
	return 1;
}

int main(void) {
	bn_t a, b, c, d;

	if (core_init() != RLC_OK) {
		fprintf(stderr, "relic consumer FAILED: core_init()\n");
		core_clean();
		return 1;
	}

	bn_null(a);
	bn_null(b);
	bn_null(c);
	bn_null(d);
	bn_new(a);
	bn_new(b);
	bn_new(c);
	bn_new(d);

	bn_read_str(a, "112233445566778899", 17, 16);
	bn_read_str(b, "0ff0ff0ff0ff0ff0f", 16, 16);

	/* 1) (a + b) - b == a */
	bn_add(c, a, b);
	bn_sub(c, c, b);
	if (!check(bn_cmp(c, a) == RLC_EQ, "(a + b) - b == a")) {
		goto fail;
	}

	/* 2) (a * a) / a == a */
	bn_sqr(c, a);
	bn_div(d, c, a);
	if (!check(bn_cmp(d, a) == RLC_EQ, "(a * a) / a == a")) {
		goto fail;
	}

	/* 3) a * b != 0 */
	bn_mul(c, a, b);
	if (!check(bn_is_zero(c) == 0, "a * b != 0")) {
		goto fail;
	}

	printf("relic consumer PASSED: 3 assertions\n");
	bn_free(a);
	bn_free(b);
	bn_free(c);
	bn_free(d);
	core_clean();
	return 0;

fail:
	bn_free(a);
	bn_free(b);
	bn_free(c);
	bn_free(d);
	core_clean();
	return 1;
}

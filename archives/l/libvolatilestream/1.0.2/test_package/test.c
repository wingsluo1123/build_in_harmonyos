/*
 * Consumer test for libvolatilestream 1.0.2 (HarmonyOS PC adaptation).
 *
 * 只使用公开 API：volstream_open() / volstream_trunc() / volstream_getbuf()
 * 以及普通 stdio 操作。13 个独立用例（12 个功能用例 + 1 个平台 fclose
 * 契约特征化用例）；每个用例输出一行 "TEST PASS <case>" 或
 * "TEST FAIL <case>"，程序末尾输出 "TEST SUMMARY: N passed, M failed"，
 * 任一用例失败则退出码为 1。
 *
 * 背景（E1807 / E302 同根因）：OHOS 运行时 musl 的 fclose 在 fflush 与
 * close 回调之前检查 `f->fd < 0`，而 fopencookie 按设计把 fd 置为 -1，
 * 因此所有无 fd 的内存流（fopencookie / fmemopen / open_memstream）的
 * fclose 都返回 EBADF 且 close 回调不执行。这是运行环境缺陷，不是
 * libvolatilestream 的缺陷；本测试用纯 libc 对照复现并只要求库流与
 * 对照行为一致（详见用例 platform_cookie_close_contract）。
 */

#define _GNU_SOURCE
#include <sys/types.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "volatilestream.h"

#define BIG_LEN (1024u * 1024u)

static unsigned char big_in[BIG_LEN];
static unsigned char big_out[BIG_LEN];

static int failed_cases;
static int passed_cases;
static int case_failures;
static const char *current_case;

static void begin_case(const char *name) {
	current_case = name;
	case_failures = 0;
	printf("[CASE] %s\n", name);
}

static void check(int condition, const char *what) {
	if (!condition) {
		case_failures++;
		printf("  CHECK FAILED: %s\n", what);
	}
}

static void end_case(void) {
	if (case_failures == 0) {
		passed_cases++;
		printf("TEST PASS %s\n", current_case);
	} else {
		failed_cases++;
		printf("TEST FAIL %s (%d checks failed)\n", current_case,
		       case_failures);
	}
}

/* ---------- 平台 cookie-stream fclose 契约（E1807 / E302 同根因）----------
 *
 * 纯 libc 对照：不使用 libvolatilestream，直接用 fopencookie(3) 建立一个
 * 最小 cookie 流，观察 fclose(3) 的行为与 close 回调是否执行。健康平台上
 * fclose 返回 0 且 close 回调执行一次；OHOS 运行时 musl 的 fclose 在
 * fflush()/close 回调之前有 `if (!f || f->fd < 0) return -EBADF` 保护，
 * 而 fopencookie 按设计把 fd 置为 -1，于是返回 EBADF、close 回调不执行。
 * 该对照在设备上复现后，后续用例只要求库流与对照行为一致。
 */
static int env_plain_rc = -1;
static int env_cookie_rc = -1;   /* -1 = cookie stream was never probed */
static int env_cookie_errno;
static int env_cookie_close_calls;
static int env_cookie_probed;
static int env_control_unavailable;
static int env_close_defect;

static ssize_t probe_cookie_write(void *cookie, const char *buf, size_t size) {
	(void)cookie;
	(void)buf;
	return (ssize_t)size;
}

static int probe_cookie_seek(void *cookie, off64_t *offset, int whence) {
	(void)cookie;
	(void)offset;
	(void)whence;
	return 0;
}

static int probe_cookie_close(void *cookie) {
	(void)cookie;
	env_cookie_close_calls++;
	return 0;
}

static void probe_platform_close_contract(void) {
	cookie_io_functions_t fns;
	FILE *plain;
	FILE *cookie;

	plain = fopen("/dev/null", "r");
	if (plain != NULL) {
		errno = 0;
		env_plain_rc = fclose(plain);
	}

	memset(&fns, 0, sizeof(fns));
	fns.write = probe_cookie_write;
	fns.seek = probe_cookie_seek;
	fns.close = probe_cookie_close;
	cookie = fopencookie(NULL, "r+", fns);
	if (cookie != NULL) {
		if (fputs("probe", cookie) >= 0) {
			errno = 0;
			env_cookie_rc = fclose(cookie);
			env_cookie_errno = errno;
			env_cookie_probed = 1;
		} else {
			/* 探测写失败：本流状态已被写错误污染，
			 * 不能作为对照组基线，关闭后丢弃。 */
			fclose(cookie);
		}
	}
	/* fopencookie 失败或探测写失败时对照组不可用：
	 * 此时不能把「未建立对照」当成「平台无缺陷」。 */
	env_control_unavailable = !env_cookie_probed;
	env_close_defect = (env_plain_rc == 0 && env_cookie_probed &&
			    env_cookie_rc != 0);
	printf("[ENV] control: plain fclose rc=%d; cookie fclose rc=%d errno=%d; "
	       "cookie close callback calls=%d; cookie control available=%s; "
	       "platform cookie-close defect=%s\n",
	       env_plain_rc, env_cookie_rc, env_cookie_errno,
	       env_cookie_close_calls,
	       env_control_unavailable ? "no" : "yes",
	       env_close_defect ? "yes" : "no");
}

/* fclose 是否符合当前平台的 cookie-stream 契约：
 * - 健康平台：返回 0；
 * - 已复现缺陷的平台：返回值与 errno 与纯 libc 对照完全一致。 */
static int close_matches_platform(FILE *f) {
	int rc;
	errno = 0;
	rc = fclose(f);
	if (env_close_defect)
		return rc == env_cookie_rc && errno == env_cookie_errno;
	return rc == 0;
}

static void check_close(FILE *f, const char *ok_message) {
	if (env_close_defect) {
		check(close_matches_platform(f),
		      "fclose matches the platform cookie-stream behavior");
	} else {
		check(fclose(f) == 0, ok_message);
	}
}

/* 1. 新建流：非空、长度为 0，关闭成功 */
static void case_open_empty_stream(void) {
	FILE *f;
	void *buf = (void *)0x1;
	size_t len = 999;

	begin_case("open_empty_stream");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf on a fresh stream succeeds");
		check(buf != (void *)0x1,
		      "volstream_getbuf writes the buffer out-parameter");
		check(len == 0, "fresh stream length is 0");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 2. 写入后 getbuf 立即可见，且可回绕读回 */
static void case_write_read_roundtrip(void) {
	const char *text = "volatile stream roundtrip";
	size_t n = strlen(text);
	char out[64];
	void *buf = NULL;
	size_t len = 0;
	FILE *f;

	begin_case("write_read_roundtrip");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fwrite(text, 1, n, f) == n, "fwrite writes all bytes");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf succeeds");
		check(len == n, "reported length matches the written bytes");
		check(buf != NULL && len >= n && memcmp(buf, text, n) == 0,
		      "direct buffer content matches");
		check(fseek(f, 0, SEEK_SET) == 0, "rewind to start");
		memset(out, 0, sizeof(out));
		check(fread(out, 1, n, f) == n, "fread returns all bytes");
		check(memcmp(out, text, n) == 0, "read-back content matches");
		check(fgetc(f) == EOF, "EOF after the last byte");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 3. 1 MiB 大缓冲增长：写入、直接校验、回绕读回 */
static void case_large_buffer_growth_1mib(void) {
	void *buf = NULL;
	size_t len = 0;
	size_t i;
	FILE *f;

	begin_case("large_buffer_growth_1mib");
	for (i = 0; i < BIG_LEN; i++)
		big_in[i] = (unsigned char)((i * 31u + 7u) & 0xFFu);
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fwrite(big_in, 1, BIG_LEN, f) == BIG_LEN,
		      "fwrite stores the full 1 MiB");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf succeeds");
		check(len == BIG_LEN, "reported length is 1 MiB");
		check(buf != NULL && len >= BIG_LEN &&
		      memcmp(buf, big_in, BIG_LEN) == 0,
		      "direct buffer matches the 1 MiB pattern");
		check(fseek(f, 0, SEEK_SET) == 0, "rewind to start");
		check(fread(big_out, 1, BIG_LEN, f) == BIG_LEN,
		      "fread returns the full 1 MiB");
		check(memcmp(big_out, big_in, BIG_LEN) == 0,
		      "read-back pattern matches");
		check(fgetc(f) == EOF, "EOF after the last byte");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 4. getbuf 允许 NULL 输出参数 */
static void case_getbuf_null_outputs(void) {
	void *buf = NULL;
	size_t len = 0;
	FILE *f;

	begin_case("getbuf_null_outputs");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fputs("abc", f) >= 0, "fputs writes 3 bytes");
		check(volstream_getbuf(f, NULL, NULL) == 0,
		      "volstream_getbuf accepts NULL out-pointers");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf with real out-pointers succeeds");
		check(volstream_getbuf(f, &buf, NULL) == 0,
		      "volstream_getbuf accepts a NULL length pointer");
		len = 0;   /* 哨兵：NULL buffer 分支仍须写出长度 */
		check(volstream_getbuf(f, NULL, &len) == 0,
		      "volstream_getbuf accepts a NULL buffer pointer");
		check(len == 3, "length is still 3");
		check(buf != NULL && len >= 3 && memcmp(buf, "abc", 3) == 0,
		      "content is still abc");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 5. trunc 缩小：长度变短、前缀保留、EOF 前移 */
static void case_trunc_shrink(void) {
	char out[16];
	void *buf = NULL;
	size_t len = 0;
	FILE *f;

	begin_case("trunc_shrink");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fwrite("0123456789", 1, 10, f) == 10,
		      "fwrite writes 10 bytes");
		check(volstream_trunc(f, 4) == 0,
		      "volstream_trunc shrink succeeds");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf succeeds");
		check(len == 4, "reported length is 4 after trunc");
		check(buf != NULL && len >= 4 && memcmp(buf, "0123", 4) == 0,
		      "kept prefix is 0123");
		check(fseek(f, 0, SEEK_SET) == 0, "rewind to start");
		memset(out, 0, sizeof(out));
		check(fread(out, 1, sizeof(out), f) == 4,
		      "fread returns 4 bytes then stops");
		check(memcmp(out, "0123", 4) == 0, "read-back prefix is 0123");
		check(fgetc(f) == EOF, "EOF after the truncated length");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 6. trunc 扩大：新增区间补零，原内容保留 */
static void case_trunc_extend_zero_fill(void) {
	unsigned char out[16];
	void *buf = NULL;
	size_t len = 0;
	size_t i;
	int zeros_ok = 1;
	FILE *f;

	begin_case("trunc_extend_zero_fill");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fwrite("ABCD", 1, 4, f) == 4, "fwrite writes 4 bytes");
		check(volstream_trunc(f, 16) == 0,
		      "volstream_trunc extend succeeds");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf succeeds");
		check(len == 16, "reported length is 16 after extend");
		check(buf != NULL && len >= 4 && memcmp(buf, "ABCD", 4) == 0,
		      "original prefix is preserved");
		if (buf != NULL && len >= 16) {
			const unsigned char *b = (const unsigned char *)buf;
			for (i = 4; i < 16; i++)
				if (b[i] != 0)
					zeros_ok = 0;
		} else {
			zeros_ok = 0;   /* short buffer: never read past len */
		}
		check(zeros_ok, "extended range is zero-filled");
		check(fseek(f, 0, SEEK_SET) == 0, "rewind to start");
		memset(out, 0xFF, sizeof(out));
		check(fread(out, 1, sizeof(out), f) == 16,
		      "fread returns all 16 bytes");
		check(memcmp(out, "ABCD", 4) == 0,
		      "read-back prefix is ABCD");
		check(out[15] == 0, "last extended byte reads back as zero");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 7. SEEK_END 越过末尾：空洞补零，之后写入的数据位置正确 */
static void case_seek_end_gap_zero_fill(void) {
	void *buf = NULL;
	size_t len = 0;
	size_t i;
	int zeros_ok = 1;
	FILE *f;

	begin_case("seek_end_gap_zero_fill");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fwrite("XY", 1, 2, f) == 2, "fwrite writes 2 bytes");
		check(fseek(f, 10, SEEK_END) == 0,
		      "seek 10 bytes past the end");
		check(fputc('Z', f) == 'Z', "write Z at the new position");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf succeeds");
		check(len == 13, "reported length is 13");
		if (buf != NULL && len >= 13) {
			const unsigned char *b = (const unsigned char *)buf;
			check(b[0] == 'X' && b[1] == 'Y',
			      "original prefix is XY");
			for (i = 2; i < 12; i++)
				if (b[i] != 0)
					zeros_ok = 0;
			check(zeros_ok, "gap between 2 and 12 is zero-filled");
			check(b[12] == 'Z', "byte 12 is Z");
		} else {
			check(0, "buffer is at least 13 bytes (gap case)");
		}
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 8. 多个流相互独立，关闭一个不影响另一个 */
static void case_multiple_independent_streams(void) {
	void *buf = NULL;
	size_t len = 0;
	FILE *a;
	FILE *b;

	begin_case("multiple_independent_streams");
	a = volstream_open();
	b = volstream_open();
	check(a != NULL && b != NULL, "two streams open");
	if (a != NULL && b != NULL) {
		check(fwrite("first", 1, 5, a) == 5, "write 5 bytes to stream A");
		check(fwrite("second!", 1, 7, b) == 7,
		      "write 7 bytes to stream B");
		check(volstream_getbuf(a, &buf, &len) == 0 && len == 5 &&
		      buf != NULL && memcmp(buf, "first", 5) == 0,
		      "stream A holds its own content");
		check(volstream_getbuf(b, &buf, &len) == 0 && len == 7 &&
		      buf != NULL && memcmp(buf, "second!", 7) == 0,
		      "stream B holds its own content");
		check_close(a, "close stream A");
		check(fputs(" more", b) >= 0, "stream B still writable");
		check(volstream_getbuf(b, &buf, &len) == 0 && len == 12 &&
		      buf != NULL && memcmp(buf, "second! more", 12) == 0,
		      "stream B content after A is closed");
		check_close(b, "close stream B");
	} else {
		if (a != NULL)
			fclose(a);
		if (b != NULL)
			fclose(b);
	}
	end_case();
}

/* 9. 普通 stdio 流不是 volstream：两个 API 都报 EBADF */
static void case_non_volstream_ebadf(void) {
	void *buf = NULL;
	size_t len = 0;
	FILE *plain;

	begin_case("non_volstream_ebadf");
	plain = fopen("/dev/null", "r");
	check(plain != NULL, "open /dev/null as a plain stdio stream");
	if (plain != NULL) {
		errno = 0;
		check(volstream_trunc(plain, 8) == -1,
		      "volstream_trunc on a plain stream fails");
		check(errno == EBADF, "volstream_trunc sets errno to EBADF");
		errno = 0;
		check(volstream_getbuf(plain, &buf, &len) == -1,
		      "volstream_getbuf on a plain stream fails");
		check(errno == EBADF, "volstream_getbuf sets errno to EBADF");
		check(fclose(plain) == 0, "fclose succeeds");
	}
	end_case();
}

/* 10. 负的 seek 位置被拒绝，流仍可用 */
static void case_seek_negative_rejected(void) {
	FILE *f;

	begin_case("seek_negative_rejected");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		errno = 0;
		check(fseek(f, -4, SEEK_SET) != 0,
		      "negative absolute seek is rejected");
		check(volstream_getbuf(f, NULL, NULL) == 0,
		      "stream is still usable after a failed seek");
		check_close(f, "fclose succeeds");
	}
	f = volstream_open();
	check(f != NULL, "open a second stream");
	if (f != NULL) {
		errno = 0;
		check(fseek(f, -1, SEEK_END) != 0,
		      "seek before the start is rejected");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 11. 与普通 stdio 混用：fprintf/fputs/fgets/fread 位置语义一致 */
static void case_stdio_mixed_formatting(void) {
	char line[32];
	char rest[8];
	void *buf = NULL;
	size_t len = 0;
	FILE *f;

	begin_case("stdio_mixed_formatting");
	f = volstream_open();
	check(f != NULL, "volstream_open returns a stream");
	if (f != NULL) {
		check(fprintf(f, "%d-%s\n", 42, "abc") == 7,
		      "fprintf writes 7 characters");
		check(fputs("tail", f) >= 0, "fputs appends 4 characters");
		check(volstream_getbuf(f, &buf, &len) == 0,
		      "volstream_getbuf succeeds");
		check(len == 11, "reported length is 11");
		check(buf != NULL && len >= 11 &&
		      memcmp(buf, "42-abc\ntail", 11) == 0,
		      "buffer holds the formatted text");
		check(fseek(f, 0, SEEK_SET) == 0, "rewind to start");
		memset(line, 0, sizeof(line));
		check(fgets(line, sizeof(line), f) != NULL,
		      "fgets reads the first line");
		check(strcmp(line, "42-abc\n") == 0,
		      "first line is 42-abc");
		memset(rest, 0, sizeof(rest));
		check(fread(rest, 1, 4, f) == 4, "fread reads the tail");
		check(memcmp(rest, "tail", 4) == 0, "tail content matches");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 12. 反复 open/write/getbuf/close，64 轮流程均成功（资源回收受平台 fclose 缺陷限制，见用例 13） */
static void case_repeated_open_close_64(void) {
	int cycles_ok = 1;
	int i;
	FILE *f;

	begin_case("repeated_open_close_64");
	for (i = 0; i < 64; i++) {
		void *buf = NULL;
		size_t len = 0;
		f = volstream_open();
		if (f == NULL) {
			cycles_ok = 0;
			break;
		}
		if (fputs("cycle", f) < 0 ||
		    volstream_getbuf(f, &buf, &len) != 0 || len != 5 ||
		    buf == NULL || memcmp(buf, "cycle", 5) != 0) {
			cycles_ok = 0;
			fclose(f);
			break;
		}
		if (!close_matches_platform(f)) {
			cycles_ok = 0;
			break;
		}
	}
	check(cycles_ok, "64 open/write/getbuf/close cycles succeed");
	f = volstream_open();
	check(f != NULL, "a new stream still works after 64 cycles");
	if (f != NULL) {
		check(volstream_getbuf(f, NULL, NULL) == 0,
		      "new stream reports its empty state");
		check_close(f, "fclose succeeds");
	}
	end_case();
}

/* 13. 平台 fclose 契约特征化：纯 libc 对照 + 库流同行为校验（E1807/E302） */
static void case_platform_cookie_close_contract(void) {
	void *buf = NULL;
	size_t len = 0;
	int rc;
	int saved_errno;
	FILE *f;

	begin_case("platform_cookie_close_contract");
	check(!env_control_unavailable,
	      "pure-libc control streams are available (contract characterized)");
	check(env_plain_rc == 0, "plain stdio stream fclose succeeds (control)");
	if (env_close_defect) {
		check(env_cookie_rc != 0 && env_cookie_errno == EBADF,
		      "pure-libc cookie stream fclose returns EBADF (control)");
		check(env_cookie_close_calls == 0,
		      "pure-libc cookie close callback is not invoked (control)");
		f = volstream_open();
		check(f != NULL, "volstream_open returns a stream");
		if (f != NULL) {
			check(fputs("close-contract", f) >= 0,
			      "library stream accepts writes before close");
			check(volstream_getbuf(f, &buf, &len) == 0 && len == 14,
			      "library buffer is complete before close");
			errno = 0;
			rc = fclose(f);
			saved_errno = errno;
			check(rc == env_cookie_rc && saved_errno == env_cookie_errno,
			      "library fclose matches the pure-libc control "
			      "(environment defect, not a library failure)");
			printf("[ENV] library stream fclose rc=%d errno=%d; "
			       "stream resources are reclaimed at process exit\n",
			       rc, saved_errno);
		}
	} else {
		check(env_cookie_rc == 0,
		      "pure-libc cookie stream fclose succeeds (control)");
		check(env_cookie_close_calls == 1,
		      "pure-libc cookie close callback runs exactly once (control)");
		f = volstream_open();
		check(f != NULL, "volstream_open returns a stream");
		if (f != NULL) {
			check(fputs("close-contract", f) >= 0,
			      "library stream accepts writes before close");
			check(volstream_getbuf(f, &buf, &len) == 0 && len == 14,
			      "library buffer is complete before close");
			check(fclose(f) == 0,
			      "library fclose succeeds on a platform "
			      "without the defect");
		}
	}
	end_case();
}

int main(void) {
	printf("libvolatilestream consumer test (%s)\n",
	       "volstream_open/trunc/getbuf");
	probe_platform_close_contract();
	case_open_empty_stream();
	case_write_read_roundtrip();
	case_large_buffer_growth_1mib();
	case_getbuf_null_outputs();
	case_trunc_shrink();
	case_trunc_extend_zero_fill();
	case_seek_end_gap_zero_fill();
	case_multiple_independent_streams();
	case_non_volstream_ebadf();
	case_seek_negative_rejected();
	case_stdio_mixed_formatting();
	case_repeated_open_close_64();
	case_platform_cookie_close_contract();
	printf("TEST SUMMARY: %d passed, %d failed\n", passed_cases,
	       failed_cases);
	if (env_close_defect)
		printf("[ENV] cookie-stream fclose EBADF is a platform libc "
		       "deviation (E1807/E302 family), reproduced by the "
		       "pure-libc control; it is not a libvolatilestream "
		       "failure\n");
	if (failed_cases == 0) {
		printf("RESULT: PASS\n");
		return 0;
	}
	printf("RESULT: FAIL\n");
	return 1;
}

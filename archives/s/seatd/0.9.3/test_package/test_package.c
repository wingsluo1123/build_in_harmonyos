/*
 * Conan test_package for seatd 0.9.3 — consumer-side L1 test of libseat.
 *
 * Why this test is not a smoke test:
 *
 * libseat always compiles in a "noop" backend (libseat/backend/noop.c) in
 * addition to the optional seatd / logind / builtin ones.  Selecting it with
 * LIBSEAT_BACKEND=noop drives the *whole* public API — open, seat_name,
 * get_fd, dispatch (including the enable_seat callback), open_device,
 * close_device, close_seat — with no seatd daemon, no logind and no session,
 * which is exactly the situation in a CI container.
 *
 * Every assertion below therefore runs unconditionally and a failure exits
 * non-zero.  Nothing is reported as "OK" because the environment happens to
 * lack a seat.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "libseat.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                                      \
	do {                                                                  \
		checks++;                                                     \
		if (cond) {                                                   \
			printf("  ok %2d: %s\n", checks, (msg));              \
		} else {                                                      \
			failures++;                                           \
			printf("  FAIL %2d: %s (errno=%d: %s)\n", checks,     \
			       (msg), errno, strerror(errno));                \
		}                                                             \
	} while (0)

static int enable_calls = 0;
static int disable_calls = 0;
static int log_calls = 0;

static void enable_seat(struct libseat *seat, void *userdata)
{
	(void)seat;
	(void)userdata;
	enable_calls++;
}

static void disable_seat(struct libseat *seat, void *userdata)
{
	(void)userdata;
	disable_calls++;
	libseat_disable_seat(seat);
}

static void count_log(enum libseat_log_level level, const char *fmt,
		      va_list args)
{
	(void)level;
	(void)fmt;
	(void)args;
	log_calls++;
}

static const struct libseat_seat_listener listener = {
	.enable_seat = enable_seat,
	.disable_seat = disable_seat,
};

/* Create a small regular file the noop backend can really open(2). */
static const char *make_device_file(void)
{
	static const char *path = "libseat_test_device.tmp";
	FILE *f = fopen(path, "w");

	if (f == NULL)
		return NULL;
	fputs("libseat test device\n", f);
	fclose(f);
	return path;
}

int main(void)
{
	struct libseat *seat;
	const char *name;
	const char *devpath;
	int fd = -1;
	int devid;
	int rc;

	printf("== libseat consumer test ==\n");

	libseat_set_log_handler(count_log);
	libseat_set_log_level(LIBSEAT_LOG_LEVEL_ERROR);

	/* --- documented error contracts ------------------------------- */

	errno = 0;
	seat = libseat_open_seat(NULL, NULL);
	CHECK(seat == NULL && errno == EINVAL,
	      "libseat_open_seat(NULL) fails with EINVAL");

	const struct libseat_seat_listener broken = {
		.enable_seat = NULL,
		.disable_seat = disable_seat,
	};
	errno = 0;
	seat = libseat_open_seat(&broken, NULL);
	CHECK(seat == NULL && errno == EINVAL,
	      "libseat_open_seat() rejects a listener without enable_seat");

	log_calls = 0;
	setenv("LIBSEAT_BACKEND", "seatd-conan-no-such-backend", 1);
	errno = 0;
	seat = libseat_open_seat(&listener, NULL);
	CHECK(seat == NULL && errno == EINVAL,
	      "unknown LIBSEAT_BACKEND fails with EINVAL");
	CHECK(log_calls > 0,
	      "the error was reported through the installed log handler");

	/* --- full API round trip on the always-present noop backend ---- */

	setenv("LIBSEAT_BACKEND", "noop", 1);
	enable_calls = 0;
	errno = 0;
	seat = libseat_open_seat(&listener, NULL);
	CHECK(seat != NULL, "LIBSEAT_BACKEND=noop opens a seat");
	if (seat == NULL) {
		printf("== %d/%d checks passed, %d failed ==\n",
		       checks - failures, checks, failures);
		return 1;
	}

	name = libseat_seat_name(seat);
	CHECK(name != NULL && strcmp(name, "seat0") == 0,
	      "libseat_seat_name() reports \"seat0\"");

	fd = libseat_get_fd(seat);
	CHECK(fd >= 0, "libseat_get_fd() returns a pollable fd");

	rc = libseat_dispatch(seat, 0);
	CHECK(rc >= 0, "libseat_dispatch(seat, 0) succeeds");
	CHECK(enable_calls == 1,
	      "the enable_seat callback fired exactly once on first dispatch");

	rc = libseat_dispatch(seat, 0);
	CHECK(rc >= 0 && enable_calls == 1,
	      "a second dispatch does not re-fire enable_seat");

	devpath = make_device_file();
	CHECK(devpath != NULL, "test device file created");
	if (devpath != NULL) {
		errno = 0;
		devid = libseat_open_device(seat, devpath, &fd);
		CHECK(devid >= 0 && fd >= 0,
		      "libseat_open_device() returns a device id and fd");
		if (devid >= 0) {
			rc = libseat_close_device(seat, devid);
			CHECK(rc == 0, "libseat_close_device() succeeds");
		}
		errno = 0;
		fd = -1;
		devid = libseat_open_device(
			seat, "seatd-conan-no-such-device", &fd);
		CHECK(devid == -1,
		      "libseat_open_device() fails on a missing path");
		remove(devpath);
	}

	rc = libseat_close_seat(seat);
	CHECK(rc == 0, "libseat_close_seat() succeeds");

	unsetenv("LIBSEAT_BACKEND");

	printf("== %d/%d checks passed, %d failed ==\n",
	       checks - failures, checks, failures);
	return failures == 0 ? 0 : 1;
}

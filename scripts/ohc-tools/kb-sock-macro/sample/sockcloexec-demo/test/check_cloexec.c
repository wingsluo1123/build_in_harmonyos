/*
 * 鸿蒙独有消费者断言：SOCK_CLOEXEC / SOCK_NONBLOCK 位是否真的落在 fd 上。
 *
 * 断言的是行为而不是宏值：
 *   FD_CLOEXEC  -> fcntl(fd, F_GETFD)
 *   O_NONBLOCK  -> fcntl(fd, F_GETFL)
 * 兼容层把宏覆盖成 0 时，socket() 照样成功，只有这里能把缺陷暴露出来。
 */
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>

#include "demo_sock.h"

static int testno;
static int failed;

static void check(const char *name, int cond)
{
	testno++;
	if (cond) {
		printf("ok %d - %s\n", testno, name);
	} else {
		printf("not ok %d - %s\n", testno, name);
		failed++;
	}
}

int main(void)
{
	int fd;
	int fdflags;
	int flflags;

	fd = demo_open_cloexec_socket();
	check("demo_open_cloexec_socket() succeeded", fd >= 0);
	if (fd < 0) {
		printf("1..%d\n", testno);
		return 1;
	}

	fdflags = fcntl(fd, F_GETFD);
	flflags = fcntl(fd, F_GETFL);
	check("FD_CLOEXEC set by SOCK_CLOEXEC", (fdflags & FD_CLOEXEC) != 0);
	check("O_NONBLOCK set by SOCK_NONBLOCK", (flflags & O_NONBLOCK) != 0);

	if (close(fd) != 0)
		check("close() succeeded", 0);

	/* 宏值对照：修复后应与系统头一致（02000000 / 04000） */
	printf("# SOCK_CLOEXEC=%d SOCK_NONBLOCK=%d\n", SOCK_CLOEXEC, SOCK_NONBLOCK);
	printf("1..%d\n", testno);
	return failed ? 1 : 0;
}

#include <sys/socket.h>

#include "demo_sock.h"
#include "bsd-compat/bsd-compat.h"

/*
 * 真实使用点：socket() 的 type 参数携带 SOCK_CLOEXEC / SOCK_NONBLOCK。
 * 兼容层把两个宏兜底成 0 后，这两个位在系统调用里静默消失。
 */
int demo_open_cloexec_socket(void)
{
	int fd;

	fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
	return fd;
}

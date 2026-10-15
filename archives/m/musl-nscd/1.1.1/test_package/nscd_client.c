/*
 * nscd_client.c — musl-nscd 端到端测试的 NSCD 协议客户端。
 *
 * 直接按 NSCD 二进制协议与被测守护进程通信（线协议取自上游 include/nscd.h、
 * src/socket_handle.c、src/write_val.c）：
 *
 *   请求: uint32[3] {NSCDVERSION(=2), reqtype, keylen} + keylen 字节 key
 *         - NAME 类请求（GETPWBYNAME/GETGRBYNAME）：key 为 NUL 结尾的字符串
 *         - UID/GID 类请求（GETPWBYUID/GETGRBYGID）：key 为 NUL 结尾的十进制串
 *   应答: passwd 请求 → uint32[PW_LEN] 头部 + name/passwd/gecos/dir/shell
 *         group  请求 → uint32[GR_LEN] 头部 + 每个成员的长度 + name/passwd + 各成员
 *
 * 同主机通信，字节序一致，无需 swap。一条连接只服务一个请求（上游处理完即
 * close），因此读侧以「读满所需字节」为准。
 *
 * 输出为逐行 key=value，供 test.sh 断言；退出码 0 = 协议往返成功（无论命中与否）。
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define NSCDVERSION 2

#define GETPWBYNAME 0
#define GETPWBYUID  1
#define GETGRBYNAME 2
#define GETGRBYGID  3

#define REQ_LEN 3
#define PW_LEN  9
#define GR_LEN  6

#define PWFOUND     1
#define PWNAMELEN   2
#define PWPASSWDLEN 3
#define PWUID       4
#define PWGID       5
#define PWGECOSLEN  6
#define PWDIRLEN    7
#define PWSHELLLEN  8

#define GRFOUND     1
#define GRNAMELEN   2
#define GRPASSWDLEN 3
#define GRGID       4
#define GRMEMCNT    5

static int read_full(int fd, void *dst, size_t n)
{
	size_t done = 0;

	while (done < n) {
		ssize_t r = read(fd, (char *)dst + done, n - done);

		if (r < 0) {
			if (errno == EINTR) {
				continue;
			}
			return -1;
		}
		if (r == 0) {
			return -1;	/* 对端提前关闭 */
		}
		done += (size_t)r;
	}
	return 0;
}

static int write_full(int fd, const void *src, size_t n)
{
	size_t done = 0;

	while (done < n) {
		ssize_t r = write(fd, (const char *)src + done, n - done);

		if (r < 0) {
			if (errno == EINTR) {
				continue;
			}
			return -1;
		}
		done += (size_t)r;
	}
	return 0;
}

/* 读长度为 len 的 NUL 结尾字段并以 key=value 打印 */
static int print_field(const char *key, int fd, uint32_t len)
{
	char *buf;

	if (len == 0) {
		printf("%s=\n", key);
		return 0;
	}
	buf = malloc(len);
	if (!buf) {
		return -1;
	}
	if (read_full(fd, buf, len) < 0) {
		free(buf);
		return -1;
	}
	if (buf[len - 1] != '\0') {
		free(buf);
		return -1;
	}
	printf("%s=%s\n", key, buf);
	free(buf);
	return 0;
}

static int handle_passwd(int fd)
{
	uint32_t head[PW_LEN];
	uint32_t i;

	if (read_full(fd, head, sizeof(head)) < 0) {
		return -1;
	}
	if (head[0] != NSCDVERSION) {
		fprintf(stderr, "应答版本错误: %u（期望 %u）\n", head[0], NSCDVERSION);
		return -1;
	}
	if (!head[PWFOUND]) {
		printf("NOTFOUND\n");
		return 0;
	}
	printf("FOUND\n");
	printf("uid=%u\n", head[PWUID]);
	printf("gid=%u\n", head[PWGID]);
	if (print_field("name", fd, head[PWNAMELEN]) < 0 ||
	    print_field("passwd", fd, head[PWPASSWDLEN]) < 0 ||
	    print_field("gecos", fd, head[PWGECOSLEN]) < 0 ||
	    print_field("dir", fd, head[PWDIRLEN]) < 0 ||
	    print_field("shell", fd, head[PWSHELLLEN]) < 0) {
		return -1;
	}
	(void)i;
	return 0;
}

static int handle_group(int fd)
{
	uint32_t head[GR_LEN];
	uint32_t *mlens = NULL;
	uint32_t i;
	int rc = -1;

	if (read_full(fd, head, sizeof(head)) < 0) {
		return -1;
	}
	if (head[0] != NSCDVERSION) {
		fprintf(stderr, "应答版本错误: %u（期望 %u）\n", head[0], NSCDVERSION);
		return -1;
	}
	if (!head[GRFOUND]) {
		printf("NOTFOUND\n");
		return 0;
	}
	printf("FOUND\n");
	printf("gid=%u\n", head[GRGID]);
	printf("nmembers=%u\n", head[GRMEMCNT]);

	if (head[GRMEMCNT] > 0) {
		mlens = malloc(sizeof(uint32_t) * head[GRMEMCNT]);
		if (!mlens) {
			return -1;
		}
		if (read_full(fd, mlens, sizeof(uint32_t) * head[GRMEMCNT]) < 0) {
			goto out;
		}
	}
	if (print_field("name", fd, head[GRNAMELEN]) < 0 ||
	    print_field("passwd", fd, head[GRPASSWDLEN]) < 0) {
		goto out;
	}
	for (i = 0; i < head[GRMEMCNT]; i++) {
		if (print_field("member", fd, mlens[i]) < 0) {
			goto out;
		}
	}
	rc = 0;
out:
	free(mlens);
	return rc;
}

int main(int argc, char **argv)
{
	struct sockaddr_un addr;
	uint32_t req[REQ_LEN];
	const char *kind;
	uint32_t reqtype;
	int is_passwd, fd, rc;
	size_t keylen;

	if (argc != 4) {
		fprintf(stderr, "用法: %s <socket 路径> <pw-name|pw-uid|gr-name|gr-gid> <key>\n",
			argv[0]);
		return 2;
	}

	kind = argv[2];
	if (strcmp(kind, "pw-name") == 0) {
		reqtype = GETPWBYNAME;
		is_passwd = 1;
	} else if (strcmp(kind, "pw-uid") == 0) {
		reqtype = GETPWBYUID;
		is_passwd = 1;
	} else if (strcmp(kind, "gr-name") == 0) {
		reqtype = GETGRBYNAME;
		is_passwd = 0;
	} else if (strcmp(kind, "gr-gid") == 0) {
		reqtype = GETGRBYGID;
		is_passwd = 0;
	} else {
		fprintf(stderr, "未知请求类型: %s\n", kind);
		return 2;
	}

	/* UID/GID 类请求由上游 strtouid() 以十进制字符串解析，keylen 上限 11 */
	keylen = strlen(argv[3]) + 1;
	if (keylen > 108 || (uint32_t)keylen == 0) {
		fprintf(stderr, "key 长度非法: %zu\n", keylen);
		return 2;
	}

	memset(&addr, 0, sizeof(addr));
	addr.sun_family = AF_UNIX;
	if (strlen(argv[1]) >= sizeof(addr.sun_path)) {
		fprintf(stderr, "socket 路径过长: %s\n", argv[1]);
		return 2;
	}
	strncpy(addr.sun_path, argv[1], sizeof(addr.sun_path) - 1);

	fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (fd < 0) {
		perror("socket");
		return 1;
	}
	if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
		perror("connect");
		close(fd);
		return 1;
	}

	req[0] = NSCDVERSION;
	req[1] = reqtype;
	req[2] = (uint32_t)keylen;

	if (write_full(fd, req, sizeof(req)) < 0 ||
	    write_full(fd, argv[3], keylen) < 0) {
		perror("write");
		close(fd);
		return 1;
	}

	rc = is_passwd ? handle_passwd(fd) : handle_group(fd);

	close(fd);
	if (rc < 0) {
		fprintf(stderr, "协议往返失败\n");
		return 1;
	}
	return 0;
}

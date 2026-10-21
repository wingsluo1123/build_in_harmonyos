#ifndef DEMO_SOCK_H
#define DEMO_SOCK_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * 以 SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK 创建 AF_UNIX socket。
 * 成功返回 fd（带 FD_CLOEXEC 与 O_NONBLOCK 语义），失败返回 -1。
 */
int demo_open_cloexec_socket(void);

#ifdef __cplusplus
}
#endif

#endif /* DEMO_SOCK_H */

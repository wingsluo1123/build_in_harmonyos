// fixture: 对照组——只引入 libc 头，不引入 UAPI，应零命中
#include <sys/socket.h>
#include <netinet/in.h>
#include <string.h>

int fixture_clean(void);

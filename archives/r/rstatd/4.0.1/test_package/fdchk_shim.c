#include <stdlib.h>
#include <stdio.h>
#include <sys/select.h>

void __fd_chk(int fd)
{
    if (fd < 0 || fd >= FD_SETSIZE) {
        fprintf(stderr, "__fd_chk: invalid fd %d\n", fd);
        abort();
    }
}
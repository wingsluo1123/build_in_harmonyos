#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>

int main(void)
{
    const char* marker = getenv("CVM_PIPE_MARKER");
    int fd;
    if (marker == 0) return 2;
    fd = open(marker, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd == -1) return 3;
    close(fd);
    return 0;
}

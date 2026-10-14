#include <cvm/errors.h>
#include <cvm/v2client.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <unistd.h>

int main(int argc, char** argv)
{
    struct rlimit limit;
    struct cvm_packet request = {0};
    struct cvm_packet response = {0};
    unsigned result;

    if (argc != 3) {
        fprintf(stderr, "usage: %s HELPER MARKER\n", argv[0]);
        return 2;
    }
    unlink(argv[2]);
    if (setenv("CVM_PIPE_MARKER", argv[2], 1) == -1) return 3;
    if (getrlimit(RLIMIT_NOFILE, &limit) == -1) return 4;
    limit.rlim_cur = 5;
    if (setrlimit(RLIMIT_NOFILE, &limit) == -1) return 5;

    request.length = 1;
    request.data[0] = 0;
    errno = 0;
    result = cvm_xfer_command_packets(argv[1], &request, &response);
    if (result != CVME_IO) {
        fprintf(stderr, "expected CVME_IO, got %u\n", result);
        return 6;
    }
    if (access(argv[2], F_OK) == 0) {
        fputs("module executed after the second pipe allocation failed\n", stderr);
        return 7;
    }
    puts("command transport pipe acquisition is failure-atomic");
    return 0;
}

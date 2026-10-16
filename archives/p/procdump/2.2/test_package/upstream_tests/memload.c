/*
 * memload — OHOS 执行层的 stress-ng 内存负载等价物（procdump 2.2 上游测试
 * 真实执行层）。上游 runProcDumpAndValidate.sh 的 MEM 分支用
 * `stress-ng --vm 1 --vm-hang 0 --vm-bytes <N>M --timeout 20s` 制造一个
 * RSS≈N MB 的被监视进程；OHOS 基础镜像不含 stress-ng，本程序以
 * malloc(N MB)+memset(全部页) 精确达到相同 RSS，并休眠直到被 procdump
 * 场景结束时的 kill 清理。参数：<MB>，如 `memload 90`。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
    int mb = (argc > 1) ? atoi(argv[1]) : 80;
    if (mb <= 0) {
        mb = 1;
    }
    size_t bytes = (size_t)mb * 1024 * 1024;
    unsigned char *p = malloc(bytes);
    if (p == NULL) {
        fprintf(stderr, "memload: malloc(%zu bytes) failed\n", bytes);
        return 1;
    }
    /* touch every page so RSS equals the requested size */
    memset(p, 0x41, bytes);
    sleep(100000); /* kept alive; killed by the scenario harness */
    return 0;
}

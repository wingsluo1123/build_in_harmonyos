#include <stdio.h>
#include "bzlib.h"

int main(void) {
    printf("bzip2 version: %s\n", BZ2_bzlibVersion());
    char out[1024]; unsigned int outlen = sizeof(out);
    int ret = BZ2_bzBuffToBuffCompress(out, &outlen, "hello world", 11, 5, 0, 0);
    printf("compress: ret=%d, outlen=%u\n", ret, outlen);
    return 0;
}

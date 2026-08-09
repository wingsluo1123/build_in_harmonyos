#include <stdio.h>
#include <md5.h>

int main(void) {
    MD5_CTX ctx;
    MD5Init(&ctx);
    unsigned char data[] = "hello";
    MD5Update(&ctx, data, 5);
    unsigned char digest[16];
    MD5Final(digest, &ctx);
    printf("MD5 digest computed successfully\n");
    return 0;
}

#include <stdio.h>
#include "bcrypt.h"

int main(void) {
    char salt[BCRYPT_HASHSIZE];
    char hash[BCRYPT_HASHSIZE];
    int ret = bcrypt_gensalt(12, salt);
    if (ret == 0) {
        ret = bcrypt_hashpw("test123", salt, hash);
        printf("bcrypt: hash=%s\n", hash);
    }
    return 0;
}

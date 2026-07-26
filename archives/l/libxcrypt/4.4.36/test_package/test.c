#include <crypt.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *password = "conan-libxcrypt-password";
    const char *salt = "$6$conan-salt$";
    char first_hash[256];
    char wrong_hash[256];
    char *hash;
    char *verified;

    hash = crypt(password, salt);
    if (hash == NULL) {
        fprintf(stderr, "crypt() returned NULL for a valid SHA-512 salt\n");
        return 1;
    }
    if (strncmp(hash, salt, strlen(salt)) != 0) {
        fprintf(stderr, "crypt() returned an unexpected hash format: %s\n", hash);
        return 2;
    }
    if (strlen(hash) >= sizeof(first_hash)) {
        fprintf(stderr, "crypt() hash is too long\n");
        return 3;
    }
    strcpy(first_hash, hash);

    verified = crypt(password, first_hash);
    if (verified == NULL || strcmp(verified, first_hash) != 0) {
        fprintf(stderr, "crypt() verification round trip failed\n");
        return 4;
    }

    hash = crypt("wrong-password", first_hash);
    if (hash == NULL || strlen(hash) >= sizeof(wrong_hash)) {
        fprintf(stderr, "crypt() failed for the negative case\n");
        return 5;
    }
    strcpy(wrong_hash, hash);
    if (strcmp(wrong_hash, first_hash) == 0) {
        fprintf(stderr, "crypt() accepted the wrong password\n");
        return 6;
    }

    puts("libxcrypt crypt() API test passed");
    return 0;
}

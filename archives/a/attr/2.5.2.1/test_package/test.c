#include <attr/attributes.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    static const char name[] = "user.attr_conan_probe";
    static const char expected[] = "libattr-probe";
    char value[sizeof(expected)] = {0};
    int value_length = (int)sizeof(value);
    int failed = 0;

    if (argc != 2) {
        fprintf(stderr, "LIBATTR usage FAIL errno=0 expected=one-file-path\n");
        return 2;
    }

    if (attr_set(argv[1], name, expected, (int)sizeof(expected), 0) == -1) {
        int saved_errno = errno;
        fprintf(stderr, "LIBATTR attr_set FAIL errno=%d message=%s\n",
                saved_errno, strerror(saved_errno));
        fprintf(stderr, "LIBATTR attr_get NOTRUN cause=attr_set errno=%d\n", saved_errno);
        failed = 1;
    } else {
        puts("LIBATTR attr_set PASS");
        if (attr_get(argv[1], name, value, &value_length, 0) == -1) {
            int saved_errno = errno;
            fprintf(stderr, "LIBATTR attr_get FAIL errno=%d message=%s\n",
                    saved_errno, strerror(saved_errno));
            failed = 1;
        } else if (value_length != (int)sizeof(expected) ||
                   memcmp(value, expected, sizeof(expected)) != 0) {
            fprintf(stderr, "LIBATTR attr_get FAIL errno=0 cause=value-mismatch length=%d\n",
                    value_length);
            failed = 1;
        } else {
            puts("LIBATTR attr_get PASS value=libattr-probe");
        }
    }

    return failed;
}

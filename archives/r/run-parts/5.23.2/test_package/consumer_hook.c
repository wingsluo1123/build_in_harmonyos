/* Consumer program for the run-parts test_package.
 *
 * It is compiled with the OHOS toolchain during `conan create` and installed
 * as an executable "hook" in a directory that the packaged run-parts binary
 * then executes.  The hook reports what run-parts handed to it (arguments,
 * stdin multiplexed through a temporary file, umask, exit status). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char *name = strrchr(argv[0], '/');
    name = name ? name + 1 : argv[0];

    printf("HOOK %s argc=%d", name, argc);
    for (int i = 1; i < argc; i++)
        printf(" [%s]", argv[i]);
    printf("\n");

    if (argc > 1 && strcmp(argv[1], "stdin") == 0) {
        char buf[256];
        size_t n = fread(buf, 1, sizeof buf - 1, stdin);
        buf[n] = '\0';
        printf("STDIN %zu %s", n, buf);
    } else if (argc > 1 && strcmp(argv[1], "umask") == 0) {
        mode_t m = umask(0);
        printf("UMASK %03o\n", (unsigned)m);
    } else if (argc > 1 && strcmp(argv[1], "fail") == 0) {
        return 3;
    }
    return 0;
}

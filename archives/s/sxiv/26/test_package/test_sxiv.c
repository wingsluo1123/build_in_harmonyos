/*
 * Installed-package smoke test for sxiv.  It validates the installed ELF
 * executable and its version path without requiring an X display.
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    struct stat st;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <sxiv-binary>\n", argv[0]);
        return 1;
    }
    if (stat(argv[1], &st) != 0 || !S_ISREG(st.st_mode) ||
        access(argv[1], X_OK) != 0) {
        fprintf(stderr, "sxiv binary is not an executable regular file: %s\n",
                argv[1]);
        return 1;
    }
    puts("sxiv installed executable check passed");
    return 0;
}

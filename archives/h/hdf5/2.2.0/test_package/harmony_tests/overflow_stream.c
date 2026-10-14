/* Calls the installed production tools library, not a copied fallback. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

/* Exact external declarations in upstream tools/lib/h5tools*.{h,c}. */
extern void h5tools_init(void);
extern void h5tools_close(void);
extern void parallel_print(const char *, ...);
extern unsigned char g_Parallel;
extern unsigned outBuffOffset;
extern FILE *overflow_file;

#define CHECK(e) do { if (!(e)) { fprintf(stderr, "Harmony overflow failure:%d:%s\n", __LINE__, #e); return 1; } } while (0)

int main(void)
{
#ifndef __OHOS__
    fputs("The OHOS production overflow backend must actually be selected\n", stderr);
    return 1;
#else
    struct utsname platform;
    struct stat before, opened, after;
    const char *tmp = getenv("TMPDIR");
    char expected[4097], actual[4097];
    CHECK(uname(&platform) == 0 && strcmp(platform.sysname, "HarmonyOS") == 0);
    CHECK(tmp && tmp[0] == '/');
    CHECK(lstat(tmp, &before) == 0 && S_ISDIR(before.st_mode));
    CHECK(before.st_uid == getuid());
    for (size_t n = 0; n < sizeof(expected) - 1; ++n)
        expected[n] = (char)('A' + n % 26);
    expected[sizeof(expected) - 1] = 0;
    h5tools_init();
    CHECK(overflow_file == NULL);
    g_Parallel = 1;
    outBuffOffset = 0;
    /* Original producer buffer is 4096 bytes; exact capacity triggers overflow. */
    parallel_print("%s", expected);
    CHECK(overflow_file != NULL);
    CHECK(fstat(fileno(overflow_file), &opened) == 0);
    CHECK(S_ISREG(opened.st_mode) && opened.st_uid == getuid());
    CHECK(opened.st_nlink == 0); /* actual immediate-unlink platform backend */
    CHECK(fflush(overflow_file) == 0 && fseek(overflow_file, 0, SEEK_SET) == 0);
    CHECK(fread(actual, 1, sizeof(expected) - 1, overflow_file) == sizeof(expected) - 1);
    CHECK(memcmp(actual, expected, sizeof(expected) - 1) == 0);
    CHECK(fgetc(overflow_file) == EOF && !ferror(overflow_file));
    CHECK(fclose(overflow_file) == 0);
    overflow_file = NULL;
    g_Parallel = 0;
    h5tools_close();
    CHECK(lstat(tmp, &after) == 0 && before.st_dev == after.st_dev && before.st_ino == after.st_ino);
    puts("HARMONY_TEST_COUNT=1\nHARMONY_PRIVATE_PRODUCTION_OVERFLOW_PASS=1/1");
    return 0;
#endif
}

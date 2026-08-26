#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <whereami.h>

static int check_path(int (*get_path)(char *, int, int *), const char *label)
{
    int dirname_length = -1;
    int length = get_path(NULL, 0, NULL);
    char *path;

    if (length <= 0) {
        fprintf(stderr, "%s length query failed: %d\n", label, length);
        return 1;
    }

    path = (char *)malloc((size_t)length + 1);
    if (path == NULL) {
        return 1;
    }

    if (get_path(path, length, &dirname_length) != length) {
        fprintf(stderr, "%s path query failed\n", label);
        free(path);
        return 1;
    }
    path[length] = '\0';

    if (path[0] != '/' || dirname_length <= 0 || dirname_length >= length ||
        path[dirname_length] != '/') {
        fprintf(stderr, "%s returned invalid path: %s\n", label, path);
        free(path);
        return 1;
    }

    printf("%s: %s\n", label, path);
    free(path);
    return 0;
}

int main(void)
{
    if (check_path(wai_getExecutablePath, "executable") != 0) {
        return 1;
    }
    if (check_path(wai_getModulePath, "module") != 0) {
        return 1;
    }
    return 0;
}

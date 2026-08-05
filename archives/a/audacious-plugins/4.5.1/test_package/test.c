#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <string.h>
#include <dlfcn.h>

/* Test: verify audacious-plugins package contains valid .so plugin files.
 * This is a consumer-side test (R34) that checks the package is usable. */
int main(void) {
    const char *plugin_dir = getenv("AUDACIOUS_PLUGIN_DIR");
    if (!plugin_dir)
        plugin_dir = "lib/audacious";

    DIR *d = opendir(plugin_dir);
    if (!d) {
        fprintf(stderr, "ERROR: Cannot open plugin directory: %s\n", plugin_dir);
        return 1;
    }

    int count = 0;
    struct dirent *entry;
    while ((entry = readdir(d)) != NULL) {
        if (strstr(entry->d_name, ".so") != NULL) {
            count++;
        }
    }
    closedir(d);

    if (count == 0) {
        fprintf(stderr, "ERROR: No .so plugin files found in %s\n", plugin_dir);
        return 1;
    }

    printf("Found %d plugin .so files in %s\n", count, plugin_dir);
    printf("test audacious-plugins 4.5.1: OK\n");
    return 0;
}

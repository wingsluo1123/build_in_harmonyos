/*
 * Consumer test for libadwaita 1.2.0.
 * Calls adw_get_major_version() to verify the library is linked
 * and returns the expected major version (1).
 * No display server is required for this test.
 */
#include <adwaita.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    guint major = adw_get_major_version();
    guint minor = adw_get_minor_version();
    guint micro = adw_get_micro_version();

    if (major != 1) {
        fprintf(stderr, "Expected libadwaita 1.x, got major version %d\n",
                major);
        return 1;
    }

    printf("libadwaita version: %d.%d.%d\n", major, minor, micro);
    return 0;
}

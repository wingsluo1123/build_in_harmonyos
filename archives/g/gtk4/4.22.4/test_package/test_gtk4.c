/*
 * Consumer test for gtk4 4.22.4.
 * Calls gtk_get_major_version() to verify the library is linked
 * and returns the expected major version (4).
 * No display server is required for this test.
 */
#include <gtk/gtk.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    guint major = gtk_get_major_version();
    guint minor = gtk_get_minor_version();
    guint micro = gtk_get_micro_version();

    if (major != 4) {
        fprintf(stderr, "Expected GTK4, got major version %d\n", major);
        return 1;
    }

    printf("GTK version: %d.%d.%d\n", major, minor, micro);
    return 0;
}

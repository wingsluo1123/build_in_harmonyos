#include <stdio.h>
#include <gnome-autoar/gnome-autoar.h>

int main(void) {
    GQuark q = autoar_libarchive_quark();
    if (q == 0) {
        fprintf(stderr, "Failed to get libarchive quark\n");
        return 1;
    }

    gboolean valid = autoar_format_is_valid(AUTOAR_FORMAT_ZIP);
    if (!valid) {
        fprintf(stderr, "ZIP format should be valid\n");
        return 1;
    }

    const char *mime = autoar_format_get_mime_type(AUTOAR_FORMAT_ZIP);
    printf("gnome-autoar: ZIP mime type = %s\n", mime ? mime : "(null)");
    printf("test gnome-autoar 0.4.5: OK\n");
    return 0;
}

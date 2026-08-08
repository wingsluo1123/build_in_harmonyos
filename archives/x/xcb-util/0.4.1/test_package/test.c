/* xcb-util 0.4.1 consumer link + API smoke test.
 *
 * Exercises xcb_atom_name_unique/by_screen/by_resource which are pure
 * string-formatting helpers that do not require an X server connection.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xcb/xcb.h>
#include <xcb/xcb_atom.h>

int main(void) {
    /* 1. xcb_atom_name_unique: should return a non-NULL string */
    char *name = xcb_atom_name_unique("test", 42);
    if (name == NULL) {
        fprintf(stderr, "xcb_atom_name_unique returned NULL\n");
        return 1;
    }
    if (strstr(name, "test") == NULL) {
        fprintf(stderr, "xcb_atom_name_unique result doesn't contain base name: %s\n", name);
        free(name);
        return 2;
    }
    free(name);

    /* 2. xcb_atom_name_by_screen: should return a non-NULL string */
    char *screen_name = xcb_atom_name_by_screen("wm", 0);
    if (screen_name == NULL) {
        fprintf(stderr, "xcb_atom_name_by_screen returned NULL\n");
        return 3;
    }
    free(screen_name);

    /* 3. xcb_atom_name_by_resource: should return a non-NULL string */
    char *res_name = xcb_atom_name_by_resource("prop", 12345);
    if (res_name == NULL) {
        fprintf(stderr, "xcb_atom_name_by_resource returned NULL\n");
        return 4;
    }
    free(res_name);

    if (printf("xcb-util api smoke ok\n") < 0) {
        return 5;
    }
    return 0;
}

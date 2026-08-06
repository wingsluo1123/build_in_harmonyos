/* test_package/test.c — Conan L1 test for mate-menus
 *
 * Calls matemenu_tree_get_type() to verify the library is correctly
 * built and linkable. This is a real API call, not a stub.
 */
#include <stdio.h>
#include <stdlib.h>

/* Must define this before including matemenu-tree.h */
#define MATEMENU_I_KNOW_THIS_IS_UNSTABLE

#include <matemenu-tree.h>

int main(void) {
    /* Call the actual mate-menus API to verify linkage */
    GType tree_type = matemenu_tree_get_type();

    if (tree_type != 0) {
        printf("mate-menus: matemenu_tree_get_type() returned %lu — OK\n",
               (unsigned long)tree_type);
        return 0;
    } else {
        fprintf(stderr, "mate-menus: matemenu_tree_get_type() returned 0 — FAIL\n");
        return 1;
    }
}

#include <libaccounts-glib/ag-manager.h>
#include <stdio.h>

int main(void) {
    /* Verify the library is linked by calling a type registration function.
     * This doesn't require D-Bus and tests the GType system. */
    GType manager_type = AG_TYPE_MANAGER;
    if (manager_type == 0) {
        fprintf(stderr, "AG_TYPE_MANAGER is 0\n");
        return 1;
    }
    printf("AG_TYPE_MANAGER = %lu\n", (unsigned long)manager_type);

    /* ag_manager_new will fail on OHOS without D-Bus,
     * but verifies the library is linked correctly */
    AgManager *manager = ag_manager_new();
    if (manager != NULL) {
        printf("AgManager created\n");
        g_object_unref(manager);
    } else {
        printf("AgManager creation failed (expected without D-Bus)\n");
    }

    printf("libaccounts-glib test passed\n");
    return 0;
}

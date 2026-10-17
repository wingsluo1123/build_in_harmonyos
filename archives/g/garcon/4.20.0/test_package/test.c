/* test_package/test.c — garcon consumer smoke (library API round-trip). */
#include <garcon/garcon.h>
#include <stdio.h>

int main(void)
{
    /* 1. version symbols: garcon exposes extern const guint
     * garcon_major_version / garcon_minor_version (runtime values from
     * the linked library) — assert against the compile-time macros. */
    const guint maj = garcon_major_version;
    const guint min = garcon_minor_version;
    printf("garcon version: %u.%u (headers: %d.%d)\n", maj, min,
           GARCON_MAJOR_VERSION, GARCON_MINOR_VERSION);
    if (maj != (guint)GARCON_MAJOR_VERSION || maj != 4) {
        printf("FAIL: unexpected major %u\n", maj);
        return 1;
    }

    /* 2. menu construction: a nonexistent path is not a construction
     * failure — parsing is lazy; validates GObject class init + the
     * libxfce4util linkage chain. */
    GarconMenu *menu = garcon_menu_new_for_path("/nonexistent/menu.xml");
    if (menu == NULL) {
        printf("FAIL: garcon_menu_new_for_path returned NULL\n");
        return 1;
    }
    g_object_unref(menu);

    /* 3. menu-item pool: construct and free (element type registration). */
    GarconMenuItemPool *pool = garcon_menu_item_pool_new();
    if (pool == NULL) {
        printf("FAIL: pool NULL\n");
        return 1;
    }
    g_object_unref(pool);

    printf("ok: garcon library loaded, version %u.%u, menu+pool round-trip\n",
           maj, min);
    return 0;
}

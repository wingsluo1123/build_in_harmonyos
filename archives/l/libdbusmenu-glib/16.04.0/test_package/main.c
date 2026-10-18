/* Consumer smoke for libdbusmenu-glib 16.04.0 — six object-level
 * assertions against the installed library, no DBus session needed. */
#include <libdbusmenu-glib/dbusmenu-glib.h>
#include <stdio.h>
#include <string.h>

static int fail = 0;
#define CHECK(cond, name) do { \
    if (cond) { printf("PASS %s\n", name); } \
    else { printf("FAIL %s\n", name); fail = 1; } \
} while (0)

int main(void)
{
    DbusmenuMenuitem *mi = dbusmenu_menuitem_new();
    CHECK(mi != NULL, "menuitem_new");

    dbusmenu_menuitem_property_set(mi, DBUSMENU_MENUITEM_PROP_LABEL, "hello");
    const gchar *lbl = dbusmenu_menuitem_property_get(mi, DBUSMENU_MENUITEM_PROP_LABEL);
    CHECK(lbl != NULL && strcmp(lbl, "hello") == 0, "label_roundtrip");

    DbusmenuMenuitem *child = dbusmenu_menuitem_new();
    dbusmenu_menuitem_child_append(mi, child);
    GList *kids = dbusmenu_menuitem_get_children(mi);
    CHECK(kids != NULL && (DbusmenuMenuitem *)kids->data == child, "child_append");

    DbusmenuServer *srv = dbusmenu_server_new("/com/example/smoke");
    CHECK(srv != NULL, "server_new");
    dbusmenu_server_set_root(srv, mi);
    CHECK(dbusmenu_server_get_status(srv) == DBUSMENU_STATUS_NORMAL, "server_status");

    /* C6: find both children, miss, then reject a removed child. */
    DbusmenuMenuitem *second = dbusmenu_menuitem_new();
    gint first_id = dbusmenu_menuitem_get_id(child);
    gint second_id = dbusmenu_menuitem_get_id(second);
    int lifecycle = dbusmenu_menuitem_child_find(second, first_id) == NULL;
    lifecycle = lifecycle && dbusmenu_menuitem_child_append(mi, second);
    lifecycle = lifecycle && dbusmenu_menuitem_child_find(mi, first_id) == child;
    lifecycle = lifecycle && dbusmenu_menuitem_child_find(mi, second_id) == second;
    lifecycle = lifecycle && dbusmenu_menuitem_child_find(mi, -12345) == NULL;
    lifecycle = lifecycle && dbusmenu_menuitem_child_delete(mi, second);
    lifecycle = lifecycle && dbusmenu_menuitem_child_find(mi, second_id) == NULL;
    CHECK(lifecycle, "child_find_lifecycle");
    g_object_unref(second);

    g_object_unref(srv);
    g_object_unref(child);
    g_object_unref(mi);

    printf(fail ? "SMOKE FAIL\n" : "SMOKE PASS\n");
    if (!fail) puts("CONSUMER_TEST_PASS=6/6");
    return fail;
}

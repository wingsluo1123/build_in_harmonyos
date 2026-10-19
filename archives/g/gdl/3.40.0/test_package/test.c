/* test_package/test.c — gdl 3.40.0 OHOS consumer test.
 *
 * 5 checks, each printing one "checkN OK" line on success:
 *   1. GdlDock instantiation — the top-level docking container constructs
 *      headless after gtk_init (exercises the glib-mkenums generated
 *      libgdltypebuiltins registration path for GdlDockPlacement etc.).
 *   2. Real docking operation — gdl_dock_add_item() with a GdlDockItem
 *      docked GDL_DOCK_TOP (exercises the dock master/item machinery).
 *   3. Layout persistence through libxml2 — gdl_dock_layout_save_layout +
 *      gdl_dock_layout_save_to_file + load_from_file roundtrip; the saved
 *      XML must contain a "<dock-layout" root element. This proves the
 *      libxml-2.0 dependency linkage works end to end.
 *   4. GdlDockBar construction bound to the dock master.
 *   5. GdlDockPlaceholder creation attached to a second dock.
 *
 * Note on the adaptation-point guard: unlike ports that disable an exported
 * symbol surface (e.g. ubuntu-private API), this port's OHOS adaptation is
 * entirely build-switch level (--disable-nls / --disable-introspection /
 * --disable-gtk-doc), and gdl exports no symbol whose absence could be
 * dlsym-guarded. The libxml2 layout roundtrip in check3 is the strongest
 * ported-dependency proof available at consumer level. Widget checks run
 * headless on the broadway backend served by broadwayd from the gtk
 * package (libido3/ayatana-ido precedent on this device; gtk4-broadwayd
 * EPERM E471 does not apply to the gtk3 package's broadwayd).
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <glib/gstdio.h>
#include <gtk/gtk.h>
#include <gdl/gdl.h>

int
main (int argc, char **argv)
{
    int failures = 0;

    if (!gtk_init_check (&argc, &argv))
      {
        printf ("check1 FAIL: no display backend for gtk_init\n");
        printf ("check2 FAIL: skipped, no display backend\n");
        printf ("check3 FAIL: skipped, no display backend\n");
        printf ("check4 FAIL: skipped, no display backend\n");
        printf ("check5 FAIL: skipped, no display backend\n");
        return 1;
      }

    /* check 1: GdlDock instantiation (typebuiltins registration path) */
    {
        GtkWidget *dock = gdl_dock_new ();
        if (dock != NULL && GDL_IS_DOCK (dock))
            printf ("check1 OK: GdlDock instantiation\n");
        else
          {
            printf ("check1 FAIL: GdlDock instantiation\n");
            failures++;
          }
    }

    /* check 2: dock an item into the dock (GDL_DOCK_TOP) */
    {
        GtkWidget *dock = gdl_dock_new ();
        GtkWidget *item = gdl_dock_item_new ("consumer-item", "Consumer Item",
                                             GDL_DOCK_ITEM_BEH_NORMAL);
        gboolean added = FALSE;
        if (dock != NULL && item != NULL && GDL_IS_DOCK_ITEM (item))
          {
            gdl_dock_add_item (GDL_DOCK (dock), GDL_DOCK_ITEM (item),
                               GDL_DOCK_TOP);
            added = TRUE;
          }
        if (added && GTK_IS_WIDGET (item) && GDL_IS_DOCK (dock))
            printf ("check2 OK: gdl_dock_add_item GDL_DOCK_TOP\n");
        else
          {
            printf ("check2 FAIL: gdl_dock_add_item\n");
            failures++;
          }
    }

    /* check 3: layout save/load roundtrip through libxml2 */
    {
        GtkWidget *dock = gdl_dock_new ();
        GdlDockLayout *layout;
        gchar *tmpdir, *path;
        gchar *xml = NULL;
        gboolean saved, loaded, has_root = FALSE;

        tmpdir = g_dir_make_tmp ("gdl-tp-XXXXXX", NULL);
        path = g_build_filename (tmpdir, "layout.xml", NULL);
        layout = gdl_dock_layout_new (G_OBJECT (dock));
        gdl_dock_layout_save_layout (layout, "consumer-check");
        saved = gdl_dock_layout_save_to_file (layout, path);
        if (saved && g_file_test (path, G_FILE_TEST_EXISTS))
          {
            gsize len = 0;
            g_file_get_contents (path, &xml, &len, NULL);
            has_root = (xml != NULL && strstr (xml, "<dock-layout") != NULL);
          }
        loaded = gdl_dock_layout_load_from_file (layout, path);
        if (saved && loaded && has_root)
            printf ("check3 OK: layout save/load roundtrip via libxml2\n");
        else
          {
            printf ("check3 FAIL: layout roundtrip saved=%d loaded=%d "
                    "root=%d\n", saved, loaded, has_root);
            failures++;
          }
        g_free (xml);
        g_object_unref (layout);
        if (path)
          {
            g_remove (path);
          }
        g_free (path);
        g_rmdir (tmpdir);
        g_free (tmpdir);
    }

    /* check 4: GdlDockBar bound to the dock master */
    {
        GtkWidget *dock = gdl_dock_new ();
        GtkWidget *bar = gdl_dock_bar_new (G_OBJECT (dock));
        if (bar != NULL && GDL_IS_DOCK_BAR (bar))
            printf ("check4 OK: GdlDockBar\n");
        else
          {
            printf ("check4 FAIL: GdlDockBar\n");
            failures++;
          }
    }

    /* check 5: GdlDockPlaceholder attached to a fresh dock */
    {
        GtkWidget *dock = gdl_dock_new ();
        GtkWidget *ph = gdl_dock_placeholder_new ("consumer-ph",
                                                  GDL_DOCK_OBJECT (dock),
                                                  GDL_DOCK_TOP, FALSE);
        if (ph != NULL && GDL_IS_DOCK_PLACEHOLDER (ph))
            printf ("check5 OK: GdlDockPlaceholder\n");
        else
          {
            printf ("check5 FAIL: GdlDockPlaceholder\n");
            failures++;
          }
    }

    return failures == 0 ? 0 : 1;
}

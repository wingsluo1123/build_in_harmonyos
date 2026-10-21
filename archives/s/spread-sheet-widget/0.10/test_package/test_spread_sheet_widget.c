/* Consumer end-to-end test for the spread-sheet-widget/0.10 HarmonyOS PC
 * package.
 *
 * Built exactly the way a downstream GNOME/GTK project would consume the
 * library: pkg-config module `spread-sheet-widget`, public headers from
 * <ssw-sheet.h> / <ssw-virtual-model.h>, and the shared library produced by
 * libtool.
 *
 * The program is a real GTK client: it opens a GtkWindow with an SswSheet,
 * lets GTK realize and map it on the headless broadway backend, then drives
 * the public API the way the upstream demo does:
 *
 *   - SswVirtualModel as the GtkTreeModel backing store (shape, cell text,
 *     live row insertion while a view is attached)
 *   - SswSheet data-model attachment and the editable/active-cell contract
 *     (set_active_cell is a no-op while the sheet is not editable)
 *   - selection-changed delivery with the SswRange payload
 *   - ssw_sheet_get_button corner button
 *   - ssw_sheet_scroll_to moving both viewport adjustments over a big model
 *
 * Every check prints one TEST PASS/TEST FAIL line; the TEST SUMMARY line and
 * the process exit code are what the Conan test_package relies on.
 */
#include <ssw-sheet.h>
#include <ssw-virtual-model.h>

#include <gtk/gtk.h>

#include <stdio.h>

static int g_passed = 0;
static int g_failed = 0;

static void
report (const char *name, gboolean ok, const char *detail)
{
  if (ok)
    {
      ++g_passed;
      printf ("TEST PASS: %s\n", name);
    }
  else
    {
      ++g_failed;
      printf ("TEST FAIL: %s\n", name);
      if (detail && *detail)
        printf ("--- detail ---\n%s\n--- end detail ---\n", detail);
    }
}

static int g_selection_signals = 0;
static SswRange g_last_selection = { -1, -1, -1, -1 };

static void
on_selection_changed (SswSheet *sheet, SswRange *range, gpointer user_data)
{
  (void) sheet;
  (void) user_data;
  ++g_selection_signals;
  g_last_selection = *range;
}

static void
pump_until_mapped (GtkWidget *window)
{
  int i;
  for (i = 0; i < 300; ++i)
    {
      while (gtk_events_pending ())
        gtk_main_iteration ();
      if (gtk_widget_get_mapped (window))
        return;
      g_usleep (10000);
    }
}

int
main (int argc, char **argv)
{
  if (!gtk_init_check (&argc, &argv))
    {
      printf ("TEST FAIL: gtk_init_check initialises the broadway GdkDisplay\n");
      printf ("TEST SUMMARY: 0 passed, 1 failed\n");
      return 1;
    }
  report ("gtk_init_check initialises the broadway GdkDisplay", TRUE, NULL);

  GtkWidget *sheet = ssw_sheet_new ();
  report ("ssw_sheet_new returns an SswSheet GtkBin widget",
          sheet != NULL && SSW_IS_SHEET (sheet) && GTK_IS_BIN (sheet), NULL);

  GObject *vmodel_obj = ssw_virtual_model_new ();
  GtkTreeModel *model = GTK_TREE_MODEL (vmodel_obj);
  report ("ssw_virtual_model_new implements GtkTreeModel",
          vmodel_obj != NULL && GTK_IS_TREE_MODEL (model), NULL);

  g_object_set (vmodel_obj,
                "rows", (guint) 240,
                "columns", (guint) 30,
                NULL);
  guint rows = 0, cols = 0;
  g_object_get (vmodel_obj, "rows", &rows, "columns", &cols, NULL);
  report ("virtual model rows/columns properties round-trip",
          rows == 240 && cols == 30, NULL);

  {
    char *detail = g_strdup_printf ("n_columns=%d n_children=%d",
                                    gtk_tree_model_get_n_columns (model),
                                    gtk_tree_model_iter_n_children (model, NULL));
    report ("GtkTreeModel reports the configured 240x30 shape",
            gtk_tree_model_get_n_columns (model) == 30
            && gtk_tree_model_iter_n_children (model, NULL) == 240,
            detail);
    g_free (detail);
  }

  {
    GtkTreeIter iter;
    gchar *cell = NULL;
    if (gtk_tree_model_iter_nth_child (model, &iter, NULL, 3))
      gtk_tree_model_get (model, &iter, 2, &cell, -1);
    report ("virtual model synthesises the r3c2 cell value",
            g_strcmp0 (cell, "r3c2") == 0, cell);
    g_free (cell);
  }

  g_object_set (sheet, "data-model", model, NULL);
  {
    GtkTreeModel *attached = NULL;
    g_object_get (sheet, "data-model", &attached, NULL);
    report ("sheet data-model property round-trips to the attached model",
            attached == model, NULL);
  }

  {
    gboolean editable = TRUE;
    g_object_get (sheet, "editable", &editable, NULL);
    report ("sheet starts non-editable", editable == FALSE, NULL);
  }

  /* Upstream contract: ssw_sheet_body_set_active_cell returns immediately
     when the body is not editable, so the active cell stays unset. */
  {
    gint col = -1, row = -1;
    gboolean had = ssw_sheet_get_active_cell (SSW_SHEET (sheet), &col, &row);
    ssw_sheet_set_active_cell (SSW_SHEET (sheet), 2, 4, NULL);
    col = -1;
    row = -1;
    gboolean has = ssw_sheet_get_active_cell (SSW_SHEET (sheet), &col, &row);
    report ("active cell stays unset while the sheet is not editable",
            had == FALSE && has == FALSE, NULL);
  }

  GtkWidget *window = gtk_window_new (GTK_WINDOW_TOPLEVEL);
  gtk_window_set_title (GTK_WINDOW (window), "ssw consumer test");
  gtk_window_set_default_size (GTK_WINDOW (window), 800, 600);
  gtk_container_add (GTK_CONTAINER (window), sheet);
  gtk_widget_show_all (window);
  pump_until_mapped (window);
  report ("sheet realizes and maps in a GtkWindow on the broadway backend",
          gtk_widget_get_realized (sheet) && gtk_widget_get_mapped (window),
          NULL);

  {
    GtkWidget *button = ssw_sheet_get_button (SSW_SHEET (sheet));
    report ("ssw_sheet_get_button returns the corner GtkButton",
            button != NULL && GTK_IS_BUTTON (button), NULL);
  }

  /* The live view must follow row insertions announced by the model. */
  {
    g_object_set (vmodel_obj, "rows", (guint) 280, NULL);
    char *detail = g_strdup_printf ("n_children=%d",
                                    gtk_tree_model_iter_n_children (model, NULL));
    report ("attached sheet model accepts a live row insertion (240 -> 280)",
            gtk_tree_model_iter_n_children (model, NULL) == 280, detail);
    g_free (detail);
  }

  g_signal_connect (sheet, "selection-changed",
                    G_CALLBACK (on_selection_changed), NULL);
  g_object_set (sheet, "editable", TRUE, NULL);
  {
    gboolean editable = FALSE;
    g_object_get (sheet, "editable", &editable, NULL);
    report ("editable property turns the sheet editable", editable == TRUE, NULL);
  }

  ssw_sheet_set_active_cell (SSW_SHEET (sheet), 2, 4, NULL);
  {
    gint col = -1, row = -1;
    gboolean has = ssw_sheet_get_active_cell (SSW_SHEET (sheet), &col, &row);
    char *detail = g_strdup_printf ("col=%d row=%d returned=%d",
                                    col, row, has);
    report ("ssw_sheet_set_active_cell/get_active_cell round-trips (2,4)",
            has == TRUE && col == 2 && row == 4, detail);
    g_free (detail);
  }

  {
    char *detail = g_strdup_printf (
        "signals=%d range=[%d,%d]-[%d,%d]", g_selection_signals,
        g_last_selection.start_x, g_last_selection.start_y,
        g_last_selection.end_x, g_last_selection.end_y);
    report ("selection-changed announced the new single-cell range",
            g_selection_signals >= 1
            && g_last_selection.start_x == 2
            && g_last_selection.start_y == 4
            && g_last_selection.end_x == 2
            && g_last_selection.end_y == 4,
            detail);
    g_free (detail);
  }

  {
    gboolean gridlines = FALSE;
    g_object_set (sheet, "gridlines", TRUE, NULL);
    g_object_get (sheet, "gridlines", &gridlines, NULL);
    report ("gridlines property round-trips", gridlines == TRUE, NULL);
  }

  /* Scroll a big model: both viewport adjustments must have room and move. */
  ssw_sheet_scroll_to (SSW_SHEET (sheet), 20, 150);
  {
    GtkAdjustment *hadj = SSW_SHEET (sheet)->hadj[0];
    GtkAdjustment *vadj = SSW_SHEET (sheet)->vadj[0];
    char *detail = g_strdup_printf (
        "h=%.1f upper=%.1f page=%.1f v=%.1f upper=%.1f page=%.1f",
        gtk_adjustment_get_value (hadj), gtk_adjustment_get_upper (hadj),
        gtk_adjustment_get_page_size (hadj),
        gtk_adjustment_get_value (vadj), gtk_adjustment_get_upper (vadj),
        gtk_adjustment_get_page_size (vadj));
    report ("ssw_sheet_scroll_to moves both viewport adjustments",
            gtk_adjustment_get_upper (hadj)
            > gtk_adjustment_get_page_size (hadj)
            && gtk_adjustment_get_upper (vadj)
            > gtk_adjustment_get_page_size (vadj)
            && gtk_adjustment_get_value (hadj) > 0
            && gtk_adjustment_get_value (vadj) > 0,
            detail);
    g_free (detail);
  }

  gtk_widget_destroy (window);
  while (gtk_events_pending ())
    gtk_main_iteration ();

  printf ("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
  return g_failed == 0 ? 0 : 1;
}

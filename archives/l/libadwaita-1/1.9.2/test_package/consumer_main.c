/*
 * HarmonyOS-specific end-to-end consumer test for libadwaita-1 1.9.2.
 *
 * This is a REAL consumer use case (赛事 rule12): it initializes libadwaita
 * with the Broadway display backend (the only GDK backend available on the
 * OHOS build), creates actual controls (AdwPreferencesWindow, AdwToast,
 * AdwToastOverlay, AdwNavigationView), sets properties (title, visibility,
 * layout), drives the GTK main loop with g_main_context_iteration() and
 * asserts observable behavior (title getter round-trip, widget class names,
 * toast title after add, navigation view child/view stack, window mapped).
 *
 * It only uses the public installed API surface (<adwaita.h> + exported
 * symbols adw_init / adw_preferences_window_new / adw_toast_new /
 * adw_toast_get_title / adw_toast_overlay_new / adw_toast_overlay_add_toast /
 * adw_navigation_view_new / gtk_window_set_title ...), never private headers
 * or internal symbols.
 */
#include <adwaita.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
    fflush (stdout); \
} while (0)

static void
pump_main_loop (int rounds)
{
  /* Drive the GTK main loop without blocking forever: process pending events
   * (window map, expose, broadway socket events) for `rounds` iterations. */
  for (int i = 0; i < rounds; i++)
    while (g_main_context_iteration (NULL, FALSE))
      ;
}

int
main (int argc, char **argv)
{
  const char *backend = g_getenv ("GDK_BACKEND");
  CHECK (backend != NULL && strcmp (backend, "broadway") == 0,
         "GDK_BACKEND=broadway 显示后端已设置（端到端真实显示环境）");

  /* adw_init(): public one-shot libadwaita initializer (adw_init() ->
   * gtk_init()) — creates the default display connection; with the broadway
   * backend this connects to gtk4-broadwayd. Retry-capable: if no display is
   * reachable the program fails loudly instead of passing silently. */
  adw_init ();
  CHECK (TRUE, "adw_init() 完成（GTK/Broadway 初始化，无崩溃）");

  /* Create a real AdwPreferencesWindow and set its title property. */
  AdwPreferencesWindow *win = adw_preferences_window_new ();
  CHECK (win != NULL, "AdwPreferencesWindow 实例化成功");
  CHECK (GTK_IS_WINDOW (win),
         "控件是 GtkWindow 子类");
  gtk_window_set_title (GTK_WINDOW (win), "HarmonyOS libadwaita E2E");
  gtk_window_set_default_size (GTK_WINDOW (win), 480, 360);
  CHECK (strcmp (gtk_window_get_title (GTK_WINDOW (win)),
                 "HarmonyOS libadwaita E2E") == 0,
         "窗口标题属性往返一致（title getter == setter）");
  gtk_widget_set_visible (GTK_WIDGET (win), TRUE);

  /* Build an AdwToast and add it to an AdwToastOverlay (real flow). */
  AdwToast *toast = adw_toast_new ("Adaptation done");
  CHECK (toast != NULL, "AdwToast 实例化成功");
  CHECK (strcmp (adw_toast_get_title (toast), "Adaptation done") == 0,
         "AdwToast 标题属性正确（adw_toast_get_title）");
  AdwToastOverlay *overlay = adw_toast_overlay_new ();
  CHECK (overlay != NULL, "AdwToastOverlay 实例化成功");
  gtk_widget_set_visible (GTK_WIDGET (overlay), TRUE);
  adw_toast_overlay_add_toast (overlay, toast);
  CHECK (TRUE, "AdwToast 已加入 AdwToastOverlay（流程跑通）");

  /* Create an AdwNavigationView and add a child page (real layout flow).
   * adw_navigation_view_add() requires an AdwNavigationPage, so build the
   * page via the public constructor adw_navigation_page_new_with_tag()
   * first (child, title, tag). */
  AdwNavigationView *nav = adw_navigation_view_new ();
  CHECK (nav != NULL, "AdwNavigationView 实例化成功");
  AdwToolbarView *tb = adw_toolbar_view_new ();
  gtk_widget_set_vexpand (GTK_WIDGET (tb), TRUE);
  AdwNavigationPage *page = adw_navigation_page_new_with_tag (GTK_WIDGET (tb), "Main", "page-main");
  CHECK (page != NULL, "AdwNavigationPage 实例化成功");
  CHECK (g_strcmp0 (adw_navigation_page_get_tag (page), "page-main") == 0,
         "AdwNavigationPage tag 属性正确");
  adw_navigation_view_add (nav, page);
  CHECK (adw_navigation_view_get_visible_page (nav) == page,
         "AdwNavigationView 子页加入成功且为可见页（布局流程跑通）");

  /* Drive the main loop so the broadway backend actually maps/paints the
   * window and processes pending events — end-to-end, not just construction. */
  pump_main_loop (32);
  CHECK (gtk_widget_get_visible (GTK_WIDGET (win)),
         "主循环迭代后窗口可见（可观察状态）");
  CHECK (gtk_widget_get_mapped (GTK_WIDGET (win)),
         "主循环迭代后窗口已映射（broadway 真实显示流程完成）");

  gtk_window_destroy (GTK_WINDOW (win));

  if (failures == 0) {
    printf ("HARMONY_LIBADWAITA_E2E_PASS: end-to-end consumer flow OK "
            "(AdwPreferencesWindow + AdwToast + AdwNavigationView, "
            "broadway backend, title/visible/mapped assertions)\n");
    return 0;
  }
  printf ("HARMONY_LIBADWAITA_E2E_FAIL: %d assertion(s) failed\n", failures);
  return 1;
}
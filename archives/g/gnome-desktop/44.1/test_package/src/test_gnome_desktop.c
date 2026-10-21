/* OHOS consumer test for gnome-desktop 44.1 (test_package).
 *
 * 目的：在已安装的 conan 包上验证真实消费者可用性（非空壳，R34）：
 *   1. 版本 API：gnome_get_platform_version() 与头文件宏一致（>=43 引入）
 *   2. locale 归一化：gnome_normalize_locale()
 *   3. 语言名解析：gnome_get_language_from_locale()（依赖 ISO-639 数据）
 *   4. GnomeWallClock：GSettings schema + 定时器 + 24h/12h 格式化
 *   5. GnomeXkbInfo：XKB 规则 XML 解析（XKB_CONFIG_ROOT 指向 xkeyboard-config）
 *
 * 断言逐项打印 PASS/FAIL，任一失败进程返回 1（conan test 判负）。
 */
/* gnome-languages.h / gnome-wall-clock.h / gnome-xkb-info.h 属不稳定 API，
 * 上游要求先定义 GNOME_DESKTOP_USE_UNSTABLE_API（同 meson 的 test_args）。 */
#define GNOME_DESKTOP_USE_UNSTABLE_API

#include <glib.h>
#include <gdesktop-enums.h>

#include <libgnome-desktop/gnome-desktop-version.h>
#include <libgnome-desktop/gnome-languages.h>
#include <libgnome-desktop/gnome-wall-clock.h>
#include <libgnome-desktop/gnome-xkb-info.h>

static int total = 0;
static int failed = 0;

static void
check (gboolean ok, const char *name, const char *detail)
{
  total++;
  if (ok)
    g_print ("PASS %02d: %s", total, name);
  else
    {
      failed++;
      g_print ("FAIL %02d: %s", total, name);
    }
  if (detail != NULL && *detail != '\0')
    g_print (" [%s]", detail);
  g_print ("\n");
}

int
main (int argc, char **argv)
{
  int platform;
  g_autofree char *normalized = NULL;
  g_autofree char *language = NULL;
  g_autoptr (GnomeWallClock) clock = NULL;
  g_autofree char *clock_text = NULL;
  g_autoptr (GDateTime) now = NULL;
  g_autofree char *fmt24 = NULL;
  g_autofree char *fmt12 = NULL;
  g_autoptr (GnomeXkbInfo) xkb = NULL;
  GList *layouts = NULL;
  guint layout_count = 0;
  const gchar *display_name = NULL;
  const gchar *short_name = NULL;
  const gchar *xkb_layout = NULL;
  const gchar *xkb_variant = NULL;
  gboolean have_us = FALSE;

  (void) argc;
  (void) argv;

  g_print ("== gnome-desktop 44.1 OHOS consumer test ==\n");

  /* 1. 平台版本：GNOME_DESKTOP_PLATFORM_VERSION == 44 */
  platform = gnome_get_platform_version ();
  {
    char detail[64];
    g_snprintf (detail, sizeof detail, "platform=%d macro=%d",
                platform, GNOME_DESKTOP_PLATFORM_VERSION);
    check (platform == GNOME_DESKTOP_PLATFORM_VERSION && platform == 44,
           "gnome_get_platform_version() == 44", detail);
  }

  /* 2. locale 归一化 */
  normalized = gnome_normalize_locale ("en_US.UTF-8");
  check (g_strcmp0 (normalized, "en_US.UTF-8") == 0,
         "gnome_normalize_locale(\"en_US.UTF-8\")", normalized);

  /* 3. 语言名解析（ISO-639 数据来自 iso-codes 依赖） */
  language = gnome_get_language_from_locale ("en_US.UTF-8", NULL);
  check (language != NULL && *language != '\0',
         "gnome_get_language_from_locale(\"en_US.UTF-8\")", language);

  /* 4. GnomeWallClock：GSettings + 时间格式化 */
  clock = gnome_wall_clock_new ();
  clock_text = g_strdup (gnome_wall_clock_get_clock (clock));
  check (clock_text != NULL && strchr (clock_text, ':') != NULL,
         "gnome_wall_clock_get_clock() 非空且含冒号", clock_text);

  now = g_date_time_new_local (2026, 1, 2, 13, 5, 0.0);
  fmt24 = gnome_wall_clock_string_for_datetime (clock, now,
                                                G_DESKTOP_CLOCK_FORMAT_24H,
                                                FALSE, FALSE, FALSE);
  fmt12 = gnome_wall_clock_string_for_datetime (clock, now,
                                                G_DESKTOP_CLOCK_FORMAT_12H,
                                                FALSE, FALSE, FALSE);
  {
    char detail[128];
    g_snprintf (detail, sizeof detail, "24h=\"%s\" 12h=\"%s\"",
                fmt24 ? fmt24 : "(null)", fmt12 ? fmt12 : "(null)");
    check (fmt24 != NULL && strstr (fmt24, "13") != NULL
             && strstr (fmt24, "PM") == NULL && strstr (fmt24, "AM") == NULL
             && g_strcmp0 (fmt24, fmt12) != 0,
           "gnome_wall_clock_string_for_datetime() 24h/12h 差异化",
           detail);
  }

  /* 5. GnomeXkbInfo：解析 XKB 规则（XKB_CONFIG_ROOT 由 test_package 注入） */
  xkb = gnome_xkb_info_new ();
  layouts = gnome_xkb_info_get_all_layouts (xkb);
  layout_count = g_list_length (layouts);
  have_us = gnome_xkb_info_get_layout_info (xkb, "us", &display_name,
                                            &short_name, &xkb_layout,
                                            &xkb_variant);
  {
    char detail[160];
    g_snprintf (detail, sizeof detail, "layouts=%u us=\"%s\"",
                layout_count, display_name ? display_name : "(null)");
    check (layout_count > 0 && have_us && display_name != NULL
             && *display_name != '\0',
           "gnome_xkb_info_get_all_layouts()/get_layout_info(\"us\")", detail);
  }
  g_list_free (layouts);

  g_print ("== result: %d/%d passed, %d failed ==\n",
           total - failed, total, failed);
  return failed == 0 ? 0 : 1;
}

/* gtkgettext_probe.c — V2 最小验收件（随 test_package 出厂，作为配方自带的回归防线）
 *
 * 目的：把"加载 libgtk-3 后首次 gettext 译文查找永久 futex 等待"这一平台级死锁
 * 变成可在 CI/真机自动判定的用例，避免同类缺陷静默出厂。
 *
 * 原理：本程序**只链接 libgtk-3**（使 libgtk 导出的 g_libintl_* 进入进程并赢得
 * libglib 的符号查找），随后做一次译文查找；不需要任何显示后端。
 *
 *   gtk/3.24.38（gettext shim 默认可见导出）→ 挂死（卡在 g_dgettext 内）
 *   gtk/3.24.43 / 任何隐藏该 shim 的构建     → 打印 "[gtkprobe] done" 并返回 0
 *
 * 有意不包含任何头文件（无需 sysroot / pkg-config），因此可直接被 CMake 目标编译。
 * 手写链接参考：
 *   clang -O1 -o gtk_gettext_probe gtkgettext_probe.c \
 *         -L<gtk pkg>/lib -lgtk-3 -L<glib pkg>/lib -lglib-2.0
 */

extern const char *g_dgettext (const char *domain, const char *msgid);
extern const char *glib_gettext (const char *str);
extern char *setlocale (int category, const char *locale);
extern long write (int fd, const void *buf, unsigned long count);

#define LC_ALL_CATEGORY 6

static void say (const char *s)
{
  unsigned long n = 0;
  while (s[n])
    n++;
  write (2, s, n);
}

int main (void)
{
  say ("[gtkprobe] start (libgtk-3 is loaded)\n");

  setlocale (LC_ALL_CATEGORY, "");
  say ("[gtkprobe] after setlocale\n");

  (void) glib_gettext ("probe");
  say ("[gtkprobe] after glib_gettext\n");

  (void) g_dgettext ("glib20", "probe");
  say ("[gtkprobe] after g_dgettext\n");

  say ("[gtkprobe] done\n");
  return 0;
}

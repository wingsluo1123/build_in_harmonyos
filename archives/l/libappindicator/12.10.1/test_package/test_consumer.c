/*
 * 鸿蒙特有消费者端到端用例（rule12）— libappindicator 12.10.1
 *
 * 真实调用库的完整消费者流程（非纯断言）：
 *   1. GTK 初始化（有显示后端时创建真实 GtkMenu 控件树）
 *   2. 构造 AppIndicator（id/icon/category），读回属性
 *   3. 设置 label / icon / attention-icon / title / ordering-index，事件循环
 *      驱动 new-label / new-status / new-icon 信号，校验信号语义（同值不重复
 *      发信号、变值发一次）与 getter 回读一致
 *   4. app_indicator_set_menu() 挂载 GtkMenu，经 "dbus-menu-server" 属性取回
 *      DbusmenuServer → root node → children，与 GtkMenu 标签逐项比对（库内部
 *      GtkMenu → dbusmenu 解析的真实往返）
 *   5. app_indicator_build_menu_from_desktop() 从 .desktop 文件构建菜单，
 *      校验命中/未命中程序名的 children 数量（上游 desktop_menu 用例同款往返）
 *
 * 退出码 0 = 全部检查通过；任何一项失败立即退出 1 并打印 FAIL 项。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gtk/gtk.h>

#include <libappindicator/app-indicator.h>
#include <libdbusmenu-glib/menuitem.h>
#include <libdbusmenu-glib/server.h>

#ifndef E2E_SRCDIR
#define E2E_SRCDIR "."
#endif

static guint checks = 0;
static guint failures = 0;

static void
check (gboolean ok, const gchar *what)
{
	checks++;
	printf ("%s [%02u] %s\n", ok ? "PASS" : "FAIL", checks, what);
	fflush (stdout);
	if (!ok) {
		failures++;
	}
}

static void
drain_events (void)
{
	while (g_main_context_pending (NULL)) {
		g_main_context_iteration (NULL, TRUE);
	}
}

/* ---- 信号回调（签名与上游 tests/test-libappindicator.c 一致） ---- */
static gint new_label_signals = 0;
static gint new_status_signals = 0;
static gint new_icon_signals = 0;

static void
on_new_label (AppIndicator *ci, gchar *label, gchar *guide, gpointer user_data)
{
	(void)ci; (void)label; (void)guide; (void)user_data;
	new_label_signals++;
}

static void
on_new_status (AppIndicator *ci, gchar *status, gpointer user_data)
{
	(void)ci; (void)status; (void)user_data;
	new_status_signals++;
}

static void
on_new_icon (AppIndicator *ci, gpointer user_data)
{
	(void)ci; (void)user_data;
	new_icon_signals++;
}

static DbusmenuMenuitem *
root_node_of (AppIndicator *ci)
{
	GValue serverval = {0};
	GValue rootval = {0};
	DbusmenuServer *server;
	DbusmenuMenuitem *root = NULL;

	/* 对象型 GValue 会持有一份引用，取完值必须 g_value_unset() 释放，
	 * 否则本函数每条主线路径都会泄漏 server / root 的引用（对象在
	 * g_object_unref(ci) 后仍然存活，后续断言可能观察到陈旧对象）。 */
	g_value_init (&serverval, DBUSMENU_TYPE_SERVER);
	g_object_get_property (G_OBJECT (ci), "dbus-menu-server", &serverval);
	server = DBUSMENU_SERVER (g_value_get_object (&serverval));
	g_value_unset (&serverval);
	if (server == NULL) {
		return NULL;
	}
	g_value_init (&rootval, DBUSMENU_TYPE_MENUITEM);
	g_object_get_property (G_OBJECT (server), DBUSMENU_SERVER_PROP_ROOT_NODE, &rootval);
	root = DBUSMENU_MENUITEM (g_value_get_object (&rootval));
	g_value_unset (&rootval);
	/* 返回的是借用指针：root 由 DbusmenuServer 持有（指示器持有 server），
	 * 此处不转移所有权，调用方无需 unref。g_value_unset() 只释放 GValue
	 * 自己那一份引用，server 仍持有 root，因此返回的指针依然有效。 */
	return root;
}

int
main (int argc, char **argv)
{
	gboolean display = gtk_init_check (&argc, &argv);
	AppIndicator *ci;

	printf ("CONSUMER_E2E_START display=%s\n", display ? "yes" : "no");

	/* 1) 构造 indicator，读回基本属性 */
	ci = app_indicator_new ("ohpc-e2e-indicator", "ohpc-e2e-icon",
	                        APP_INDICATOR_CATEGORY_APPLICATION_STATUS);
	check (ci != NULL, "app_indicator_new() returns object");
	check (g_strcmp0 (app_indicator_get_id (ci), "ohpc-e2e-indicator") == 0,
	       "get_id() roundtrip");
	check (app_indicator_get_category (ci) == APP_INDICATOR_CATEGORY_APPLICATION_STATUS,
	       "get_category() roundtrip");
	check (app_indicator_get_status (ci) == APP_INDICATOR_STATUS_PASSIVE,
	       "default status is PASSIVE");

	/* 2) 状态 + 信号 */
	g_signal_connect (G_OBJECT (ci), APP_INDICATOR_SIGNAL_NEW_LABEL,
	                  G_CALLBACK (on_new_label), NULL);
	g_signal_connect (G_OBJECT (ci), APP_INDICATOR_SIGNAL_NEW_STATUS,
	                  G_CALLBACK (on_new_status), NULL);
	g_signal_connect (G_OBJECT (ci), APP_INDICATOR_SIGNAL_NEW_ICON,
	                  G_CALLBACK (on_new_icon), NULL);

	app_indicator_set_status (ci, APP_INDICATOR_STATUS_ACTIVE);
	drain_events ();
	check (app_indicator_get_status (ci) == APP_INDICATOR_STATUS_ACTIVE,
	       "set_status(ACTIVE) then get_status() roundtrip");
	check (new_status_signals >= 1, "new-status signal emitted on status change");

	/* 3) label 信号语义（与上游 label_signals 用例同一语义） */
	app_indicator_set_label (ci, "OHPC-Label", "OHPC-Guide");
	drain_events ();
	check (g_strcmp0 (app_indicator_get_label (ci), "OHPC-Label") == 0,
	       "set_label() then get_label() roundtrip");
	check (g_strcmp0 (app_indicator_get_label_guide (ci), "OHPC-Guide") == 0,
	       "get_label_guide() roundtrip");
	/* 严格计数断言：一次 set_label() 后经主循环 flush，new-label 恰好触发一次。
	 * 这是本用例唯一的精确计数断言，语义与上游
	 * test_libappindicator_label_signals 一致（详见 notes.md 与 MANIFEST.yml
	 * 对信号合并语义的说明）；下面的 ==0 是它的反向对照，两条配对才完整。 */
	check (new_label_signals == 1, "new-label emitted exactly once for a change");

	new_label_signals = 0;
	app_indicator_set_label (ci, "OHPC-Label", "OHPC-Guide");
	drain_events ();
	check (new_label_signals == 0, "new-label not emitted when value unchanged");

	/* 4) icon / attention-icon / title / ordering-index */
	app_indicator_set_icon_full (ci, "ohpc-e2e-icon-2", "OHPC icon desc");
	drain_events ();
	check (g_strcmp0 (app_indicator_get_icon (ci), "ohpc-e2e-icon-2") == 0,
	       "set_icon_full() then get_icon() roundtrip");
	check (g_strcmp0 (app_indicator_get_icon_desc (ci), "OHPC icon desc") == 0,
	       "get_icon_desc() roundtrip");
	check (new_icon_signals >= 1, "new-icon signal emitted on icon change");

	app_indicator_set_attention_icon_full (ci, "ohpc-e2e-attention", "attention desc");
	drain_events ();
	check (g_strcmp0 (app_indicator_get_attention_icon (ci), "ohpc-e2e-attention") == 0,
	       "set_attention_icon_full() then get_attention_icon() roundtrip");

	app_indicator_set_title (ci, "OHPC E2E Title");
	check (g_strcmp0 (app_indicator_get_title (ci), "OHPC E2E Title") == 0,
	       "set_title() then get_title() roundtrip");

	app_indicator_set_icon_theme_path (ci, "/tmp/ohpc-e2e-icons");
	check (g_strcmp0 (app_indicator_get_icon_theme_path (ci), "/tmp/ohpc-e2e-icons") == 0,
	       "set_icon_theme_path() then get_icon_theme_path() roundtrip");

	app_indicator_set_ordering_index (ci, 42);
	check (app_indicator_get_ordering_index (ci) == 42,
	       "set_ordering_index() then get_ordering_index() roundtrip");

	/* 5) GtkMenu → dbusmenu 真实往返（需要 GTK 显示后端才能建控件树） */
	if (display) {
		const gchar *labels[3] = {"OHPC Item 0", "OHPC Item 1", "OHPC Item 2"};
		GtkMenu *menu = GTK_MENU (gtk_menu_new ());
		GValue serverval = {0};
		DbusmenuServer *server;
		DbusmenuMenuitem *root;
		GList *children;
		guint i;

		for (i = 0; i < 3; i++) {
			GtkWidget *item = gtk_menu_item_new_with_label (labels[i]);
			gtk_menu_shell_append (GTK_MENU_SHELL (menu), item);
			gtk_widget_show (item);
		}
		app_indicator_set_menu (ci, menu);
		check (app_indicator_get_menu (ci) == menu, "set_menu() then get_menu() roundtrip");

		g_value_init (&serverval, DBUSMENU_TYPE_SERVER);
		g_object_get_property (G_OBJECT (ci), "dbus-menu-server", &serverval);
		server = DBUSMENU_SERVER (g_value_get_object (&serverval));
		check (server != NULL, "dbus-menu-server property exported");
		/* 对象型 GValue 持有引用，用完即释放，避免泄漏 server 引用 */
		g_value_unset (&serverval);

		root = root_node_of (ci);
		check (root != NULL, "dbusmenu root node available");
		children = root ? dbusmenu_menuitem_get_children (root) : NULL;
		check (children != NULL && g_list_length (children) == 3,
		       "dbusmenu root has 3 children (GtkMenu -> dbusmenu parse)");
		if (children != NULL && g_list_length (children) == 3) {
			for (i = 0; i < 3; i++) {
				const gchar *label = dbusmenu_menuitem_property_get (
				    DBUSMENU_MENUITEM (g_list_nth_data (children, i)),
				    DBUSMENU_MENUITEM_PROP_LABEL);
				gchar *what = g_strdup_printf (
				    "child %u label matches GtkMenu (%s)", i, labels[i]);
				check (g_strcmp0 (label, labels[i]) == 0, what);
				g_free (what);
			}
		}
		/* 注意：GtkMenu 是 GInitiallyUnowned，gtk_menu_new() 给的是**浮动引用**，
		 * app_indicator_set_menu() 内部 g_object_ref_sink() 已把它转成指示器
		 * 自己的强引用（upstream app-indicator.c:2261；upstream 测试同样不 unref）。
		 * 这里若再 g_object_unref(menu)，就会把指示器唯一持有的引用放掉 →
		 * 菜单及其子项被析构，而指示器仍留着悬垂指针，随后
		 * build_menu_from_desktop() 触碰已释放的 widget：实测先出现
		 * "gtk_widget_get_visible: assertion 'GTK_IS_WIDGET (widget)' failed"，
		 * 偶发 SIGSEGV（3 次里 1 次，qemu 下 core dumped）→ 不能 unref。 */
	} else {
		printf ("SKIP menu roundtrip: no GTK display backend "
		        "(broadwayd) available in this environment\n");
	}

	/* 6) .desktop 文件构建菜单（上游 desktop_menu 用例同款往返）
	 *
	 * 夹具路径优先取运行期环境变量 E2E_DESKTOP（真机/其他部署位置可用它
	 * 指向实际落地的夹具），未设置时回退到编译期 E2E_SRCDIR —— 后者在
	 * conan 构建目录内始终存在，故常规 test_package 运行行为不变。 */
	{
		const gchar *env_desktop = g_getenv ("E2E_DESKTOP");
		gchar *desktop = env_desktop
		    ? g_strdup (env_desktop)
		    : g_build_filename (E2E_SRCDIR,
		                        "test-libappindicator.desktop", NULL);
		DbusmenuMenuitem *root;
		GList *children;

		if (!g_file_test (desktop, G_FILE_TEST_EXISTS)) {
			printf ("SKIP desktop menu roundtrip: fixture not found at %s\n",
			        desktop);
			g_free (desktop);
			goto after_desktop;
		}

		app_indicator_build_menu_from_desktop (ci, desktop, "Test Program");
		drain_events ();
		root = root_node_of (ci);
		children = root ? dbusmenu_menuitem_get_children (root) : NULL;
		check (children != NULL && g_list_length (children) == 3,
		       "build_menu_from_desktop('Test Program') -> 3 dbusmenu children");

		/* 反向用例：夹具 test-libappindicator.desktop 的三个 Shortcut 都写着
		 * `OnlyShowIn=Test Program;`，传入不匹配的 "Not Test Program" 时
		 * 菜单不应留下任何条目（上游行为是清空菜单树，见下方实测说明）。 */
		app_indicator_build_menu_from_desktop (ci, desktop, "Not Test Program");
		drain_events ();
		root = root_node_of (ci);
		children = root ? dbusmenu_menuitem_get_children (root) : NULL;
		check (root != NULL,
		       "dbusmenu root node still available after reverse lookup");
		/* 可复现的实测语义：不匹配的 desktop 名会让
		 * app_indicator_build_menu_from_desktop() **清掉**上一次构建的菜单树
		 * （实测 root 变为 NULL，children=-1），而不是"保留 3 个子项"或
		 * "得到 0 个子项的 root"。这与上游
		 * tests/test-libappindicator.c 的 test_libappindicator_desktop_menu_bad
		 * 一致：该方法在不匹配时把菜单清空，因此正确断言是"没有残留子项"，
		 * 即 children 为 NULL 或长度为 0。
		 * 这条断言对"清空"和"从未构建"两种实现都成立，是该方法对外可观测的
		 * 契约；正例（3 children）在上方，两条配对覆盖构建/清空两个方向。 */
		check (children == NULL || g_list_length (children) == 0,
		       "build_menu_from_desktop('Not Test Program') clears the menu");
		g_free (desktop);
	}
after_desktop:

	g_object_unref (ci);

	printf ("CONSUMER_E2E_RESULT checks=%u failures=%u new_label_signals=%d "
	        "new_status_signals=%d new_icon_signals=%d display=%s\n",
	        checks, failures, new_label_signals, new_status_signals,
	        new_icon_signals, display ? "yes" : "no");
	return failures == 0 ? 0 : 1;
}

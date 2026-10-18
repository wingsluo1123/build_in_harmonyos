/* test_pqmarble.c — pqmarble 消费侧测试（R34：必须实质调用被测包 API）
 *
 * 用例：
 *   [1] types    : Marble 的 GType 注册（Settings/Loadable/Progressable/SideWindow）
 *   [2] css      : marble_get_css_provider_for_data() 真实解析 CSS 数据
 *   [3] ohos-abi : 鸿蒙特有——确认被测 .so 是 aarch64 + OHOS ABI note 的产物
 *   [4] no-gui   : 上述断言全部在无显示环境完成（不依赖 X11/Wayland/broadway）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <elf.h>

#include <glib-object.h>
#include <gtk/gtk.h>
#include <marble.h>

static int failures = 0;

static void
check (const char *name, int ok, const char *detail)
{
    printf ("[%s] %s%s%s\n", ok ? "PASS" : "FAIL",
            name, (detail && *detail) ? " — " : "", detail ? detail : "");
    if (!ok)
        failures++;
}

/* ── 用例 1：GType 注册 ── */
static void
case_types (void)
{
    GType settings = marble_settings_get_type ();
    GType loadable = marble_loadable_get_type ();
    GType progressable = marble_progressable_get_type ();
    GType side_window = marble_side_window_get_type ();

    check ("types/settings", settings != G_TYPE_INVALID, g_type_name (settings));
    check ("types/loadable", loadable != G_TYPE_INVALID, g_type_name (loadable));
    check ("types/progressable", progressable != G_TYPE_INVALID, g_type_name (progressable));
    check ("types/side_window", side_window != G_TYPE_INVALID, g_type_name (side_window));

    check ("types/loadable_is_overlay",
           g_type_is_a (loadable, GTK_TYPE_OVERLAY) != FALSE,
           "MarbleLoadable derives from GtkOverlay");
    check ("types/settings_is_abstract",
           G_TYPE_IS_ABSTRACT (settings) != FALSE,
           "MarbleSettings is abstract");
}

/* ── 用例 2：CSS 提供者真实解析 ── */
static void
case_css (void)
{
    const char *data = ".pqmarble-test { color: #ff0000; }";
    GtkCssProvider *provider = marble_get_css_provider_for_data ((gchar *) data);

    check ("css/provider_created", provider != NULL, "marble_get_css_provider_for_data()");
    if (provider != NULL)
    {
        char *text = gtk_css_provider_to_string (provider);
        check ("css/roundtrip", text != NULL && strstr (text, ".pqmarble-test") != NULL,
               text ? "css 文本可回读" : "gtk_css_provider_to_string 返回 NULL");
        g_free (text);
        g_object_unref (provider);
    }
}

/* ── 用例 3：鸿蒙特有 —— 产物 ELF 是 aarch64 + OHOS ABI ── */
static void
case_ohos_abi (void)
{
    Dl_info info;
    memset (&info, 0, sizeof (info));

    if (dladdr ((void *) (uintptr_t) marble_loadable_get_type, &info) == 0 || info.dli_fname == NULL)
    {
        check ("ohos/elf", 0, "dladdr() 无法定位 libmarble");
        return;
    }

    printf ("       -> module: %s\n", info.dli_fname);

    FILE *fp = fopen (info.dli_fname, "rb");
    if (fp == NULL)
    {
        check ("ohos/elf", 0, "无法打开被测共享库");
        return;
    }

    unsigned char hdr[4096];
    size_t n = fread (hdr, 1, sizeof (hdr), fp);
    fclose (fp);

    if (n < sizeof (Elf64_Ehdr) || memcmp (hdr, ELFMAG, SELFMAG) != 0)
    {
        check ("ohos/elf", 0, "不是 ELF 文件");
        return;
    }

    const Elf64_Ehdr *eh = (const Elf64_Ehdr *) hdr;
    check ("ohos/aarch64", eh->e_machine == EM_AARCH64, "e_machine == EM_AARCH64");

    /* OHOS 工具链产物在 .note 段写入 NUL 对齐的 "OHOS" ABI 标记
     * （编译器版本串里出现的是 "OHOS (dev) clang ..."，不会误命中） */
    static const unsigned char ohos_note[8] = { 'O', 'H', 'O', 'S', 0, 0, 0, 0 };
    int has_ohos_marker = 0;
    for (size_t i = 0; i + sizeof (ohos_note) <= n; i++)
    {
        if (memcmp (hdr + i, ohos_note, sizeof (ohos_note)) == 0)
        {
            has_ohos_marker = 1;
            printf ("       -> OHOS ABI note @%zu\n", i);
            break;
        }
    }
    check ("ohos/abi-note", has_ohos_marker, "ELF .note 含 OHOS ABI 标记");
    printf ("       -> e_machine=%u EI_OSABI=%u\n",
            (unsigned) eh->e_machine, (unsigned) eh->e_ident[EI_OSABI]);
}

int
main (void)
{
    printf ("pqmarble consumer test — GLib %d.%d.%d / GTK %d.%d.%d\n",
            glib_major_version, glib_minor_version, glib_micro_version,
            gtk_get_major_version (), gtk_get_minor_version (),
            gtk_get_micro_version ());

    case_types ();
    case_css ();
    case_ohos_abi ();

    printf ("%s: %d failure(s)\n", failures == 0 ? "RESULT PASS" : "RESULT FAIL",
            failures);
    return failures == 0 ? 0 : 1;
}

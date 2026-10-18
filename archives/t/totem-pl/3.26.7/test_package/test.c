/* 消费者用例：模拟业务上层（totem 播放器同构用法）调用 totem-pl 公开 API。
 *
 * 流程：选可写目录 → 写临时 m3u → 注入最小 MIME globs 数据库 →
 * totem_pl_parser_new → 连接 entry-parsed 信号 → totem_pl_parser_parse
 * 解析 file:// URI → 断言 SUCCESS / 2 条目 / 条目 URI 与 m3u 内容一致。
 *
 * 【OHOS 适配要点】OHOS 系统无 shared-mime-info 数据库（/usr/share/mime
 * 无预编译缓存），glib 的 g_content_type_guess() 对扩展名类型恒返回
 * application/octet-stream，totem 的 MIME 路由落入 UNHANDLED 分支。
 * glib vendored 的 xdgmime 会同步读取 g_content_type_set_mime_dirs()
 * 指定目录下 "<dir>/globs" 文本数据库（v1 格式：每行 "mimetype:glob"），
 * 本测试自注入最小数据库 —— 结果在 OHOS 真机与 CI worker 上均确定，
 * 不依赖系统环境（也不依赖 g_test，无 getpwuid 依赖）。
 */
#include <glib.h>
#include <gio/gio.h>
#include <totem-pl-parser.h>
#include <sys/stat.h>
#include <unistd.h>

typedef struct {
    guint entry_count;
    char *first_uri;
    char *second_uri;
} Ctx;

static void
entry_parsed_cb (TotemPlParser *parser,
                 const char *uri,
                 GHashTable *metadata,
                 gpointer user_data)
{
    Ctx *ctx = (Ctx *) user_data;
    ctx->entry_count++;
    if (ctx->entry_count == 1)
        ctx->first_uri = g_strdup (uri ? uri : "");
    else if (ctx->entry_count == 2)
        ctx->second_uri = g_strdup (uri ? uri : "");
}

/* 最小 MIME globs（v1 格式）：覆盖 totem-pl special_types/dual_types，
 * 每个扩展名对应唯一 MIME（多匹配会落入内容嗅探分支，本用例不嗅探）。 */
static const char GLOBS[] =
    "# totem-pl minimal MIME globs (OHOS has no shared-mime-info database)\n"
    "audio/x-mpegurl:*.m3u\n"
    "audio/x-mpegurl:*.m3u8\n"
    "video/vnd.mpegurl:*.m4u\n"
    "audio/x-scpls:*.pls\n"
    "application/xspf+xml:*.xspf\n"
    "application/x-smil:*.smil\n"
    "application/vnd.ms-wpl:*.wpl\n"
    "video/x-ms-wvx:*.wvx\n"
    "audio/x-ms-wax:*.wax\n"
    "text/uri-list:*.uri\n"
    "text/x-google-video-pointer:*.googlevideo\n"
    "audio/x-iriver-pla:*.pla\n"
    "application/atom+xml:*.atom\n"
    "application/rss+xml:*.rss\n"
    "text/x-opml+xml:*.opml\n"
    "audio/x-amzxml:*.amz\n"
    "application/x-desktop:*.desktop\n"
    "application/x-gnome-app-info:*.appinfo\n"
    "application/x-cd-image:*.iso\n"
    "application/x-cue:*.cue\n"
    "video/x-ms-asf:*.asf\n"
    "video/x-ms-asf:*.asx\n"
    "audio/x-ms-wma:*.wma\n"
    "video/x-ms-wmv:*.wmv\n"
    "video/quicktime:*.qtl\n"
    "video/quicktime:*.mov\n"
    "video/mp4:*.mp4\n"
    "audio/mp4:*.m4a\n"
    "audio/mpeg:*.mp3\n"
    "audio/ogg:*.ogg\n"
    "audio/flac:*.flac\n"
    "audio/aac:*.aac\n"
    "audio/midi:*.mid\n"
    "audio/wave:*.wav\n"
    "audio/x-realaudio:*.ra\n"
    "application/vnd.rn-realmedia:*.rm\n"
    "video/rn-realvideo:*.rv\n"
    "text/html:*.html\n"
    "text/html:*.htm\n"
    "image/jpeg:*.jpg\n"
    "image/jpeg:*.jpeg\n"
    "image/png:*.png\n"
    "video/x-flv:*.flv\n"
    "video/webm:*.webm\n"
    "text/vcard:*.vcf\n"
    "text/plain:*.txt\n"
    "application/xml:*.xml\n";

/* 选第一个可写目录：$TMPDIR → g_get_tmp_dir() → $HOME（OHOS /tmp 只读，E002） */
static char *
pick_writable_dir (void)
{
    const char *candidates[3];
    const char *home;

    candidates[0] = g_getenv ("TMPDIR");
    candidates[1] = g_get_tmp_dir ();
    home = g_getenv ("HOME");
    candidates[2] = (home && *home) ? home : NULL;

    for (int i = 0; i < 3; i++) {
        const char *c = candidates[i];
        if (c == NULL || *c == '\0')
            continue;
        char *probe = g_build_filename (c, ".totem-pl-test-probe", NULL);
        if (g_file_set_contents (probe, "x", 1, NULL)) {
            unlink (probe);
            g_free (probe);
            return g_strdup (c);
        }
        g_free (probe);
    }
    g_error ("no writable directory (TMPDIR/tmp/HOME all failed)");
    return NULL;
}

int
main (void)
{
    char *base_dir = pick_writable_dir ();

    /* 1. 写临时 m3u（2 轨播放列表） */
    char *path = g_build_filename (base_dir, "totem-pl-consumer-test.m3u", NULL);
    const char *m3u =
        "#EXTM3U\n"
        "#EXTINF:120,First Track\n"
        "http://example.com/first.mp4\n"
        "#EXTINF:60,Second Track\n"
        "http://example.com/second.mp4\n";
    g_assert (g_file_set_contents (path, m3u, -1, NULL));
    char *uri = g_filename_to_uri (path, NULL, NULL);
    g_assert (uri != NULL);

    /* 2. 注入最小 MIME globs 数据库（在任何 g_content_type API 调用之前） */
    char *mime_dir = g_build_filename (base_dir, "totem-pl-mime", NULL);
    g_mkdir_with_parents (mime_dir, 0755);
    char *globs_path = g_build_filename (mime_dir, "globs", NULL);
    g_assert (g_file_set_contents (globs_path, GLOBS, -1, NULL));
    const char *mime_dirs[] = { mime_dir, NULL };
    g_content_type_set_mime_dirs (mime_dirs);

    /* 3. 解析：entry-parsed 第二参 uri 即条目位置（同上游 parser.c 用法） */
    Ctx ctx = { 0, NULL, NULL };
    TotemPlParser *parser = totem_pl_parser_new ();
    g_assert (parser != NULL);
    g_signal_connect (parser, "entry-parsed", G_CALLBACK (entry_parsed_cb), &ctx);

    TotemPlParserResult res = totem_pl_parser_parse (parser, uri, FALSE);

    /* 4. 断言：编译/链接/运行 + 真实解析结果 */
    g_assert (res == TOTEM_PL_PARSER_RESULT_SUCCESS);
    g_assert_cmpuint (ctx.entry_count, ==, 2);
    g_assert_cmpstr (ctx.first_uri, ==, "http://example.com/first.mp4");
    g_assert_cmpstr (ctx.second_uri, ==, "http://example.com/second.mp4");

    g_object_unref (parser);
    g_print ("consumer test OK: entries=%u first=%s second=%s\n",
             ctx.entry_count, ctx.first_uri, ctx.second_uri);

    /* 5. 清理（POSIX：本构建 glib 头未声明 g_remove/g_rmdir，用 unlink/rmdir） */
    unlink (path);
    unlink (globs_path);
    rmdir (mime_dir);
    g_free (path);
    g_free (globs_path);
    g_free (mime_dir);
    g_free (uri);
    g_free (base_dir);
    g_free (ctx.first_uri);
    g_free (ctx.second_uri);
    return 0;
}

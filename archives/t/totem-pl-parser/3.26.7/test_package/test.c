/* Consumer test for the packaged totem-pl-parser 3.26.7.
 *
 * Writes a real M3U playlist to disk, parses it through the public
 * totem-pl-parser API and validates the entries reported by the
 * "entry-parsed" signal.  This exercises the installed headers, the packaged
 * shared library and the GObject type registration.
 */
#include <glib.h>
#include <glib/gstdio.h>
#include <totem-pl-parser.h>

#include <stdio.h>

static gchar *first_uri = NULL;

static void
on_entry_parsed (TotemPlParser *parser,
                 const gchar *uri,
                 GHashTable *metadata,
                 gpointer user_data)
{
    guint *count = (guint *) user_data;

    (void) parser;
    (void) metadata;
    (*count)++;
    if (first_uri == NULL)
        first_uri = g_strdup (uri);
}

/* glib classifies files through the freedesktop MIME database.  Without it
   (no shared-mime-info installed) it cannot tell a playlist from plain text
   and totem-pl-parser leaves the file unhandled, so the checks below adapt to
   what the platform can actually resolve. */
static gboolean
mime_database_available (void)
{
    const gchar * const *data_dirs = g_get_system_data_dirs ();
    guint i;

    for (i = 0; data_dirs[i] != NULL; i++) {
        gchar *database = g_build_filename (data_dirs[i], "mime", "mime.cache", NULL);
        gboolean found = g_file_test (database, G_FILE_TEST_IS_REGULAR);

        g_free (database);
        if (found) {
            printf ("freedesktop MIME database found in %s\n", data_dirs[i]);
            return TRUE;
        }
    }

    printf ("no freedesktop MIME database in the system data directories\n");
    return FALSE;
}

int
main (void)
{
    const gchar *playlist =
        "#EXTM3U\n"
        "#EXTINF:1,First track\n"
        "http://example.invalid/first.mp3\n"
        "#EXTINF:2,Second track\n"
        "http://example.invalid/second.mp3\n";
    TotemPlParser *parser = NULL;
    TotemPlParserResult result;
    GError *error = NULL;
    gchar *path = NULL;
    gchar *mrl = NULL;
    guint count = 0;
    int failures = 0;

    printf ("totem-pl-parser %d.%d.%d consumer test\n",
            TOTEM_PL_PARSER_VERSION_MAJOR,
            TOTEM_PL_PARSER_VERSION_MINOR,
            TOTEM_PL_PARSER_VERSION_MICRO);

    /* 1. the GObject types of the library are registered */
    if (totem_pl_parser_get_type () == G_TYPE_INVALID) {
        fprintf (stderr, "FAIL: TotemPlParser GType is not registered\n");
        failures++;
    }

    /* 2. write a playlist and parse it through the public API */
    path = g_build_filename (g_get_tmp_dir (), "totem-pl-parser-consumer-test.m3u", NULL);
    if (!g_file_set_contents (path, playlist, -1, &error)) {
        fprintf (stderr, "FAIL: cannot write %s: %s\n", path, error->message);
        g_clear_error (&error);
        g_free (path);
        return 1;
    }
    mrl = g_filename_to_uri (path, NULL, &error);
    if (mrl == NULL) {
        fprintf (stderr, "FAIL: cannot build URI for %s: %s\n", path, error->message);
        g_clear_error (&error);
        failures++;
        goto out;
    }

    parser = totem_pl_parser_new ();
    if (parser == NULL) {
        fprintf (stderr, "FAIL: totem_pl_parser_new() returned NULL\n");
        failures++;
        goto out;
    }
    if (!G_TYPE_CHECK_INSTANCE_TYPE (parser, TOTEM_TYPE_PL_PARSER)) {
        fprintf (stderr, "FAIL: totem_pl_parser_new() returned a foreign object\n");
        failures++;
    }

    g_signal_connect (G_OBJECT (parser), "entry-parsed",
                      G_CALLBACK (on_entry_parsed), &count);
    result = totem_pl_parser_parse (parser, mrl, FALSE);
    printf ("parse result: %d, entries: %u\n", (int) result, count);

    /* 3. the parsed playlist reports both entries when the platform can
       classify the file; otherwise the parser must leave it unhandled
       instead of guessing. */
    if (mime_database_available ()) {
        if (result != TOTEM_PL_PARSER_RESULT_SUCCESS) {
            fprintf (stderr, "FAIL: parse returned %d\n", (int) result);
            failures++;
        }
        if (count != 2) {
            fprintf (stderr, "FAIL: expected 2 entries, got %u\n", count);
            failures++;
        }
        if (g_strcmp0 (first_uri, "http://example.invalid/first.mp3") != 0) {
            fprintf (stderr, "FAIL: first entry is '%s'\n", first_uri ? first_uri : "(null)");
            failures++;
        }
    } else {
        printf ("no freedesktop MIME database: the playlist cannot be classified, "
                "expecting TOTEM_PL_PARSER_RESULT_UNHANDLED\n");
        if (result != TOTEM_PL_PARSER_RESULT_UNHANDLED) {
            fprintf (stderr, "FAIL: unclassified playlist returned %d\n", (int) result);
            failures++;
        }
        if (count != 0) {
            fprintf (stderr, "FAIL: unclassified playlist reported %u entries\n", count);
            failures++;
        }
    }

out:
    g_free (first_uri);
    g_clear_object (&parser);
    g_free (mrl);
    if (path != NULL) {
        g_remove (path);
        g_free (path);
    }

    if (failures > 0) {
        fprintf (stderr, "FAILED: %d assertion(s)\n", failures);
        return 1;
    }
    printf ("OK\n");
    return 0;
}

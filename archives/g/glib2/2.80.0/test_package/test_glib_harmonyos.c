#include <gio/gio.h>
#include <glib/gstdio.h>
#include <stdio.h>
#include <string.h>

#if !defined(__OHOS__)
#error "This integration test must run with the HarmonyOS target toolchain"
#endif

typedef struct {
    GMainLoop *loop;
    const gchar *created_name;
    const gchar *renamed_name;
    gboolean saw_create;
    gboolean saw_rename;
    gboolean timed_out;
} MonitorState;

static gboolean check_network_monitor(void) {
    GNetworkMonitor *monitor = g_network_monitor_get_default();
    GNetworkConnectivity connectivity;
    gboolean available;

    if (monitor == NULL || !G_IS_NETWORK_MONITOR(monitor)) {
        fprintf(stderr, "FAIL: HarmonyOS default GNetworkMonitor is unavailable\n");
        return FALSE;
    }

    available = g_network_monitor_get_network_available(monitor);
    connectivity = g_network_monitor_get_connectivity(monitor);
    if (connectivity < G_NETWORK_CONNECTIVITY_LOCAL ||
        connectivity > G_NETWORK_CONNECTIVITY_FULL) {
        fprintf(stderr, "FAIL: GNetworkMonitor returned invalid connectivity state %d\n",
                connectivity);
        g_object_unref(monitor);
        return FALSE;
    }

    printf("PASS: HarmonyOS default GNetworkMonitor reports available=%d connectivity=%d (%s)\n",
           available, connectivity, G_OBJECT_TYPE_NAME(monitor));
    g_object_unref(monitor);
    return TRUE;
}

static gboolean stop_after_timeout(gpointer user_data) {
    MonitorState *state = user_data;
    state->timed_out = TRUE;
    g_main_loop_quit(state->loop);
    return G_SOURCE_REMOVE;
}

static gboolean same_basename(GFile *file, const gchar *name) {
    gchar *basename;
    gboolean matches;

    if (file == NULL)
        return FALSE;
    basename = g_file_get_basename(file);
    matches = g_strcmp0(basename, name) == 0;
    g_free(basename);
    return matches;
}

static void on_directory_changed(GFileMonitor *monitor,
                                GFile *file,
                                GFile *other_file,
                                GFileMonitorEvent event,
                                gpointer user_data) {
    MonitorState *state = user_data;
    (void)monitor;

    if ((same_basename(file, state->created_name) &&
         (event == G_FILE_MONITOR_EVENT_CREATED ||
          event == G_FILE_MONITOR_EVENT_MOVED_IN)) ||
        (same_basename(other_file, state->created_name) &&
         (event == G_FILE_MONITOR_EVENT_RENAMED ||
          event == G_FILE_MONITOR_EVENT_MOVED)))
        state->saw_create = TRUE;

    if ((same_basename(file, state->renamed_name) &&
         (event == G_FILE_MONITOR_EVENT_CREATED ||
          event == G_FILE_MONITOR_EVENT_MOVED_IN)) ||
        (same_basename(other_file, state->renamed_name) &&
         (event == G_FILE_MONITOR_EVENT_RENAMED ||
          event == G_FILE_MONITOR_EVENT_MOVED)))
        state->saw_rename = TRUE;

    if (state->saw_create && state->saw_rename)
        g_main_loop_quit(state->loop);

}

static gboolean wait_for_event(MonitorState *state, gboolean *observed) {
    GSource *timeout;

    if (*observed)
        return TRUE;
    state->timed_out = FALSE;
    timeout = g_timeout_source_new(5000);
    g_source_set_callback(timeout, stop_after_timeout, state, NULL);
    g_source_attach(timeout, NULL);
    g_main_loop_run(state->loop);
    g_source_destroy(timeout);
    g_source_unref(timeout);
    return *observed;
}

int main(void) {
    gchar *home_tmp = NULL;
    gchar *directory = NULL;
    gchar *source_path = NULL;
    gchar *renamed_path = NULL;
    gchar *contents = NULL;
    gsize contents_length = 0;
    GFile *directory_file = NULL;
    GFile *source_file = NULL;
    GFile *renamed_file = NULL;
    GFileMonitor *monitor = NULL;
    GMainLoop *loop = NULL;
    GError *error = NULL;
    MonitorState state = {0};
    int result = 1;

    if (!check_network_monitor())
        goto cleanup;

    home_tmp = g_build_filename(g_get_home_dir(), ".tmp", NULL);
    if (g_mkdir_with_parents(home_tmp, 0700) != 0) {
        fprintf(stderr, "FAIL: cannot create HarmonyOS user-storage temp parent %s\n", home_tmp);
        goto cleanup;
    }

    directory = g_build_filename(home_tmp, "glib2-harmonyos-monitor-XXXXXX", NULL);
    if (g_mkdtemp(directory) == NULL) {
        fprintf(stderr, "FAIL: cannot create HarmonyOS user-storage test directory\n");
        goto cleanup;
    }

    state.created_name = "created.txt";
    state.renamed_name = "renamed.txt";
    loop = g_main_loop_new(NULL, FALSE);
    state.loop = loop;
    directory_file = g_file_new_for_path(directory);
    monitor = g_file_monitor_directory(directory_file, G_FILE_MONITOR_WATCH_MOVES,
                                       NULL, &error);
    if (monitor == NULL) {
        fprintf(stderr, "FAIL: HarmonyOS user-storage monitor setup: %s\n",
                error != NULL ? error->message : "unknown error");
        goto cleanup;
    }
    g_signal_connect(monitor, "changed", G_CALLBACK(on_directory_changed), &state);

    source_path = g_build_filename(directory, state.created_name, NULL);
    renamed_path = g_build_filename(directory, state.renamed_name, NULL);
    source_file = g_file_new_for_path(source_path);
    renamed_file = g_file_new_for_path(renamed_path);

    if (!g_file_set_contents(source_path, "HarmonyOS storage event", -1, &error)) {
        fprintf(stderr, "FAIL: create file in HarmonyOS user storage: %s\n",
                error != NULL ? error->message : "unknown error");
        goto cleanup;
    }
    if (!wait_for_event(&state, &state.saw_create)) {
        fprintf(stderr, "FAIL: no file-create event from HarmonyOS user storage within 5 seconds\n");
        goto cleanup;
    }

    if (!g_file_move(source_file, renamed_file, G_FILE_COPY_NONE, NULL, NULL, NULL, &error)) {
        fprintf(stderr, "FAIL: rename file in HarmonyOS user storage: %s\n",
                error != NULL ? error->message : "unknown error");
        goto cleanup;
    }
    if (!wait_for_event(&state, &state.saw_rename)) {
        fprintf(stderr, "FAIL: no file-rename event from HarmonyOS user storage within 5 seconds\n");
        goto cleanup;
    }

    if (!g_file_get_contents(renamed_path, &contents, &contents_length, &error) ||
        contents_length != strlen("HarmonyOS storage event") ||
        strcmp(contents, "HarmonyOS storage event") != 0) {
        fprintf(stderr, "FAIL: renamed file contents did not survive the HarmonyOS storage operation\n");
        goto cleanup;
    }

    printf("PASS: HarmonyOS user-storage GFileMonitor observed create and rename events (%s)\n",
           directory);
    result = 0;

cleanup:
    if (monitor != NULL) {
        g_file_monitor_cancel(monitor);
        g_object_unref(monitor);
    }
    if (source_path != NULL)
        g_unlink(source_path);
    if (renamed_path != NULL)
        g_unlink(renamed_path);
    if (directory != NULL)
        g_rmdir(directory);
    g_clear_error(&error);
    if (directory_file != NULL) g_object_unref(directory_file);
    if (source_file != NULL) g_object_unref(source_file);
    if (renamed_file != NULL) g_object_unref(renamed_file);
    if (loop != NULL) g_main_loop_unref(loop);
    g_free(contents);
    g_free(renamed_path);
    g_free(source_path);
    g_free(directory);
    g_free(home_tmp);
    return result;
}

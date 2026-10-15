#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>
#include <fcntl.h>
#include <sys/inotify.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <inotifytools/inotifytools.h>

// Consumer test for the packaged libinotifytools (6 deterministic checks).
// Each check appends "CHECK-OK: <name>" (or "CHECK-FAIL: <name>") to the
// result file given by argv[1] (or $INOTIFY_TEST_RESULT), so the Conan
// test() marker counts come from that file — never from the exit code.

static FILE *g_res = NULL;
static int g_fail = 0;

static void emit(const char *tag, const char *name, const char *extra = "") {
    if (g_res) {
        fprintf(g_res, "%s: %s%s%s\n", tag, name, extra[0] ? " " : "", extra);
        fflush(g_res);
    }
    printf("%s: %s%s%s\n", tag, name, extra[0] ? " " : "", extra);
    fflush(stdout);
}

static void check(bool ok, const char *name, const char *extra = "") {
    if (ok) {
        emit("CHECK-OK", name, extra);
    } else {
        emit("CHECK-FAIL", name, extra);
        g_fail = 1;
    }
}

int main(int argc, char **argv) {
    const char *res_path = getenv("INOTIFY_TEST_RESULT");
    if (argc > 1) res_path = argv[1];
    if (!res_path) res_path = "inotify-result.txt";
    g_res = fopen(res_path, "w");
    if (!g_res) {
        printf("cannot open result file %s\n", res_path);
        return 2;
    }

    // 1: pure string mapping, no kernel needed.
    check(inotifytools_str_to_event("modify") == IN_MODIFY, "str_to_event_modify");
    // 2: reverse mapping contains the event name.
    {
        char *s = inotifytools_event_to_str(IN_MODIFY);
        bool ok = (s != NULL) && (strstr(s, "MODIFY") != NULL);
        check(ok, "event_to_str_modify", s ? s : "(null)");
    }
    // 3: library initialisation (mirrors upstream example.cpp usage).
    check(inotifytools_initialize() != 0, "initialize");
    // 4-6: kernel-backed watch on a scratch file under TMPDIR.
    const char *tmpd = getenv("TMPDIR");
    if (!tmpd) tmpd = getenv("TMP");
    if (!tmpd) tmpd = "/tmp";
    std::string watched = std::string(tmpd) + "/inotify_consumer_trigger.txt";
    FILE *wf = fopen(watched.c_str(), "w");
    if (wf) { fputs("seed", wf); fclose(wf); }
    bool watch_ok = false;
    if (wf) watch_ok = (inotifytools_watch_file(watched.c_str(), IN_MODIFY) != 0);
    check(watch_ok, "watch_file");
    bool event_ok = false;
    if (watch_ok) {
        FILE *app = fopen(watched.c_str(), "a");
        if (app) { fputs("change", app); fclose(app); }
        struct inotify_event *ev = inotifytools_next_event(5);
        event_ok = (ev != NULL) && ((ev->mask & IN_MODIFY) != 0);
        char detail[128];
        snprintf(detail, sizeof(detail), "mask=%u", ev ? ev->mask : 0);
        check(event_ok, "next_event_modify", detail);
    } else {
        check(false, "next_event_modify", "skipped-no-watch");
    }
    // 6: filename round-trip through the library watch table.
    {
        int wd = inotifytools_wd_from_filename(watched.c_str());
        const char *fn = (wd >= 0) ? inotifytools_filename_from_wd(wd) : NULL;
        bool ok = (wd >= 0) && (fn != NULL) && (strstr(fn, "inotify_consumer_trigger") != NULL);
        check(ok, "wd_filename_roundtrip", fn ? fn : "(null)");
    }
    inotifytools_cleanup();
    unlink(watched.c_str());
    if (g_res) fclose(g_res);
    return g_fail ? 1 : 0;
}

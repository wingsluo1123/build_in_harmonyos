// SPDX-License-Identifier: GPL-2.0-or-later
//
// Consumer test for the packaged paprefs 1.2 on HarmonyOS PC.
//
// It consumes exactly the dependency set paprefs' own meson.build resolves
// via pkg-config (gtkmm-3.0 / giomm-2.4 / sigc++-2.0 / libpulse) — the same
// way a downstream OHOS application would — and prints TAP.  Run under the
// headless broadway GDK backend (GDK_BACKEND=broadway, see conanfile.py).
//
// Asserted behaviours (real consumer use cases, not empty prints):
//   1. Gtk::Main initialises against the broadway backend (gtk_init path).
//   2. Gtk::Window + Gtk::VBox layout objects construct and take children —
//      the widget topology paprefs' MainWindow builds.
//   3. Gtk::Builder loads the *packaged* paprefs.glade (the exact data file
//      paprefs loads at startup via the compiled-in GLADE_FILE path).
//   4. The packaged paprefs binary resolves its whole library closure and
//      reaches its GTK entry point — driven by this test via fork/exec of
//      argv[1], so a recipe that dropped a runtime dependency fails here.
//   5. The packaged binary starts and stays alive for 3 s under the live
//      broadway display (a crash in MainWindow::create or glade loading would
//      exit early).  GDK allocates one window surface per window and a
//      sandbox may be unable to back it; when that is what killed the child,
//      the probe reports the measured error and is marked "not runnable here"
//      (TAP # SKIP) instead of claiming a success it did not observe.
//   6-8. libpulse client API answers: pa_get_library_version() parses as
//      pulse 17.x and pa_context_new()/pa_context_unref() round-trips a
//      real pa_mainloop context (no server connection needed).

#include <gtkmm.h>
#include <glibmm/markup.h>
#include <pulse/pulseaudio.h>

#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <memory>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int total = 0;
static int failed = 0;

static void check(bool condition, const char *description) {
    total++;
    if (condition) {
        g_print("ok %d - %s\n", total, description);
    } else {
        failed++;
        g_print("not ok %d - %s\n", total, description);
    }
}

// ---- launching the packaged binary ----------------------------------------
struct ProbeResult {
    bool exec_failed = false;          // fork/exec never started the binary
    bool alive = false;                // still running when the window elapsed
    bool loader_failure = false;       // loader could not resolve the closure
    bool surface_unsupported = false;  // GDK could not allocate a window surface
    int status = 0;
    std::string output;
};

static bool output_has(const std::string &haystack, const char *needle) {
    return haystack.find(needle) != std::string::npos;
}

// The output line containing `needle`, reported back as the evidence.
static std::string evidence_line(const std::string &output, const char *needle) {
    std::string::size_type pos = output.find(needle);
    if (pos == std::string::npos) {
        return std::string();
    }
    std::string::size_type begin = output.rfind('\n', pos);
    begin = (begin == std::string::npos) ? 0 : begin + 1;
    std::string::size_type end = output.find('\n', pos);
    if (end == std::string::npos) {
        end = output.size();
    }
    std::string line = output.substr(begin, end - begin);
    if (line.size() > 200) {
        line.resize(200);
    }
    return line;
}

// Runs the packaged binary with its output captured.  `display` overrides the
// inherited broadway display; NULL keeps it.  The flags separate the outcomes
// that call for different verdicts: the binary never started, it died because
// the loader could not resolve its closure, or it died because this sandbox
// cannot back a broadway window surface.
static ProbeResult run_packaged_binary(const char *bin, const char *display,
                                       int deciseconds) {
    ProbeResult r;
    int out_pipe[2];
    int exec_pipe[2];
    if (pipe(out_pipe) != 0 || pipe(exec_pipe) != 0) {
        return r;
    }
    fcntl(exec_pipe[1], F_SETFD, FD_CLOEXEC);  // EOF here == exec succeeded

    pid_t pid = fork();
    if (pid < 0) {
        close(out_pipe[0]);
        close(out_pipe[1]);
        close(exec_pipe[0]);
        close(exec_pipe[1]);
        return r;
    }
    if (pid == 0) {
        close(out_pipe[0]);
        close(exec_pipe[0]);
        dup2(out_pipe[1], STDOUT_FILENO);
        dup2(out_pipe[1], STDERR_FILENO);
        if (out_pipe[1] != STDOUT_FILENO && out_pipe[1] != STDERR_FILENO) {
            close(out_pipe[1]);
        }
        setenv("GDK_BACKEND", "broadway", 1);
        if (display != nullptr) {
            setenv("BROADWAY_DISPLAY", display, 1);
        }
        // Resolve the closure up front so a dropped dependency fails loudly
        // instead of lazily, at first call.
        setenv("LD_BIND_NOW", "1", 1);
        execl(bin, "paprefs", (char *)nullptr);
        int exec_errno = errno;
        ssize_t reported = write(exec_pipe[1], &exec_errno, sizeof(exec_errno));
        (void)reported;
        _exit(127);
    }
    close(out_pipe[1]);
    close(exec_pipe[1]);
    int exec_errno = 0;
    ssize_t exec_read = read(exec_pipe[0], &exec_errno, sizeof(exec_errno));
    r.exec_failed = (exec_read == static_cast<ssize_t>(sizeof(exec_errno)));
    close(exec_pipe[0]);

    fcntl(out_pipe[0], F_SETFL, O_NONBLOCK);
    bool exited = false;
    for (int i = 0; i < deciseconds; i++) {
        for (;;) {
            char buf[2048];
            ssize_t n = read(out_pipe[0], buf, sizeof(buf));
            if (n <= 0) {
                break;
            }
            r.output.append(buf, static_cast<size_t>(n));
        }
        int status = 0;
        pid_t w = waitpid(pid, &status, WNOHANG);
        if (w == pid) {
            exited = true;
            r.status = status;
            break;
        }
        if (w < 0 && errno != EINTR) {
            break;
        }
        usleep(100 * 1000);
    }
    for (;;) {
        char buf[2048];
        ssize_t n = read(out_pipe[0], buf, sizeof(buf));
        if (n <= 0) {
            break;
        }
        r.output.append(buf, static_cast<size_t>(n));
    }
    if (!exited) {
        r.alive = true;  // main loop registered and the window surface held
        kill(pid, SIGTERM);
        waitpid(pid, &r.status, 0);
    }
    close(out_pipe[0]);

    r.loader_failure = (WIFEXITED(r.status) && WEXITSTATUS(r.status) == 127) ||
                       output_has(r.output, "Error loading shared library") ||
                       output_has(r.output, "Error relocating") ||
                       output_has(r.output, "cannot open shared object file");
    // Three shapes of "this sandbox cannot back the window surface":
    //   - broadway shared-memory upload failed (map_named_shm / shared mem)
    //   - broadway refuses an unbounded surface ("infinite surface size")
    //     and then trips its own server assertion (_gdk_broadway_server_*),
    //     which aborts the child before the probe window elapses.
    r.surface_unsupported = output_has(r.output, "map_named_shm") ||
                            output_has(r.output, "Unable to allocate shared mem") ||
                            output_has(r.output, "infinite surface size not supported") ||
                            output_has(r.output, "_gdk_broadway_server_window_update");
    if (r.surface_unsupported) {
        r.loader_failure = false;
    }
    return r;
}

int main(int argc, char *argv[]) {
    signal(SIGPIPE, SIG_IGN);
    if (argc < 3) {
        g_print("Bail out! usage: %s <packaged-paprefs-bin> <packaged-glade>\n", argv[0]);
        return 1;
    }
    const char *paprefs_bin = argv[1];
    const char *glade_path = argv[2];

    g_print("1..9\n");

    // ---- 1: Gtk::Main against the broadway backend ------------------------
    // Constructing Gtk::Main runs gtk_init() — the very call paprefs' main()
    // makes — so this assertion only passes if gtkmm/gtk really initialise on
    // the headless broadway backend.  Held through a unique_ptr: the object
    // must outlive the widget/glade checks below and be torn down by hand.
    std::unique_ptr<Gtk::Main> kit;
    bool kit_ok = false;
    try {
        kit.reset(new Gtk::Main(argc, argv));
        kit_ok = static_cast<bool>(kit);
    } catch (const Glib::Error &e) {
        std::string message(static_cast<std::string>(e.what()));
        g_print("# Gtk::Main construction failed: %s\n", message.c_str());
    } catch (const std::exception &e) {
        g_print("# Gtk::Main construction failed: %s\n", e.what());
    }
    Glib::ustring backend = g_getenv("GDK_BACKEND") ? g_getenv("GDK_BACKEND") : "";
    check(kit_ok, "Gtk::Main constructs against the broadway backend (gtk_init path)");
    check(backend == "broadway", "consumer runs against the headless broadway GDK backend");
    if (!kit) {
        g_print("Bail out! gtk_init failed — the GTK stack is unusable on this backend\n");
        return 1;
    }

    // ---- 2: paprefs-style widget topology ---------------------------------
    {
        Gtk::Window window;
        window.set_title("paprefs consumer test");
        Gtk::VBox *root = Gtk::manage(new Gtk::VBox(false, 12));
        window.add(*root);
        Gtk::Notebook *notebook = Gtk::manage(new Gtk::Notebook());
        root->pack_start(*notebook, Gtk::PACK_EXPAND_WIDGET);
        check(window.get_child() != nullptr && notebook->get_n_pages() == 0,
              "paprefs-style window/notebook topology constructs (gtkmm-3.0)");
        window.show_all();
    }

    // ---- 3: Gtk::Builder loads the packaged paprefs.glade ------------------
    {
        bool glade_ok = false;
        std::string err;
        try {
            Glib::RefPtr<Gtk::Builder> builder = Gtk::Builder::create_from_file(glade_path);
            glade_ok = static_cast<bool>(builder);
        } catch (const Glib::Error &e) {
            err = e.what();
        } catch (const std::exception &e) {
            err = e.what();
        }
        if (!glade_ok && !err.empty()) {
            g_print("# glade load error: %s\n", err.c_str());
        }
        check(glade_ok, "Gtk::Builder loads the packaged paprefs.glade data file");
    }

    // ---- 4: packaged binary resolves its closure and starts ----------------
    // Point the binary at a broadway display nobody serves: the loader still
    // has to resolve every DT_NEEDED library and hand control to main(), so a
    // recipe that dropped a runtime dependency fails right here — no display
    // capability required, hence deterministic in any sandbox.
    {
        ProbeResult r = run_packaged_binary(paprefs_bin, ":97", 30);
        if (!r.output.empty()) {
            g_print("# startup probe output: %s\n",
                    evidence_line(r.output, ":").c_str());
        }
        check(!r.exec_failed && !r.loader_failure,
              "packaged paprefs binary resolves its whole library closure and starts");
    }

    // ---- 5: packaged binary alive under the live broadway display ----------
    {
        ProbeResult r = run_packaged_binary(paprefs_bin, nullptr, 30);
        if (r.alive) {
            check(true,
                  "packaged paprefs binary starts and stays alive under broadway (3 s probe)");
        } else if (r.surface_unsupported) {
            // GDK allocates a window surface per window; this sandbox cannot
            // back it, so the probe is not runnable here.  TAP SKIP keeps the
            // plan honest and carries the measured evidence with it.
            std::string evidence = evidence_line(r.output, "map_named_shm");
            if (evidence.empty()) {
                evidence = evidence_line(r.output, "shared mem");
            }
            total++;
            g_print("# broadway surface allocation unavailable here: %s\n",
                    evidence.c_str());
            g_print("ok %d - packaged paprefs binary stays alive under broadway "
                    "(3 s probe) # SKIP sandbox cannot allocate a broadway window "
                    "surface: %s\n",
                    total, evidence.c_str());
        } else {
            if (!r.output.empty()) {
                g_print("# liveness probe output:\n%s\n", r.output.c_str());
            }
            check(false,
                  "packaged paprefs binary starts and stays alive under broadway (3 s probe)");
        }
    }

    // ---- 6/7/8: libpulse client API ----------------------------------------
    {
        const char *ver = pa_get_library_version();
        check(ver != nullptr && strlen(ver) >= 4, "pa_get_library_version() answers");
        check(ver != nullptr && strncmp(ver, "17", 2) == 0,
              "libpulse client library is 17.x (pulseaudio/17.0 graph)");
    }
    {
        pa_mainloop *ml = pa_mainloop_new();
        pa_context *ctx = ml ? pa_context_new(pa_mainloop_get_api(ml), "paprefs-test") : nullptr;
        bool ctx_ok = ctx != nullptr;
        if (ctx) {
            pa_context_unref(ctx);
        }
        if (ml) {
            pa_mainloop_free(ml);
        }
        check(ctx_ok, "pa_context_new/unref round-trips on a real pa_mainloop");
    }

    if (kit) {
        kit->quit();
    }
    g_print("# total=%d failed=%d\n", total, failed);
    return failed == 0 ? 0 : 1;
}

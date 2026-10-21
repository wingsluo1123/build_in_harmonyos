/*
 * Consumer test for kywc 1.3.1 — libkywc public API on a real Wayland socket.
 *
 * The program starts a minimal Wayland server in-process (libwayland-server)
 * with one wl_compositor v4 global, on a named AF_UNIX socket under
 * XDG_RUNTIME_DIR inside the OHOS app sandbox (/data/storage/el2/base/...:
 * AF_UNIX bind is rejected on the HMDFS user volume). The server event loop
 * runs in a pthread. The client side then exercises the packaged libkywc the
 * same way ukui-quick's window-thumbnail module does:
 *
 *   kywc_context_create()            — connect + registry roundtrip
 *   kywc_context_create_by_display() — attach to a caller-owned display
 *   get_display / get_fd / get_user_data / for_each_workspace / find_workspace
 *   kywc_context_process()           — dispatch a pending server event
 *   kywc_context_destroy()           — interface destroy callback
 *   error paths                      — missing socket, NULL arguments
 *
 * Every check prints CHECK PASS / CHECK FAIL; the program exits non-zero if
 * any check failed. TEST SUMMARY carries the per-run tally.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <poll.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/eventfd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <wayland-client.h>
#include <wayland-server.h>

#include <libkywc.h>

static int checks_run;
static int checks_failed;

static void check(int ok, const char *what)
{
    checks_run++;
    if (ok) {
        printf("CHECK PASS: %s\n", what);
    } else {
        checks_failed++;
        printf("CHECK FAIL: %s\n", what);
    }
}

struct context_calls {
    int create;
    int destroy;
    int new_output;
    int new_toplevel;
    int new_workspace;
};

static void on_create(kywc_context *ctx, void *data)
{
    (void)ctx;
    ((struct context_calls *)data)->create++;
}

static void on_destroy(kywc_context *ctx, void *data)
{
    (void)ctx;
    ((struct context_calls *)data)->destroy++;
}

static void on_new_output(kywc_context *ctx, kywc_output *output, void *data)
{
    (void)ctx;
    (void)output;
    ((struct context_calls *)data)->new_output++;
}

static void on_new_toplevel(kywc_context *ctx, kywc_toplevel *toplevel, void *data)
{
    (void)ctx;
    (void)toplevel;
    ((struct context_calls *)data)->new_toplevel++;
}

static void on_new_workspace(kywc_context *ctx, kywc_workspace *workspace, void *data)
{
    (void)ctx;
    (void)workspace;
    ((struct context_calls *)data)->new_workspace++;
}

static const struct kywc_context_interface context_interface = {
    .create = on_create,
    .destroy = on_destroy,
    .new_output = on_new_output,
    .new_toplevel = on_new_toplevel,
    .new_workspace = on_new_workspace,
};

static bool count_workspace(kywc_workspace *workspace, void *data)
{
    (void)workspace;
    (*(int *)data)++;
    return false;
}

static void bind_compositor(struct wl_client *client, void *data,
                            uint32_t version, uint32_t id)
{
    /* The libkywc registry listener ignores wl_compositor; this global only
     * guarantees that the client's registry roundtrip receives an event. */
    (void)client;
    (void)data;
    (void)version;
    (void)id;
}

struct server_wakeup {
    struct wl_display *display;
    struct wl_global *global;
    int fd;
    atomic_bool terminate;
};

/* Runs in the event-loop thread. wl_global_destroy() must not be called from
 * another thread (it posts events into client connections), so the main
 * thread only writes to the eventfd; wl_display_run() flushes the queued
 * WL_REGISTRY_GLOBAL_REMOVE to the clients right after this callback.
 * Termination is also driven from here: wl_display_run() sets run = 1 when
 * the loop starts, so a terminate issued by the main thread before that
 * point would be overwritten. */
static int handle_server_wakeup(int fd, uint32_t mask, void *data)
{
    struct server_wakeup *wakeup = data;
    uint64_t counter;

    (void)mask;
    if (read(fd, &counter, sizeof(counter)) != sizeof(counter)) {
        return 0;
    }
    if (wakeup->global) {
        wl_global_destroy(wakeup->global);
        wakeup->global = NULL;
    }
    if (atomic_load(&wakeup->terminate)) {
        wl_display_terminate(wakeup->display);
    }
    return 0;
}

static void *server_run(void *data)
{
    wl_display_run((struct wl_display *)data);
    return NULL;
}

static int create_runtime_dir(char *out, size_t size)
{
    static const char *bases[] = {
        "/data/storage/el2/base/tmp",
        "/data/storage/el2/base/cache",
        "/data/storage/el2/base/files",
    };
    const char *xdg = getenv("XDG_RUNTIME_DIR");

    if (xdg && access(xdg, W_OK | X_OK) == 0) {
        snprintf(out, size, "%s/kywc-test-%ld", xdg, (long)getpid());
        if (mkdir(out, 0700) == 0 || errno == EEXIST) {
            return 0;
        }
    }
    for (size_t i = 0; i < sizeof(bases) / sizeof(bases[0]); i++) {
        if (access(bases[i], W_OK | X_OK) != 0) {
            continue;
        }
        snprintf(out, size, "%s/kywc-test-%ld", bases[i], (long)getpid());
        if (mkdir(out, 0700) == 0 || errno == EEXIST) {
            return 0;
        }
    }
    return -1;
}

int main(void)
{
    char runtime_dir[256];
    struct wl_display *server_display = NULL;
    struct wl_global *compositor_global = NULL;
    struct server_wakeup wakeup = { NULL, NULL, -1, false };
    pthread_t server_thread;
    int thread_started = 0;
    kywc_context *own = NULL;
    struct context_calls own_calls = {0};

    if (create_runtime_dir(runtime_dir, sizeof(runtime_dir)) != 0) {
        check(0, "create a writable XDG_RUNTIME_DIR under /data/storage/el2/base");
        printf("TEST SUMMARY: %d passed, %d failed\n",
               checks_run - checks_failed, checks_failed);
        return 1;
    }
    check(1, "create a writable XDG_RUNTIME_DIR under /data/storage/el2/base");
    setenv("XDG_RUNTIME_DIR", runtime_dir, 1);

    server_display = wl_display_create();
    check(server_display != NULL, "wl_display_create (server)");
    if (!server_display) {
        goto out;
    }

    compositor_global = wl_global_create(server_display, &wl_compositor_interface,
                                         4, NULL, bind_compositor);
    check(compositor_global != NULL, "register wl_compositor v4 global");
    if (!compositor_global) {
        goto out;
    }

    if (wl_display_add_socket(server_display, "wl") != 0) {
        check(0, "bind AF_UNIX socket in XDG_RUNTIME_DIR");
        goto out;
    }
    check(1, "bind AF_UNIX socket in XDG_RUNTIME_DIR");

    /* wakeup channel: the eventfd is a plain kernel object, so writing to it
     * from the main thread is thread-safe; the callback runs in the loop. It
     * is a hard prerequisite: without it the loop cannot be woken when the
     * test ends, and the global_remove check cannot run. */
    wakeup.display = server_display;
    wakeup.global = compositor_global;
    wakeup.fd = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
    if (wakeup.fd >= 0 &&
        wl_event_loop_add_fd(wl_display_get_event_loop(server_display),
                             wakeup.fd, WL_EVENT_READABLE,
                             handle_server_wakeup, &wakeup) == NULL) {
        close(wakeup.fd);
        wakeup.fd = -1;
    }
    if (wakeup.fd < 0) {
        check(0, "create the eventfd wakeup channel");
        goto out;
    }

    if (pthread_create(&server_thread, NULL, server_run, server_display) == 0) {
        thread_started = 1;
        check(1, "start the server event loop thread");
    } else {
        check(0, "start the server event loop thread");
    }
    /* Without the loop thread the registry roundtrip below would block
     * forever (the socket exists, but nobody answers), so stop here and
     * report a clean failure instead of hanging the CI run. */
    if (!thread_started) {
        goto out;
    }

    /* 1. own-display context: connect + registry roundtrip */
    own = kywc_context_create("wl",
                              KYWC_CONTEXT_CAPABILITY_OUTPUT |
                              KYWC_CONTEXT_CAPABILITY_TOPLEVEL |
                              KYWC_CONTEXT_CAPABILITY_WORKSPACE,
                              &context_interface, &own_calls);
    check(own != NULL,
          "kywc_context_create connects and completes the registry roundtrip");
    if (own) {
        int workspaces = 0;

        check(own_calls.create == 1,
              "context create callback invoked exactly once");
        check(kywc_context_get_display(own) != NULL,
              "kywc_context_get_display returns a display");
        check(kywc_context_get_fd(own) >= 0,
              "kywc_context_get_fd returns a valid fd");
        check(kywc_context_get_user_data(own) == &own_calls,
              "kywc_context_get_user_data returns the caller pointer");

        kywc_context_for_each_workspace(own, count_workspace, &workspaces);
        check(workspaces == 0,
              "for_each_workspace yields zero workspaces on a server without kywc globals");
        check(kywc_context_find_workspace(own, "absent-uuid") == NULL,
              "find_workspace returns NULL for an unknown uuid");
    }

    /* 2. caller-owned display: create_by_display + destroy */
    {
        struct wl_display *client_display = wl_display_connect("wl");
        check(client_display != NULL, "wl_display_connect to the test compositor");
        if (client_display) {
            struct context_calls ext_calls = {0};
            kywc_context *ext = kywc_context_create_by_display(
                client_display, KYWC_CONTEXT_CAPABILITY_OUTPUT,
                &context_interface, &ext_calls);
            check(ext != NULL, "kywc_context_create_by_display on an existing display");
            if (ext) {
                check(kywc_context_get_display(ext) == client_display,
                      "create_by_display keeps the caller display");
                kywc_context_destroy(ext);
                check(ext_calls.destroy == 1,
                      "destroy callback invoked by kywc_context_destroy");
            }
            wl_display_disconnect(client_display);
        }
    }

    /* 3. error path: nonexistent socket */
    {
        struct context_calls missing_calls = {0};
        kywc_context *missing = kywc_context_create(
            "kywc-no-such-socket", KYWC_CONTEXT_CAPABILITY_OUTPUT,
            &context_interface, &missing_calls);
        check(missing == NULL,
              "kywc_context_create returns NULL when the socket does not exist");
    }

    /* 4. NULL-argument handling of the public getters */
    check(kywc_context_get_display(NULL) == NULL,
          "kywc_context_get_display(NULL) returns NULL");
    check(kywc_context_get_fd(NULL) == -1,
          "kywc_context_get_fd(NULL) returns -1");
    check(kywc_context_get_user_data(NULL) == NULL,
          "kywc_context_get_user_data(NULL) returns NULL");
    check(kywc_context_process(NULL) == -1,
          "kywc_context_process(NULL) returns -1");
    kywc_context_destroy(NULL);
    check(1, "kywc_context_destroy(NULL) is a no-op");

    /* 5. process(): a server-side global_remove makes the client fd readable */
    if (own) {
        struct pollfd pfd;
        int pr;

        if (compositor_global && wakeup.fd >= 0) {
            uint64_t one = 1;

            /* the loop thread destroys the global and flushes the queued
             * global_remove to the client; see handle_server_wakeup() */
            if (write(wakeup.fd, &one, sizeof(one)) != sizeof(one)) {
                fprintf(stderr, "kywc-test: wakeup write failed: %s\n",
                        strerror(errno));
            }
            compositor_global = NULL;
        }
        pfd.fd = kywc_context_get_fd(own);
        pfd.events = POLLIN;
        pfd.revents = 0;
        pr = poll(&pfd, 1, 3000);
        check(pr == 1 && (pfd.revents & POLLIN),
              "client fd becomes readable after a server global_remove");
        if (pr == 1 && (pfd.revents & POLLIN)) {
            check(kywc_context_process(own) == 0,
                  "kywc_context_process dispatches the pending event");
        }
        kywc_context_destroy(own);
        own = NULL;
        check(own_calls.destroy == 1,
              "own-display context destroy callback invoked exactly once");
    }

out:
    if (thread_started) {
        uint64_t one = 1;

        /* Ask the loop itself to terminate: wl_display_run() sets run = 1 on
         * entry, so a terminate issued from this thread before the loop has
         * started could be overwritten. The wakeup callback runs inside the
         * loop (waking it from epoll_wait as a side effect), so the join is
         * race-free even on the failure paths above. */
        atomic_store(&wakeup.terminate, true);
        if (wakeup.fd >= 0) {
            (void)write(wakeup.fd, &one, sizeof(one));
        } else {
            wl_display_terminate(server_display);
        }
        pthread_join(server_thread, NULL);
    }
    if (server_display) {
        wl_display_destroy(server_display);
    }
    if (wakeup.fd >= 0) {
        close(wakeup.fd);
    }
    rmdir(runtime_dir);

    printf("TEST SUMMARY: %d passed, %d failed\n",
           checks_run - checks_failed, checks_failed);
    return checks_failed == 0 ? 0 : 1;
}

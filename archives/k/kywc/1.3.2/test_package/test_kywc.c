/*
 * test_kywc.c — installed-consumer E2E for kywc 1.3.2 on HarmonyOS PC.
 *
 * Starts an in-process Wayland server (libwayland-server) on a AF_UNIX
 * socket under a writable /data/storage/el2/base directory, then exercises
 * the public libkywc API through the installed package:
 *
 *   1. capabilities=0 lifecycle: create/roundtrip, display, fd, user data,
 *      iterators, find helpers, destroy callback
 *   2. manager-backed capabilities (OUTPUT|TOPLEVEL|WORKSPACE) against a
 *      server that advertises no kywc globals: context must still be created,
 *      iterators must be empty and destroy must stay null-safe
 *   3. kywc_context_create_by_display: non-owning display must survive the
 *      context destruction and remain usable for another roundtrip
 *   4. kywc_context_create on a missing socket must return NULL
 *   5. NULL-argument helpers are safe
 *
 * Output: one CHECK PASS/FAIL line per check and a final TEST SUMMARY line.
 * Exit code 1 if any check failed.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include <wayland-client.h>
#include <wayland-server-core.h>

#include "libkywc.h"

static int checks_passed;
static int checks_failed;

#define CHECK(cond, ...)                                                   \
    do {                                                                   \
        if (cond) {                                                        \
            checks_passed++;                                               \
            printf("CHECK PASS: ");                                        \
        } else {                                                           \
            checks_failed++;                                               \
            printf("CHECK FAIL: ");                                        \
        }                                                                  \
        printf(__VA_ARGS__);                                               \
        printf("\n");                                                      \
        fflush(stdout);                                                    \
    } while (0)

struct cb_state {
    int create_calls;
    int destroy_calls;
    kywc_context *create_ctx;
    kywc_context *destroy_ctx;
    void *create_data;
    void *destroy_data;
};

static struct cb_state callback_state;

static void on_create(kywc_context *ctx, void *data)
{
    callback_state.create_calls++;
    callback_state.create_ctx = ctx;
    callback_state.create_data = data;
}

static void on_destroy(kywc_context *ctx, void *data)
{
    callback_state.destroy_calls++;
    callback_state.destroy_ctx = ctx;
    callback_state.destroy_data = data;
}

static const struct kywc_context_interface context_impl = {
    .create = on_create,
    .destroy = on_destroy,
};

static void reset_callbacks(void)
{
    memset(&callback_state, 0, sizeof(callback_state));
}

/* libkywc iterators pass each object to the callback; the public iterator
 * typedef returns bool (true breaks the loop). */
static bool output_counter(kywc_output *output, void *data)
{
    (void)output;
    (*(int *)data)++;
    return false;
}

static bool workspace_counter(kywc_workspace *workspace, void *data)
{
    (void)workspace;
    (*(int *)data)++;
    return false;
}

static int for_each_outputs(kywc_context *ctx)
{
    int count = 0;
    kywc_context_for_each_output(ctx, output_counter, &count);
    return count;
}

static int for_each_workspaces(kywc_context *ctx)
{
    int count = 0;
    kywc_context_for_each_workspace(ctx, workspace_counter, &count);
    return count;
}

static char runtime_dir[512];
static struct wl_display *server_display;
static pthread_t server_thread;
static int server_thread_started;
static const char *server_socket;

static void *server_run(void *arg)
{
    wl_display_run((struct wl_display *)arg);
    return NULL;
}

/* AF_UNIX bind() is EPERM on HMDFS (/storage); the el2 base directories are
 * on the writable data partition (libinput signed-loader precedent). */
static int make_runtime_dir(void)
{
    const char *bases[] = {
        "/data/storage/el2/base/tmp",
        "/data/storage/el2/base/cache",
        "/data/storage/el2/base",
        NULL, /* TMPDIR */
        NULL, /* HOME */
        ".",
    };
    bases[3] = getenv("TMPDIR");
    bases[4] = getenv("HOME");
    for (size_t i = 0; i < sizeof(bases) / sizeof(bases[0]); i++) {
        if (!bases[i] || !*bases[i])
            continue;
        struct stat info;
        if (stat(bases[i], &info) != 0 || !S_ISDIR(info.st_mode))
            continue;
        if (access(bases[i], W_OK | X_OK) != 0)
            continue;
        char template_path[600];
        snprintf(template_path, sizeof(template_path), "%s/kywc-e2e-XXXXXX",
                 bases[i]);
        char *created = mkdtemp(template_path);
        if (!created)
            continue;
        strncpy(runtime_dir, created, sizeof(runtime_dir) - 1);
        runtime_dir[sizeof(runtime_dir) - 1] = '\0';
        if (setenv("XDG_RUNTIME_DIR", runtime_dir, 1) != 0)
            return -1;
        return 0;
    }
    return -1;
}

static void on_alarm(int signum)
{
    (void)signum;
    printf("CHECK FAIL: watchdog timeout after 60s\n");
    printf("TEST SUMMARY: %d passed, %d failed\n", checks_passed,
           checks_failed + 1);
    fflush(stdout);
    _exit(1);
}

int main(void)
{
    signal(SIGALRM, on_alarm);
    alarm(60);

    printf("TEST CASE 0: in-process Wayland server setup\n");
    CHECK(make_runtime_dir() == 0, "writable XDG_RUNTIME_DIR created: %s",
          runtime_dir[0] ? runtime_dir : "(none)");

    server_display = wl_display_create();
    CHECK(server_display != NULL, "wl_display_create returned a display");
    if (!server_display)
        goto summary;

    server_socket = wl_display_add_socket_auto(server_display);
    CHECK(server_socket != NULL, "server socket allocated: %s",
          server_socket ? server_socket : "(null)");
    if (!server_socket)
        goto summary;

    server_thread_started =
        pthread_create(&server_thread, NULL, server_run, server_display) == 0;
    CHECK(server_thread_started, "server event-loop thread started");
    if (!server_thread_started)
        goto summary;

    /* ---- 1. capabilities=0 lifecycle ---- */
    printf("TEST CASE 1: capabilities=0 lifecycle\n");
    reset_callbacks();
    int marker = 42;
    int outputs = 0;
    int workspaces = 0;
    kywc_context *ctx = kywc_context_create(server_socket, 0, &context_impl,
                                            &marker);
    CHECK(ctx != NULL, "kywc_context_create(capabilities=0) returned a context");
    if (ctx) {
        CHECK(callback_state.create_calls == 1,
              "create callback fired exactly once (got %d)",
              callback_state.create_calls);
        CHECK(callback_state.create_ctx == ctx,
              "create callback received the same context pointer");
        CHECK(callback_state.create_data == &marker,
              "create callback received the caller data pointer");

        struct wl_display *display = kywc_context_get_display(ctx);
        CHECK(display != NULL, "kywc_context_get_display returned non-NULL");

        int fd = kywc_context_get_fd(ctx);
        CHECK(fd >= 0 && fcntl(fd, F_GETFD) != -1,
              "kywc_context_get_fd returned a live fd (%d)", fd);

        CHECK(kywc_context_get_user_data(ctx) == &marker,
              "kywc_context_get_user_data returns the create-time data");

        int marker2 = 43;
        kywc_context_set_user_data(ctx, &marker2);
        CHECK(kywc_context_get_user_data(ctx) == &marker2,
              "kywc_context_set_user_data replaces the data pointer");

        outputs = for_each_outputs(ctx);
        CHECK(outputs == 0,
              "for_each_output visits no output on an empty server (got %d)",
              outputs);
        workspaces = for_each_workspaces(ctx);
        CHECK(workspaces == 0,
              "for_each_workspace visits no workspace on an empty server (got %d)",
              workspaces);

        CHECK(kywc_context_find_output(ctx, "no-such-output") == NULL,
              "find_output returns NULL for an unknown uuid");
        CHECK(kywc_context_find_workspace(ctx, "no-such-workspace") == NULL,
              "find_workspace returns NULL for an unknown uuid");

        kywc_context_destroy(ctx);
        CHECK(callback_state.destroy_calls == 1,
              "destroy callback fired exactly once (got %d)",
              callback_state.destroy_calls);
        CHECK(callback_state.destroy_ctx == ctx,
              "destroy callback received the same context pointer");
        CHECK(callback_state.destroy_data == &marker2,
              "destroy callback received the current user data pointer");
    }

    /* ---- 2. manager capabilities without globals ---- */
    printf("TEST CASE 2: manager capabilities on a globals-less server\n");
    reset_callbacks();
    int marker3 = 44;
    uint32_t caps = KYWC_CONTEXT_CAPABILITY_OUTPUT |
                    KYWC_CONTEXT_CAPABILITY_TOPLEVEL |
                    KYWC_CONTEXT_CAPABILITY_WORKSPACE;
    ctx = kywc_context_create(server_socket, caps, &context_impl, &marker3);
    CHECK(ctx != NULL, "context with OUTPUT|TOPLEVEL|WORKSPACE created");
    if (ctx) {
        CHECK(callback_state.create_calls == 1,
              "create callback fired exactly once for manager capabilities");
        CHECK(kywc_context_get_display(ctx) != NULL,
              "manager-capability context has a display");
        outputs = for_each_outputs(ctx);
        CHECK(outputs == 0,
              "no output is reported when no kywc-output-manager global exists (got %d)",
              outputs);
        workspaces = for_each_workspaces(ctx);
        CHECK(workspaces == 0,
              "no workspace is reported when no kywc-workspace-manager global exists (got %d)",
              workspaces);
        kywc_context_destroy(ctx);
        CHECK(callback_state.destroy_calls == 1,
              "destroy callback fired exactly once for manager capabilities");
    }

    /* ---- 3. create_by_display is non-owning ---- */
    printf("TEST CASE 3: kywc_context_create_by_display\n");
    reset_callbacks();
    struct wl_display *client_display = wl_display_connect(server_socket);
    CHECK(client_display != NULL, "wl_display_connect(%s) succeeded",
          server_socket);
    if (client_display) {
        ctx = kywc_context_create_by_display(
            client_display, KYWC_CONTEXT_CAPABILITY_OUTPUT, &context_impl, NULL);
        CHECK(ctx != NULL, "kywc_context_create_by_display returned a context");
        if (ctx) {
            CHECK(kywc_context_get_display(ctx) == client_display,
                  "context exposes the caller-owned display");
            kywc_context_destroy(ctx);
            CHECK(callback_state.destroy_calls == 1,
                  "destroy callback fired for the by-display context");
        }
        /* The context did not own the display: it must stay usable.
         * wl_display_roundtrip returns the number of dispatched events
         * (>= 0) on success and -1 when the display is in error. */
        struct wl_registry *registry = wl_display_get_registry(client_display);
        CHECK(registry != NULL,
              "caller-owned display survives context destruction");
        int roundtrip_events = wl_display_roundtrip(client_display);
        CHECK(roundtrip_events >= 0,
              "caller-owned display still round-trips with the server "
              "(dispatched %d events, display error %d)",
              roundtrip_events,
              wl_display_get_error(client_display));
        if (registry)
            wl_registry_destroy(registry);
        wl_display_disconnect(client_display);
    }

    /* ---- 4. missing socket ---- */
    printf("TEST CASE 4: missing Wayland socket\n");
    reset_callbacks();
    ctx = kywc_context_create("kywc-e2e-no-such-socket", 0, &context_impl, NULL);
    CHECK(ctx == NULL,
          "kywc_context_create returns NULL for a missing compositor socket");
    CHECK(callback_state.create_calls == 0,
          "create callback is not fired when the socket is missing");

    /* ---- 5. NULL-argument safety ---- */
    printf("TEST CASE 5: NULL-argument helpers\n");
    CHECK(kywc_context_get_display(NULL) == NULL,
          "kywc_context_get_display(NULL) returns NULL");
    CHECK(kywc_context_get_fd(NULL) == -1,
          "kywc_context_get_fd(NULL) returns -1");
    CHECK(kywc_context_get_user_data(NULL) == NULL,
          "kywc_context_get_user_data(NULL) returns NULL");
    kywc_context_destroy(NULL);
    CHECK(1, "kywc_context_destroy(NULL) is a no-op");

summary:
    if (server_display) {
        wl_display_terminate(server_display);
        if (server_thread_started)
            pthread_join(server_thread, NULL);
        wl_display_destroy(server_display);
    }
    if (runtime_dir[0])
        rmdir(runtime_dir);

    printf("TEST SUMMARY: %d passed, %d failed\n", checks_passed, checks_failed);
    return checks_failed == 0 ? 0 : 1;
}

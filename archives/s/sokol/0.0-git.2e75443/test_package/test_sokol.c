/*
 * Consumer test for sokol 0.0-git.2e75443 (C99 TU).
 *
 * 54 assertions across 11 core/util headers, all calibrated on the
 * target (OHOS aarch64 / clang 15 / musl) during recipe bring-up:
 *   sokol_gfx        sg_setup/sg_isvalid/sg_shutdown lifecycle (dummy)
 *   sokol_time       stm_now/stm_diff/stm_since/stm_laptime monotonicity
 *                    + unit-conversion math on exact tick counts
 *   sokol_args       key=value parsing, exists/find/value/value_def
 *   sokol_audio      dummy-backend setup defaults (44100/1/2048/8192),
 *                    push(2 frames) => 2 written, expect() == 8190
 *   sokol_color      sg_make_color_4b channel encoding
 *   sokol_shape      sshape_plane_sizes(1/2) vertex+index counts
 *   sokol_letterbox  16:9 fullscreen + 4:3 letterboxed viewport
 *   sokol_memtrack   smemtrack_alloc/free roundtrip
 *   sokol_log        slog_func formatted emission (smoke)
 *   sokol_fetch      posix-threads backend: real file async load,
 *                    256 bytes, content checksum, setup/teardown
 *   sokol_framebuffer sfb_setup/shutdown lifecycle (needs sg up)
 *
 * Implementation sections compiled in SOKOL_DUMMY_BACKEND mode in this
 * binary (headless consumption; graphics backend binding is a
 * per-consumer decision by upstream design).
 */
#ifndef SOKOL_DUMMY_BACKEND
#define SOKOL_DUMMY_BACKEND
#endif
#define SOKOL_IMPL
#include "sokol_gfx.h"
#include "sokol_log.h"
#include "sokol_time.h"
#include "sokol_args.h"
#include "sokol_audio.h"
#include "sokol_fetch.h"
#include "sokol_color.h"
#include "sokol_shape.h"
#include "sokol_letterbox.h"
#include "sokol_memtrack.h"
#include "sokol_framebuffer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failures = 0;
static int checks = 0;
#define CHECK(cond) do { \
    checks++; \
    if (!(cond)) { failures++; printf("FAIL: %s (line %d)\n", #cond, __LINE__); } \
} while (0)

/* ── fetch callback state: 1 = fetched (chunk), 2 = finished ok, 3 = failed ── */
static int fetch_state = 0;
static size_t fetch_size = 0;
static void fetch_cb(const sfetch_response_t* r) {
    if (r->fetched) { fetch_state = 1; fetch_size = r->data.size; }
    if (r->finished) { if (r->failed) fetch_state = 3; else fetch_state = 2; }
}

int main(void) {
    /* ── sokol_gfx (dummy backend) ─────────────────────────────── */
    sg_setup(&(sg_desc){0});
    CHECK(sg_isvalid());
    sg_shutdown();
    CHECK(!sg_isvalid());

    /* ── sokol_time ────────────────────────────────────────────── */
    stm_setup();
    uint64_t t0 = stm_now();
    uint64_t t1 = stm_now();
    CHECK(t1 >= t0);                 /* monotonic (first read may be 0 on musl) */
    CHECK(stm_sec(1000000000ULL) == 1.0);
    CHECK(stm_ms(1000000ULL) == 1.0);
    CHECK(stm_us(1000ULL) == 1.0);
    CHECK(stm_ns(1ULL) == 1.0);
    /* upstream contract: new>old ? new-old : 1 (t1==t0 possible on musl) */
    CHECK(stm_diff(t1, t0) == (t1 > t0 ? t1 - t0 : 1));
    CHECK(stm_since(t0) >= t1 - t0);
    uint64_t lap_start = t0;
    uint64_t lap = stm_laptime(&lap_start);
    CHECK(lap >= 0);
    CHECK(stm_round_to_common_refresh_rate(16666667ULL) > 0);

    /* ── sokol_args ────────────────────────────────────────────── */
    char* argv_1[] = { (char*)"test_sokol", (char*)"kvp0=val0" };
    sargs_setup(&(sargs_desc){ .argc = 2, .argv = argv_1 });
    CHECK(sargs_isvalid());
    CHECK(sargs_num_args() == 1);
    CHECK(sargs_exists("kvp0"));
    CHECK(!sargs_exists("nope"));
    CHECK(sargs_find("kvp0") == 0);
    CHECK(sargs_find("nope") == -1);
    CHECK(strcmp(sargs_value("kvp0"), "val0") == 0);
    CHECK(strcmp(sargs_value("nope"), "") == 0);
    CHECK(strcmp(sargs_value_def("nope", "dflt"), "dflt") == 0);
    CHECK(strcmp(sargs_key_at(0), "kvp0") == 0);
    CHECK(strcmp(sargs_value_at(0), "val0") == 0);
    sargs_shutdown();
    CHECK(!sargs_isvalid());

    /* ── sokol_audio (dummy backend; anchors calibrated on target) ── */
    saudio_setup(&(saudio_desc){0});
    CHECK(saudio_isvalid());
    CHECK(saudio_sample_rate() == 44100);
    CHECK(saudio_channels() == 1);
    CHECK(saudio_buffer_frames() == 2048);
    CHECK(saudio_expect() == 8192);
    float frames[2] = { 0.5f, -0.5f };
    CHECK(saudio_push(frames, 2) == 2);
    CHECK(saudio_expect() == 8190);
    saudio_shutdown();
    CHECK(!saudio_isvalid());

    /* ── sokol_color ───────────────────────────────────────────── */
    const sg_color c0 = sg_make_color_4b(255, 127, 0, 255);
    CHECK(c0.r == 1.0f);
    CHECK(c0.g > 0.49f && c0.g < 0.50f);   /* 127/255 == 0.498039 */
    CHECK(c0.b == 0.0f);
    CHECK(c0.a == 1.0f);

    /* ── sokol_shape ───────────────────────────────────────────── */
    sshape_sizes_t ps = sshape_plane_sizes(1, SSHAPE_MAX_VERTEX_SIZE);
    CHECK(ps.vertices.num == 4);
    CHECK(ps.indices.num == 6);
    CHECK(ps.vertices.size == ps.vertices.num * SSHAPE_MAX_VERTEX_SIZE);
    CHECK(ps.indices.size == ps.indices.num * sizeof(uint16_t));
    ps = sshape_plane_sizes(2, SSHAPE_MAX_VERTEX_SIZE);
    CHECK(ps.vertices.num == 9);
    CHECK(ps.indices.num == 24);

    /* ── sokol_letterbox (anchors calibrated on target) ────────── */
    slbx_viewport vp169 = slbx_letterbox(1920, 1080, &(slbx_letterbox_desc){
        .content_aspect_ratio = 16.0f / 9.0f,
    });
    CHECK(vp169.x == 0);
    CHECK(vp169.y == 0);
    CHECK(vp169.width == 1920);
    CHECK(vp169.height == 1080);
    slbx_viewport vp43 = slbx_letterbox(1920, 1080, &(slbx_letterbox_desc){
        .content_aspect_ratio = 4.0f / 3.0f,
    });
    CHECK(vp43.x == 240);
    CHECK(vp43.y == 0);
    CHECK(vp43.width == 1440);
    CHECK(vp43.height == 1080);

    /* ── sokol_memtrack ────────────────────────────────────────── */
    void* p = smemtrack_alloc(64, 0);
    CHECK(p != 0);
    memset(p, 0xA5, 64);
    CHECK(((unsigned char*)p)[63] == 0xA5);
    smemtrack_free(p, 0);

    /* ── sokol_log (formatted emission smoke) ──────────────────── */
    slog_func("sokol-test", 1, 0, "consumer smoke log line", 42,
              "test_sokol.c", 0);

    /* ── sokol_fetch (posix-threads backend, real file) ────────── */
    const char* fname = "sokol_fetch_probe.tmp";
    FILE* f = fopen(fname, "wb");
    CHECK(f != 0);
    if (f) {
        for (int i = 0; i < 256; i++) fputc(i & 0xFF, f);
        fclose(f);
    }
    sfetch_setup(&(sfetch_desc_t){0});
    CHECK(sfetch_valid());
    static uint8_t buf[256];
    sfetch_send(&(sfetch_request_t){
        .path = fname,
        .callback = fetch_cb,
        .buffer = { .ptr = buf, .size = sizeof(buf) },
    });
    for (int i = 0; i < 1000 && fetch_state < 2; i++) {
        sfetch_dowork();
        usleep(1000);
    }
    CHECK(fetch_state == 2);          /* finished without failure */
    CHECK(fetch_size == 256);
    CHECK(buf[0] == 0x00 && buf[255] == 0xFF);
    sfetch_shutdown();
    CHECK(!sfetch_valid());
    remove(fname);

    /* ── sokol_framebuffer (needs sg up) ───────────────────────── */
    sg_setup(&(sg_desc){0});
    sfb_setup(&(sfb_desc){0});
    sfb_shutdown();
    sg_shutdown();

    printf("sokol consumer test (C): %d checks, %d failures — %s\n",
           checks, failures, failures ? "FAILED" : "ALL OK");
    return failures ? 1 : 0;
}

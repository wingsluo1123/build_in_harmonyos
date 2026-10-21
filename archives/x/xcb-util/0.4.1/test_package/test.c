/* xcb-util 0.4.1 consumer link + real API test (runs without an X server).
 *
 * xcb-util exposes three families of helpers that are fully usable without a
 * server connection:
 *   - xcb_aux_parse_color(): pure "#RGB" string parser from Xlib,
 *   - xcb_atom_name_*(): predefined atom name builders (vasprintf-based),
 *   - xcb_event_get_{label,error_label,request_label}(): static lookup
 *     tables over the core protocol numbering.
 *
 * Per knowledge entry E530 (X11-family client libraries ship no upstream
 * tests and a real server is unavailable on OHOS CI workers), the test does
 * strong-typed relocation of the exported symbols, pins the ABI of the
 * xcb_params_* packing structs, and then actually calls the pure functions
 * and asserts their documented results.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>

#include <xcb/xcb.h>
#include <xcb/xcb_util.h>

static int failures = 0;
static int assertions = 0;

static void expect(const char *what, int condition) {
    assertions++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

static void expect_str(const char *what, const char *got, const char *want) {
    assertions++;
    if (!got || strcmp(got, want) != 0) {
        fprintf(stderr, "FAIL: %s = %s, expected \"%s\"\n", what, got ? got : "(null)", want);
        failures++;
    }
}

/* --- E530 strong-typed relocation: the exported symbols must exist with the
 *     exact documented signatures, and taking their addresses forces the
 *     linker to resolve them from libxcb-util. --- */
int (*xcb_aux_parse_color_alias)(const char *, uint16_t *, uint16_t *, uint16_t *)
    = xcb_aux_parse_color;
const char *(*xcb_event_get_label_alias)(uint8_t) = xcb_event_get_label;
const char *(*xcb_event_get_error_label_alias)(uint8_t) = xcb_event_get_error_label;
const char *(*xcb_event_get_request_label_alias)(uint8_t) = xcb_event_get_request_label;
char *(*xcb_atom_name_by_screen_alias)(const char *, uint8_t) = xcb_atom_name_by_screen;
char *(*xcb_atom_name_unique_alias)(const char *, uint32_t) = xcb_atom_name_unique;

/* --- ABI pins for the caller-filled parameter structs (all uint32_t fields,
 *     layout pinned because xcb_aux_* walks them with XCB_AUX_ADD_PARAM). --- */
_Static_assert(sizeof(xcb_params_cw_t) == 15 * 4, "xcb_params_cw_t layout");
_Static_assert(offsetof(xcb_params_cw_t, back_pixmap) == 0, "xcb_params_cw_t.back_pixmap");
_Static_assert(offsetof(xcb_params_cw_t, override_redirect) == 36, "xcb_params_cw_t.override_redirect");
_Static_assert(offsetof(xcb_params_cw_t, cursor) == 56, "xcb_params_cw_t.cursor");

_Static_assert(sizeof(xcb_params_gc_t) == 23 * 4, "xcb_params_gc_t layout");
_Static_assert(offsetof(xcb_params_gc_t, function) == 0, "xcb_params_gc_t.function");
_Static_assert(offsetof(xcb_params_gc_t, mask) == 76, "xcb_params_gc_t.mask");
_Static_assert(offsetof(xcb_params_gc_t, arc_mode) == 88, "xcb_params_gc_t.arc_mode");

_Static_assert(sizeof(xcb_params_configure_window_t) == 7 * 4, "xcb_params_configure_window_t layout");
_Static_assert(offsetof(xcb_params_configure_window_t, stack_mode) == 24, "xcb_params_configure_window_t.stack_mode");

_Static_assert(sizeof(xcb_params_keyboard_t) == 8 * 4, "xcb_params_keyboard_t layout");
_Static_assert(offsetof(xcb_params_keyboard_t, auto_repeat_mode) == 28, "xcb_params_keyboard_t.auto_repeat_mode");

int main(void) {
    /* --- xcb_aux_parse_color: real calls of the pure parser --- */
    {
        uint16_t r = 0xAAAA, g = 0xBBBB, b = 0xCCCC;
        expect("parse_color #123456 succeeds",
               xcb_aux_parse_color("#123456", &r, &g, &b) == 1);
        expect("parse_color red", r == 0x1200);
        expect("parse_color green", g == 0x3400);
        expect("parse_color blue", b == 0x5600);
    }
    {
        uint16_t r = 0, g = 0, b = 0;
        expect("parse_color #ABC succeeds",
               xcb_aux_parse_color("#ABC", &r, &g, &b) == 1);
        expect("parse_color short red", r == 0xA000);
        expect("parse_color short green", g == 0xB000);
        expect("parse_color short blue", b == 0xC000);
    }
    {
        uint16_t r, g, b;
        expect("parse_color rejects 4-digit length",
               xcb_aux_parse_color("#1234", &r, &g, &b) == 0);
        expect("parse_color rejects non-hex",
               xcb_aux_parse_color("#GGG", &r, &g, &b) == 0);
        expect("parse_color rejects missing #",
               xcb_aux_parse_color("red", &r, &g, &b) == 0);
        expect("parse_color rejects NULL",
               xcb_aux_parse_color(NULL, &r, &g, &b) == 0);
    }

    /* --- xcb_event_* label tables --- */
    expect_str("event label KeyPress", xcb_event_get_label(XCB_KEY_PRESS), "KeyPress");
    expect_str("event label Expose", xcb_event_get_label(XCB_EXPOSE), "Expose");
    expect("event label out of range is NULL", xcb_event_get_label(200) == NULL);
    expect_str("error label Success", xcb_event_get_error_label(0), "Success");
    expect_str("error label BadValue", xcb_event_get_error_label(2), "BadValue");
    expect_str("error label BadImplementation", xcb_event_get_error_label(17), "BadImplementation");
    expect("error label out of range is NULL", xcb_event_get_error_label(200) == NULL);
    expect_str("request label MapWindow", xcb_event_get_request_label(8), "MapWindow");
    expect_str("request label InternAtom", xcb_event_get_request_label(16), "InternAtom");
    expect("request label out of range is NULL", xcb_event_get_request_label(200) == NULL);

    /* --- xcb_atom_* name builders (vasprintf path on musl via config.h) --- */
    {
        char *s = xcb_atom_name_by_screen("WM_PROTOCOLS", 3);
        expect_str("atom_name_by_screen", s, "WM_PROTOCOLS_S3");
        free(s);
    }
    {
        char *s = xcb_atom_name_by_resource("ESETROOT", 0xDEADBEEFu);
        expect_str("atom_name_by_resource", s, "ESETROOT_RDEADBEEF");
        free(s);
    }
    {
        char *s = xcb_atom_name_unique("WM_STATE", 7);
        expect_str("atom_name_unique with base", s, "WM_STATE_U7");
        free(s);
        s = xcb_atom_name_unique(NULL, 42);
        expect_str("atom_name_unique without base", s, "U42");
        free(s);
    }

    /* --- XCB_AUX_ADD_PARAM flag bookkeeping on the caller's struct --- */
    {
        xcb_params_cw_t params;
        uint32_t mask = 0;
        memset(&params, 0, sizeof(params));
        XCB_AUX_ADD_PARAM(&mask, &params, back_pixel, 0xFF00FF00u);
        XCB_AUX_ADD_PARAM(&mask, &params, event_mask, 0x1u);
        expect("XCB_AUX_ADD_PARAM sets back_pixel", params.back_pixel == 0xFF00FF00u);
        expect("XCB_AUX_ADD_PARAM sets event_mask", params.event_mask == 0x1u);
        /* XCB_AUX_INTERNAL_OFFSETOF expresses the offset in uint32_t units,
         * so the flags must be 1<<1 for back_pixel (second field) and 1<<11
         * for event_mask (twelfth field). */
        expect("mask flags for back_pixel+event_mask", mask == ((1u << 1) | (1u << 11)));
    }

    printf("xcb-util consumer test: assertions=%d failures=%d\n", assertions, failures);
    return failures == 0 ? 0 : 1;
}

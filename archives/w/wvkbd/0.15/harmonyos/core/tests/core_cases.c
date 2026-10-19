/* SPDX-License-Identifier: GPL-3.0-only */
#include "core_cases.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expr); return 1; } } while (0)
typedef struct { size_t row, column; } position;

static position find_key(wvkbd_action action, const char *text)
{
    wvkbd_core_state state;
    wvkbd_core_state_init(&state);
    for (size_t r = 0; r < wvkbd_core_row_count(); ++r) {
        for (size_t c = 0; c < wvkbd_core_key_count(r); ++c) {
            wvkbd_event event;
            if (wvkbd_core_activate(&state, r, c, &event) == 0 &&
                event.action == action && (!text || strcmp(event.text, text) == 0))
                return (position){r, c};
            wvkbd_core_state_init(&state);
        }
    }
    return (position){SIZE_MAX, SIZE_MAX};
}

static int press(wvkbd_core_state *state, position key, wvkbd_action action, const char *text)
{
    wvkbd_event event;
    CHECK(wvkbd_core_activate(state, key.row, key.column, &event) == 0);
    CHECK(event.action == action);
    CHECK(strcmp(event.text, text) == 0);
    return 0;
}

/* Catches omitted printable/control keys and wrong emitted action/text. */
static int test_default_layout_has_printable_and_control_keys(void)
{
    wvkbd_core_state state;
    wvkbd_core_state_init(&state);
    CHECK(wvkbd_core_row_count() > 0);
    CHECK(press(&state, find_key(WVKBD_ACTION_INSERT_TEXT, "a"), WVKBD_ACTION_INSERT_TEXT, "a") == 0);
    CHECK(press(&state, find_key(WVKBD_ACTION_INSERT_TEXT, " "), WVKBD_ACTION_INSERT_TEXT, " ") == 0);
    CHECK(press(&state, find_key(WVKBD_ACTION_BACKSPACE, NULL), WVKBD_ACTION_BACKSPACE, "") == 0);
    CHECK(press(&state, find_key(WVKBD_ACTION_ENTER, NULL), WVKBD_ACTION_ENTER, "") == 0);
    return 0;
}

/* Catches sticky Shift, lost Caps, and incorrect letter/punctuation case. */
static int test_shift_caps_and_emitted_character(void)
{
    wvkbd_core_state state;
    wvkbd_core_state_init(&state);
    position a = find_key(WVKBD_ACTION_INSERT_TEXT, "a");
    position one = find_key(WVKBD_ACTION_INSERT_TEXT, "1");
    position shift = find_key(WVKBD_ACTION_SHIFT, NULL);
    position controls[] = {find_key(WVKBD_ACTION_BACKSPACE, NULL), find_key(WVKBD_ACTION_ENTER, NULL), find_key(WVKBD_ACTION_INSERT_TEXT, " ")};
    CHECK(!state.shift && !state.caps_lock);
    CHECK(press(&state, shift, WVKBD_ACTION_SHIFT, "") == 0);
    wvkbd_key_view view;
    CHECK(wvkbd_core_key_at(&state, a.row, a.column, &view) == 0);
    CHECK(strcmp(view.label, "A") == 0);
    CHECK(press(&state, a, WVKBD_ACTION_INSERT_TEXT, "A") == 0);
    CHECK(!state.shift);
    CHECK(press(&state, a, WVKBD_ACTION_INSERT_TEXT, "a") == 0);
    for (size_t i = 0; i < sizeof controls / sizeof controls[0]; ++i) {
        wvkbd_event event;
        CHECK(press(&state, shift, WVKBD_ACTION_SHIFT, "") == 0);
        CHECK(wvkbd_core_activate(&state, controls[i].row, controls[i].column, &event) == 0);
        CHECK(!state.shift);
    }
    wvkbd_core_set_caps_lock(&state, true);
    CHECK(press(&state, a, WVKBD_ACTION_INSERT_TEXT, "A") == 0);
    CHECK(state.caps_lock);
    CHECK(press(&state, one, WVKBD_ACTION_INSERT_TEXT, "1") == 0);
    CHECK(press(&state, shift, WVKBD_ACTION_SHIFT, "") == 0);
    CHECK(press(&state, a, WVKBD_ACTION_INSERT_TEXT, "a") == 0);
    CHECK(state.caps_lock && !state.shift);
    CHECK(press(&state, shift, WVKBD_ACTION_SHIFT, "") == 0);
    CHECK(press(&state, one, WVKBD_ACTION_INSERT_TEXT, "!") == 0);
    CHECK(press(&state, shift, WVKBD_ACTION_SHIFT, "") == 0);
    CHECK(press(&state, shift, WVKBD_ACTION_SHIFT, "") == 0);
    CHECK(!state.shift);
    wvkbd_core_set_caps_lock(&state, false);
    CHECK(press(&state, a, WVKBD_ACTION_INSERT_TEXT, "a") == 0);
    state.shift = state.caps_lock = true;
    wvkbd_core_state_init(&state);
    CHECK(!state.shift && !state.caps_lock);
    return 0;
}

/* Catches unchecked indexes/nulls, stale outputs, and mutation on failure. */
static int test_invalid_key_coordinates_and_null_arguments(void)
{
    wvkbd_core_state state = {true, true};
    wvkbd_key_view view, zero_view;
    wvkbd_event event, zero_event;
    memset(&zero_view, 0, sizeof zero_view);
    memset(&zero_event, 0, sizeof zero_event);
    position invalid[] = {{wvkbd_core_row_count(), 0}, {0, wvkbd_core_key_count(0)}, {SIZE_MAX, SIZE_MAX}};
    CHECK(wvkbd_core_key_count(SIZE_MAX) == 0);
    CHECK(wvkbd_core_key_count(wvkbd_core_row_count()) == 0);
    for (size_t i = 0; i < sizeof invalid / sizeof invalid[0]; ++i) {
        memset(&view, 0xa5, sizeof view);
        memset(&event, 0xa5, sizeof event);
        CHECK(wvkbd_core_key_at(&state, invalid[i].row, invalid[i].column, &view) == -1);
        CHECK(memcmp(&view, &zero_view, sizeof view) == 0);
        CHECK(wvkbd_core_activate(&state, invalid[i].row, invalid[i].column, &event) == -1);
        CHECK(memcmp(&event, &zero_event, sizeof event) == 0);
        CHECK(state.shift && state.caps_lock);
    }
    memset(&view, 0xa5, sizeof view);
    memset(&event, 0xa5, sizeof event);
    CHECK(wvkbd_core_key_at(NULL, 0, 0, &view) == -1);
    CHECK(memcmp(&view, &zero_view, sizeof view) == 0);
    CHECK(wvkbd_core_activate(NULL, 0, 0, &event) == -1);
    CHECK(memcmp(&event, &zero_event, sizeof event) == 0);
    CHECK(wvkbd_core_key_at(&state, 0, 0, NULL) == -1);
    CHECK(wvkbd_core_activate(&state, 0, 0, NULL) == -1);
    CHECK(wvkbd_core_key_at(NULL, SIZE_MAX, SIZE_MAX, NULL) == -1);
    CHECK(wvkbd_core_activate(NULL, SIZE_MAX, SIZE_MAX, NULL) == -1);
    CHECK(state.shift && state.caps_lock);
    wvkbd_core_state_init(NULL);
    wvkbd_core_set_caps_lock(NULL, true);
    return 0;
}

static int valid_utf8(const char *text)
{
    const unsigned char *p = (const unsigned char *)text;
    while (*p) {
        uint32_t cp;
        unsigned need;
        if (*p < 0x80) { ++p; continue; }
        if (*p >= 0xc2 && *p <= 0xdf) { cp = *p & 31; need = 1; }
        else if (*p >= 0xe0 && *p <= 0xef) { cp = *p & 15; need = 2; }
        else if (*p >= 0xf0 && *p <= 0xf4) { cp = *p & 7; need = 3; }
        else return 0;
        ++p;
        for (unsigned i = 0; i < need; ++i) {
            if ((*p & 0xc0) != 0x80) return 0;
            cp = (cp << 6) | (*p++ & 63);
        }
        if ((need == 1 && cp < 0x80) || (need == 2 && cp < 0x800) ||
            (need == 3 && cp < 0x10000) || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return 0;
    }
    return 1;
}

/* Catches encoding damage across every layer's labels and emitted text. */
static int test_layout_strings_are_valid_utf8(void)
{
    int saw_shift = 0;
    for (unsigned layer = 0; layer < 4; ++layer) {
        for (size_t r = 0; r < wvkbd_core_row_count(); ++r) {
            CHECK(wvkbd_core_key_count(r) > 0);
            for (size_t c = 0; c < wvkbd_core_key_count(r); ++c) {
                wvkbd_core_state state = {(layer & 1) != 0, (layer & 2) != 0};
                wvkbd_key_view view;
                wvkbd_event event;
                CHECK(wvkbd_core_key_at(&state, r, c, &view) == 0);
                CHECK(view.label && valid_utf8(view.label));
                if (strcmp(view.label, "⇧") == 0) saw_shift = 1;
                CHECK(wvkbd_core_activate(&state, r, c, &event) == 0);
                CHECK(memchr(event.text, '\0', sizeof event.text) != NULL);
                CHECK(valid_utf8(event.text));
            }
        }
    }
    CHECK(saw_shift);
    return 0;
}

const wvkbd_test_case wvkbd_test_cases[] = {
    {"C01", "test_default_layout_has_printable_and_control_keys", test_default_layout_has_printable_and_control_keys},
    {"C02", "test_shift_caps_and_emitted_character", test_shift_caps_and_emitted_character},
    {"C03", "test_invalid_key_coordinates_and_null_arguments", test_invalid_key_coordinates_and_null_arguments},
    {"C04", "test_layout_strings_are_valid_utf8", test_layout_strings_are_valid_utf8}
};
const size_t wvkbd_test_case_count = sizeof wvkbd_test_cases / sizeof wvkbd_test_cases[0];

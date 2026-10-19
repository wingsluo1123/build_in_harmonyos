/* SPDX-License-Identifier: GPL-3.0-only
 * Portable action/state adaptation of wvkbd v0.15 keyboard behavior.
 * Shift is released after a non-modifier action; Caps affects letters only.
 */
#include "layout_mobintl.h"
#include <string.h>

void wvkbd_core_state_init(wvkbd_core_state *state)
{
    if (state) { state->shift = false; state->caps_lock = false; }
}
void wvkbd_core_set_caps_lock(wvkbd_core_state *state, bool enabled)
{
    if (state) state->caps_lock = enabled;
}
size_t wvkbd_core_row_count(void) { return wvkbd_layout_row_count(); }
size_t wvkbd_core_key_count(size_t row) { return wvkbd_layout_key_count(row); }

static const char *key_label(const wvkbd_core_state *state, const wvkbd_layout_key *key)
{
    bool shifted = key->letter ? state->shift != state->caps_lock : state->shift;
    return shifted ? key->shifted : key->normal;
}

int wvkbd_core_key_at(const wvkbd_core_state *state, size_t row,
                      size_t column, wvkbd_key_view *out)
{
    if (out) memset(out, 0, sizeof *out);
    if (!state || !out) return -1;
    const wvkbd_layout_key *key = wvkbd_layout_key_at(row, column);
    if (!key) return -1;
    out->label = key_label(state, key);
    out->action = key->action;
    return 0;
}

int wvkbd_core_activate(wvkbd_core_state *state, size_t row, size_t column,
                        wvkbd_event *out)
{
    if (out) memset(out, 0, sizeof *out);
    if (!state || !out) return -1;
    const wvkbd_layout_key *key = wvkbd_layout_key_at(row, column);
    if (!key) return -1;
    if (key->action == WVKBD_ACTION_INSERT_TEXT) {
        const char *text = strcmp(key->normal, "Space") == 0 ? " " : key_label(state, key);
        size_t length = strlen(text);
        /* Reject oversized strings as a whole, preserving UTF-8 boundaries. */
        if (length >= sizeof out->text) return -1;
        memcpy(out->text, text, length + 1);
    }
    out->action = key->action;
    if (key->action == WVKBD_ACTION_SHIFT) state->shift = !state->shift;
    else state->shift = false;
    return 0;
}
